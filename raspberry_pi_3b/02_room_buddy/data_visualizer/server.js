const express = require('express');
const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const app = express();
const PORT = 3000;

// Database files
const INDOOR_DB = '../data/indoor_weather.db';
const OUTDOOR_DB = '../data/outdoor_weather.db';
const TABLE_NAME_TEMPERATURE = 'temperature_data';
const COLUMN_NAME_TEMPERATURE = 'temperature_celsius';
const TABLE_NAME_HUMIDITY = 'relative_humidity_data';
const COLUMN_NAME_HUMIDITY = 'relative_humidity_percent';
const OUTDOOR_DB_TABLE_NAMES = {
    DHT22_TEMPERATURE: 'dht22_temperature_celsius',
    DHT22_RELATIVE_HUMIDITY: 'dht22_relative_humidity_percent',
    BMP280_TEMPERATURE: 'bmp280_temperature_celsius',
    BMP280_AIR_PRESSURE: 'bmp280_air_pressure_pa',
};
const OUTDOOR_DB_COLUMN_NAMES = {
    DHT22_TEMPERATURE: 'temperature_celsius',
    DHT22_RELATIVE_HUMIDITY: 'relative_humidity_percent',
    BMP280_TEMPERATURE: 'temperature_celsius',
    BMP280_AIR_PRESSURE: 'air_pressure_pa',
};

// Serve static files (for D3.js and the chart)
app.use(express.static(path.join(__dirname, 'public')));

// Helper function to query data from a database
function getWeatherData(dbFile, tableName, columnName, callback) {
    const db = new sqlite3.Database(dbFile);
    db.all(`SELECT timestamp, ${columnName} FROM ${tableName} ORDER BY timestamp`, (err, rows) => {
        if (err) {
            callback(err, null);
        } else {
            callback(null, rows);
        }
    });
    db.close();
}

// API endpoint for indoor data
app.get('/api/indoor', (req, res) => {
    getWeatherData(INDOOR_DB, TABLE_NAME_TEMPERATURE, COLUMN_NAME_TEMPERATURE, (err, temperatureData) => {
        if (err) {
            res.status(500).send({ error: 'Failed to fetch outdoor data.' });
        } else {
            getWeatherData(INDOOR_DB, TABLE_NAME_HUMIDITY, COLUMN_NAME_HUMIDITY, (err, humidityData) => {
                if (err) {
                    res.status(500).send({ error: 'Failed to fetch outdoor data.' });
                } else {
                    res.json({
                        temperatureData,
                        humidityData
                    });
                }
            });
        }
    });
});

// API endpoint for outdoor data
app.get('/api/outdoor', (req, res) => {
    // TODO Support more values, add bmp280 support
    getWeatherData(OUTDOOR_DB, OUTDOOR_DB_TABLE_NAMES.DHT22_TEMPERATURE, OUTDOOR_DB_COLUMN_NAMES.DHT22_TEMPERATURE, (err, temperatureData) => {
        if (err) {
            res.status(500).send({ error: 'Failed to fetch outdoor data.' });
        } else {
            getWeatherData(OUTDOOR_DB, OUTDOOR_DB_TABLE_NAMES.DHT22_RELATIVE_HUMIDITY, OUTDOOR_DB_COLUMN_NAMES.DHT22_RELATIVE_HUMIDITY, (err, humidityData) => {
                if (err) {
                    res.status(500).send({ error: 'Failed to fetch outdoor data.' });
                } else {
                    res.json({
                        temperatureData,
                        humidityData
                    });
                }
            });
        }
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running at http://localhost:${PORT}`);
});
