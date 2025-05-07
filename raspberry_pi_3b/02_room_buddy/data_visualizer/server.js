const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const PORT = 3000;

// Database files
const INDOOR_DB = '../data/indoor_weather.db';
const OUTDOOR_DB = '../data/outdoor_weather.db';

// Serve static files (for D3.js and the chart)
app.use(express.static(path.join(__dirname, 'public')));

function getDbDataInfo(id) {
    switch (id) {
        case 'dht22_temperature_celsius':
        case 'bmp280_temperature_celsius':
            return { tableName: id, valueColumnName: 'temperature_celsius' };
        case 'bmp280_air_pressure_pa':
            return { tableName: id, valueColumnName: 'air_pressure_pa' };
        case 'dht22_relative_humidity_percent':
            return { tableName: id, valueColumnName: 'relative_humidity_percent' };
        default:
            throw Error(`Unknown db data ${id}`);
    }
}

function getDbData(dbFile, tableName, valueColumnName, average = false, startDate = null, endDate = null) {
    return new Promise((resolve, reject) => {
        const db = new sqlite3.Database(dbFile, sqlite3.OPEN_READONLY, (err) => {
            if (err) {
                return reject(err);
            }
        });

        const whereQuery = [];
        const params = [];

        if (startDate) {
            whereQuery.push("timestamp >= ?");
            params.push(startDate);
        }
        if (endDate) {
            whereQuery.push("timestamp <= ?");
            params.push(endDate);
        }
        if (average) {
            if (startDate) {
                params.push(startDate);
            }
            if (endDate) {
                params.push(endDate);
            }
        }

        const whereQueryString = whereQuery.length > 0 ? ` WHERE ${whereQuery.join(" AND ")}` : "";
        const query = average ? `
-- Rename columns
SELECT
    time_group AS timestamp,
    avg_value AS value
FROM (
-- Calculate the range
WITH time_range AS (
    SELECT julianday(MAX(timestamp)) - julianday(MIN(timestamp)) AS days_spanned
    FROM ${tableName}${whereQueryString}
)
SELECT
    CASE
        -- If the day range is greater than a year smooth to days
        WHEN (SELECT days_spanned FROM time_range) > 32 * 12 THEN strftime('%Y-%m-%dT00:00:00', timestamp)  -- ISO day
        -- If the day range is greater than 3 months smooth to hours
        WHEN (SELECT days_spanned FROM time_range) > 32 * 6 THEN strftime('%Y-%m-%dT%H:00:00', timestamp)   -- ISO hour
        ELSE strftime('%Y-%m-%dT%H:%M:00', timestamp)                                                       -- ISO minute
    END AS time_group,
    AVG(${valueColumnName}) AS avg_value
FROM ${tableName}${whereQueryString}
-- Group values by time group instead of just listing all values
GROUP BY time_group
ORDER BY time_group
);
` : `SELECT timestamp, ${valueColumnName} AS value FROM ${tableName}${whereQueryString} ORDER BY timestamp`;

        // DELETE
        console.log("Query", query, params);

        let startTime = performance.now();
        db.all(query, params, (err, rows) => {
            let endTime = performance.now();
            if (err) {
                reject(err);
            } else {
                resolve(rows);
                console.log("Query result", rows.length, endTime - startTime, "ms");
            }
            db.close();
        });
    });
}

function isValidDate(date) {
    const parsedDate = new Date(date);
    return !isNaN(parsedDate.getTime());
}

// GET /api/indoor/123/true?startDate=2024-01-01&endDate=2024-02-01
// GET /api/outdoor/789/
app.get('/api/:location(indoor|outdoor)/:id/:average(average)?', async (req, res) => {
    console.debug(req.url, req.ip, req.params, req.query);
    const { location, id, average } = req.params;
    const { startDate, endDate } = req.query;
    try {
        const dbFile = location === "indoor" ? INDOOR_DB : location === "outdoor" ? OUTDOOR_DB : null;
        if (dbFile === null) {
            throw Error(`Unknown location ${location}`);
        }
        const { tableName, valueColumnName } = getDbDataInfo(id);
        const data = await getDbData(dbFile, tableName, valueColumnName,
            average === "average",
            isValidDate(startDate) ? new Date(startDate).toISOString() : null,
            isValidDate(endDate) ? new Date(endDate).toISOString() : null,
        );
        res.json(data);
    } catch (err) {
        res.status(500).json({ error: 'An error occurred', details: err.message });
    }
});

app.get('/api/available_data', async (req, res) => {
    try {
        res.json({
            'temperature_celsius': [{
                name: 'dht22_temperature_celsius',
                locations: ['indoor', 'outdoor']
            }, {
                name: 'bmp280_temperature_celsius',
                locations: ['outdoor']
            }],
            'relative_humidity_percent': [{
                name: 'dht22_relative_humidity_percent',
                locations: ['indoor', 'outdoor']
            }],
            'air_pressure_pa': [{
                name: 'bmp280_air_pressure_pa',
                locations: ['outdoor']
            }]
        });
    } catch (err) {
        res.status(500).json({ error: 'An error occurred', details: err.message });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running at http://localhost:${PORT}`);
});
