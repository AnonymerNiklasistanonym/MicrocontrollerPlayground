function addLegend(svg, width, labels, colors) {
    // Create a legend group
    const legend = svg.append("g")
        .attr("class", "legend")
        .attr("transform", `translate(${width - 100}, 10)`); // Position the legend near the top right

    labels.forEach((label, i) => {
        const legendRow = legend.append("g")
            .attr("transform", `translate(0, ${i * 20})`);

        // Add colored rectangles
        legendRow.append("rect")
            .attr("width", 10)
            .attr("height", 10)
            .attr("fill", colors[i]);

        // Add text
        legendRow.append("text")
            .attr("x", 20)
            .attr("y", 10)
            .attr("text-anchor", "start")
            .attr("font-size", "12px")
            .text(label);
    });
}
function clipFilter(minThreshold, maxThreshold, name) {
    return (current) => {
        if (current.value >= minThreshold && current.value <= maxThreshold) {
            return true;
        }
        console.log(`Filter (clip) ${name} value ${current.value} (minThreshold=${minThreshold},maxThreshold=${maxThreshold})`)
        return false;
    };
}
function rollingThresholdFilter(windowSize, thresholdFactor, name) {
    return (current, index, array) => {
        const start = Math.max(0, index - Math.floor(windowSize / 2));
        const end = Math.min(array.length, index + Math.ceil(windowSize / 2));
        const window = array.slice(start, end).map(a => a.value);

        const mean = d3.mean(window);
        const stdDev = d3.deviation(window);

        const lowerLimit = mean - thresholdFactor * stdDev;
        const upperLimit = mean + thresholdFactor * stdDev;

        if (current.value >= lowerLimit && current.value <= upperLimit) {
            return true;
        }
        console.log(`Filter (rolling threshold) ${name} value ${current.value} (windowSize=${windowSize},thresholdFactor=${thresholdFactor},window=${window.join(',')},lowerLimit=${lowerLimit},upperLimit=${upperLimit})`)
        return false;
    };
}
function differenceThresholdFilter(valueThreshold , name) {
    let lastValid = null;

    return function (current, index, array) {
        if (index === 0 || Math.abs(current.value - lastValid.value) <= valueThreshold) {
            lastValid = current;
            return true;
        }
        console.log(`Filter (difference threshold) ${name} value ${current.value} (valueThreshold=${valueThreshold},lastValid=${lastValid})`)
        return false;
    };
}
function dateRangeFilter(startDate, endDate , name) {
    return function (current, index, array) {
        if ((!isNaN(startDate) ? current.timestamp >= startDate : true) && (!isNaN(endDate) ? current.timestamp <= endDate : true)) {
            return true;
        }
        console.log(`Filter (date range) ${name} value ${current.value} (startDate=${startDate},endDate=${endDate})`)
        return false;
    };
}
function getLatestTimestamp(...lists) {
    let latest = null;

    lists.forEach(list => {
        list.forEach(item => {
            if (!latest || item.timestamp > latest) {
                latest = item.timestamp;
            }
        });
    });

    return latest ? latest : null;
}
function addLatestDataPoint(list, latestTimestamp) {
    if (latestTimestamp !== null && list.length > 0 && list[list.length - 1].timestamp !== latestTimestamp) {
        list.push({...list[list.length - 1], timestamp: latestTimestamp});
    }
    return list;
}

async function fetchData() {
    const [indoorResponse, outdoorResponse] = await Promise.all([
        fetch('/api/indoor').then(res => res.json()),
        fetch('/api/outdoor').then(res => res.json())
    ]);
    console.log("read data:", indoorResponse, outdoorResponse)

    return {indoorResponse,outdoorResponse};
}

function filterData(data, startDate, endDate) {
    const dht22MinTemperatureCelsius = -40
    const dht22MaxTemperatureCelsius = 80
    const dht22MinRelativeHumidityPercent = 0
    const dht22MaxRelativeHumidityPercent = 100

    const indoorTemperature = data.indoorResponse.temperatureData
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.temperature_celsius
        }))
        .filter(clipFilter(dht22MinTemperatureCelsius, dht22MaxTemperatureCelsius, "indoorTemperature"))
        .filter(dateRangeFilter(startDate, endDate, "indoorTemperature"));
    const indoorHumidity = data.indoorResponse.humidityData
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.relative_humidity_percent
        }))
        .filter(clipFilter(dht22MinRelativeHumidityPercent, dht22MaxRelativeHumidityPercent, "indoorHumidity"))
        .filter(dateRangeFilter(startDate, endDate, "indoorHumidity"));

    const outdoorTemperature = data.outdoorResponse.temperatureData
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.temperature_celsius
        }))
        .filter(clipFilter(dht22MinTemperatureCelsius, dht22MaxTemperatureCelsius, "outdoorTemperature"))
        .filter(dateRangeFilter(startDate, endDate, "outdoorTemperature"));
    const outdoorHumidity = data.outdoorResponse.humidityData
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.relative_humidity_percent
        }))
        .filter(clipFilter(dht22MinRelativeHumidityPercent, dht22MaxRelativeHumidityPercent, "outdoorHumidity"))
        .filter(dateRangeFilter(startDate, endDate, "outdoorHumidity"));

    const latestTimestampTemperature = getLatestTimestamp(indoorTemperature, outdoorTemperature)
    const latestTimestampHumidity = getLatestTimestamp( indoorHumidity, outdoorHumidity)

    return {
        indoorTemperature:
        {
            clipped: indoorTemperature,
            filtered: addLatestDataPoint(indoorTemperature.filter(rollingThresholdFilter(5, 1, "indoorTemperature")), latestTimestampTemperature),
        },
        outdoorTemperature: {
            clipped: outdoorTemperature,
            filtered: addLatestDataPoint(outdoorTemperature.filter(rollingThresholdFilter(5, 1, "outdoorTemperature")), latestTimestampTemperature),
        },
        indoorHumidity: {
            clipped: indoorHumidity,
            filtered: addLatestDataPoint(indoorHumidity.filter(rollingThresholdFilter(5, 0.5, "indoorHumidity")), latestTimestampHumidity),
        },
        outdoorHumidity: {
            clipped: outdoorHumidity,
            filtered: addLatestDataPoint(outdoorHumidity.filter(rollingThresholdFilter(5, 0.5, "outdoorHumidity")), latestTimestampHumidity),
        },
    };
}

function render(indoorTemperature, outdoorTemperature, indoorHumidity, outdoorHumidity) {
    const combinedTemperatureData = [...indoorTemperature.filtered, ...outdoorTemperature.filtered];
    const combinedHumidityData = [...indoorHumidity.filtered, ...outdoorHumidity.filtered];

    // Dimensions and margins for both graphs
    const margin = { top: 20, right: 20, bottom: 30, left: 80 },
        width = 800 - margin.left - margin.right,
        height = 300 - margin.top - margin.bottom;

    // Function to create an SVG container
    function createSvg(id) {
        return d3.select(`#${id}`).html("").append("svg")
            .attr("width", width + margin.left + margin.right)
            .attr("height", height + margin.top + margin.bottom)
            .append("g")
            .attr("transform", `translate(${margin.left},${margin.top})`);
    }

    // --- Temperature Graph ---
    const svgTemp = createSvg("temperatureChart");

    const xTempScale = d3.scaleTime()
        .domain(d3.extent(combinedTemperatureData, d => d.timestamp))
        .range([0, width]);

    const yTempScale = d3.scaleLinear()
        .domain([
            d3.min(combinedTemperatureData, d => d.value) - 5,
            d3.max(combinedTemperatureData, d => d.value) + 5
        ])
        .range([height, 0]);

    svgTemp.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(xTempScale));

    svgTemp.append("g").call(d3.axisLeft(yTempScale));

    const tempLine = d3.line()
        .x(d => xTempScale(d.timestamp))
        .y(d => yTempScale(d.value));

    svgTemp.append("path")
        .datum(indoorTemperature.filtered)
        .attr("d", tempLine)
        .style("stroke", "blue")
        .style("fill", "none");

    svgTemp.append("path")
        .datum(outdoorTemperature.filtered)
        .attr("d", tempLine)
        .style("stroke", "red")
        .style("fill", "none");

    svgTemp.append("path")
        .datum(indoorTemperature.clipped)
        .attr("d", tempLine)
        .style("stroke", "blue")
        .style("stroke-opacity", 0.3)
        .style("stroke-dasharray", "4,2")
        .style("fill", "none");

    svgTemp.append("path")
        .datum(outdoorTemperature.clipped)
        .attr("d", tempLine)
        .style("stroke", "red")
        .style("stroke-opacity", 0.3)
        .style("stroke-dasharray", "4,2")
        .style("fill", "none");

    svgTemp.append("text")
        .attr("x", width / 2)
        .attr("y", height + margin.bottom)
        .attr("text-anchor", "middle")
        .text("Time");

    svgTemp.append("text")
        .attr("transform", "rotate(-90)")
        .attr("x", -height / 2)
        .attr("y", -margin.left + 40)
        .attr("text-anchor", "middle")
        .text("Temperature (°C)");

    // Add legend for temperature chart
    addLegend(svgTemp, width, ["Indoor (filtered)", "Outdoor (filtered)"], ["blue", "red"]);

    // --- Humidity Graph ---
    const svgHum = createSvg("humidityChart");

    const xHumScale = d3.scaleTime()
        .domain(d3.extent(combinedHumidityData, d => d.timestamp))
        .range([0, width]);

    const yHumScale = d3.scaleLinear()
        .domain([
            d3.min(combinedHumidityData, d => d.value) - 5,
            d3.max(combinedHumidityData, d => d.value) + 5
        ])
        .range([height, 0]);

    svgHum.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(xHumScale));

    svgHum.append("g").call(d3.axisLeft(yHumScale));

    const humLine = d3.line()
        .x(d => xHumScale(d.timestamp))
        .y(d => yHumScale(d.value));

    svgHum.append("path")
        .datum(indoorHumidity.filtered)
        .attr("d", humLine)
        .style("stroke", "blue")
        .style("fill", "none");

    svgHum.append("path")
        .datum(outdoorHumidity.filtered)
        .attr("d", humLine)
        .style("stroke", "red")
        .style("fill", "none");

    svgHum.append("path")
        .datum(indoorHumidity.clipped)
        .attr("d", humLine)
        .style("stroke", "blue")
        .style("stroke-opacity", 0.3)
        .style("stroke-dasharray", "4,2")
        .style("fill", "none");

    svgHum.append("path")
        .datum(outdoorHumidity.clipped)
        .attr("d", humLine)
        .style("stroke", "red")
        .style("stroke-opacity", 0.3)
        .style("stroke-dasharray", "4,2")
        .style("fill", "none");

    svgHum.append("text")
        .attr("x", width / 2)
        .attr("y", height + margin.bottom)
        .attr("text-anchor", "middle")
        .text("Time");

    svgHum.append("text")
        .attr("transform", "rotate(-90)")
        .attr("x", -height / 2)
        .attr("y", -margin.left + 40)
        .attr("text-anchor", "middle")
        .text("Humidity (%)");

    // Add legend for humidity chart
    addLegend(svgHum, width, ["Indoor (filtered)", "Outdoor (filtered)"], ["blue", "red"]);
}

// Load data
fetchData().then(data => {

    function refilterData() {
        const startDate = new Date(document.getElementById("startDate").value);
        const endDate = new Date(document.getElementById("endDate").value);

        refilteredData = filterData(data, startDate, endDate)
        render(
            refilteredData.indoorTemperature,
            refilteredData.outdoorTemperature,
            refilteredData.indoorHumidity,
            refilteredData.outdoorHumidity,
        );
    }

    // Event Listeners
    document.getElementById("startDate").addEventListener("change", refilterData);
    document.getElementById("endDate").addEventListener("change", refilterData);

    // Initial Render
    const filteredData = filterData(data)
    render(
        filteredData.indoorTemperature,
        filteredData.outdoorTemperature,
        filteredData.indoorHumidity,
        filteredData.outdoorHumidity,
    );
}).catch(err => consoler.error(err));
