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

function getDbData(dbFile, tableName, valueColumnName, startDate = null, endDate = null) {
    return new Promise((resolve, reject) => {
        const db = new sqlite3.Database(dbFile);

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

        const whereQueryString = whereQuery.length > 0 ? ` WHERE ${whereQuery.join(" AND ")}` : "";
        const query = `SELECT timestamp, ${valueColumnName} AS value FROM ${tableName}${whereQueryString} ORDER BY timestamp`;

        db.all(query, params, (err, rows) => {
            if (err) {
                reject(err);
            } else {
                resolve(rows);
            }
        });

        db.close();
    });
}

app.get('/api/:location(indoor|outdoor)/:id', async (req, res) => {
    const { location, id } = req.params;
    try {
        const dbFile = location === "indoor" ? INDOOR_DB : location === "outdoor" ? OUTDOOR_DB : null;
        if (dbFile === null) {
            throw Error(`Unknown location ${location}`);
        }
        const { tableName, valueColumnName } = getDbDataInfo(id);
        const data = await getDbData(dbFile, tableName, valueColumnName);
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
