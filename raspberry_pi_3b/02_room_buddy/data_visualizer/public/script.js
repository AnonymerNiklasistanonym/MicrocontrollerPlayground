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
function differenceThresholdFilter(valueThreshold, name) {
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

/**
 * Filter data based on a date range.
 *
 * @param {Date|undefined} startDate The start of the date range
 * @param {Date|undefined} endDate The end of the date range
 * @param {string} name Name of the data to be filtered
 * @param {boolean} keepOneOutsideValue Get the previous and the next data point outside of the date range
 */
function dateRangeFilter(startDate, endDate, name, keepOneOutsideValue = true) {
    /**
     * @param {Date} date
     */
    const isInDateRange = date => (startDate !== undefined ? date >= startDate : true) && (endDate !== undefined ? date <= endDate : true)
    return function (current, index, array) {
        const previous = array[index - 1];
        const next = array[index + 1];
        if (isInDateRange(current.timestamp)) {
            return true;
        }
        if (keepOneOutsideValue && ((previous && isInDateRange(previous.timestamp)) || (next && isInDateRange(next.timestamp)))) {
            console.warn(`KEEP DATA BECAUSE IT HAS A PREVIOUS ${isInDateRange(previous.timestamp)}/NEXT ${isInDateRange(next.timestamp)} VALUE THAT IS INSIDE THE DATE RANGE`, current.timestamp, { startDate, endDate })
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
        list.push({ ...list[list.length - 1], timestamp: latestTimestamp });
    }
    return list;
}

async function fetchData() {
    const [indoorResponse, outdoorResponse] = await Promise.all([
        fetch('/api/indoor').then(res => res.json()),
        fetch('/api/outdoor').then(res => res.json())
    ]);
    console.log("read data:", indoorResponse, outdoorResponse)

    return { indoorResponse, outdoorResponse };
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
    const latestTimestampHumidity = getLatestTimestamp(indoorHumidity, outdoorHumidity)

    const colorOutdoor = "blue";
    const colorIndoor = "red";
    return {
        temperatureGraphData:
            [{
                name: "Indoor",
                color: colorIndoor,
                clipped: indoorTemperature,
                filtered: addLatestDataPoint(indoorTemperature.filter(rollingThresholdFilter(5, 1, "indoorTemperature")), latestTimestampTemperature),
            },
            {
                name: "Outdoor",
                color: colorOutdoor,
                clipped: outdoorTemperature,
                filtered: addLatestDataPoint(outdoorTemperature.filter(rollingThresholdFilter(5, 1, "outdoorTemperature")), latestTimestampTemperature),
            }],
        humidityGraphData: [{
            name: "Indoor",
            color: colorIndoor,
            clipped: indoorHumidity,
            filtered: addLatestDataPoint(indoorHumidity.filter(rollingThresholdFilter(5, 0.5, "indoorHumidity")), latestTimestampHumidity),
        },
        {
            name: "Outdoor",
            color: colorOutdoor,
            clipped: outdoorHumidity,
            filtered: addLatestDataPoint(outdoorHumidity.filter(rollingThresholdFilter(5, 0.5, "outdoorHumidity")), latestTimestampHumidity),
        }]
    };
}

/**
 * Render the data in graphs
 * @param {[{name:string;color:string;clipped:[{value:number;timestamp:Date}];filtered:[{value:number;timestamp:Date}]}]} temperatureGraphData
 * @param {[{name:string;color:string;clipped:[{value:number;timestamp:Date}];filtered:[{value:number;timestamp:Date}]}]} humidityGraphData
 * @param {{startDate?: Date;endDate?: Date}} dateClipRange
 */
function render(temperatureGraphData, humidityGraphData, dateClipRange) {
    const { startDate, endDate } = dateClipRange;

    const combinedTemperatureData = temperatureGraphData
        .flatMap(dataset => dataset.filtered);
    const combinedHumidityData = humidityGraphData
        .flatMap(dataset => dataset.filtered);

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

    // Clipping path definition
    function createClippingPath(svg, id, xScale, yScale) {
        const clip = svg.append("defs").append("clipPath")
            .attr("id", id);

        // Use a rectangular clipping area based on the date range
        clip.append("rect")
            .attr("x", startDate ? xScale(startDate) : 0)
            .attr("y", 0)
            .attr("width", endDate ? xScale(endDate) - xScale(startDate || 0) : width)
            .attr("height", height);
    }

    // --- Temperature Graph ---
    const svgTemp = createSvg("temperatureChart");

    const xTempScale = d3.scaleTime()
        .domain([
            startDate || d3.min(combinedTemperatureData, d => d.timestamp),
            endDate || d3.max(combinedTemperatureData, d => d.timestamp)
        ])
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

    const clipIdTemp = "tempClip";
    createClippingPath(svgTemp, clipIdTemp, xTempScale, yTempScale);

    const tempLine = d3.line()
        .x(d => xTempScale(d.timestamp))
        .y(d => yTempScale(d.value));

    for (dataset of temperatureGraphData) {
        svgTemp.append("path")
            .datum(dataset.filtered)
            .attr("d", tempLine)
            .style("stroke", dataset.color)
            .style("fill", "none")
            .attr("clip-path", `url(#${clipIdTemp})`);
        svgTemp.append("path")
            .datum(dataset.clipped)
            .attr("d", tempLine)
            .style("stroke", dataset.color)
            .style("stroke-opacity", 0.3)
            .style("stroke-dasharray", "4,2")
            .style("fill", "none")
            .attr("clip-path", `url(#${clipIdTemp})`);
    }

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

    addLegend(svgTemp, width * 0.75, temperatureGraphData.map(a => `${a.name} [filtered]`), temperatureGraphData.map(a => a.color));

    // --- Humidity Graph ---
    const svgHum = createSvg("humidityChart");

    const xHumScale = d3.scaleTime()
        .domain([
            startDate || d3.min(combinedHumidityData, d => d.timestamp),
            endDate || d3.max(combinedHumidityData, d => d.timestamp)
        ])
        .range([0, width]);

    const yHumScale = d3.scaleLinear()
        .domain([0, 100])
        .range([height, 0]);

    svgHum.append("g")
        .attr("transform", `translate(0,${height})`)
        .call(d3.axisBottom(xHumScale));

    svgHum.append("g").call(d3.axisLeft(yHumScale));

    const clipIdHum = "humClip";
    createClippingPath(svgHum, clipIdHum, xHumScale, yHumScale)

    const humLine = d3.line()
        .x(d => xHumScale(d.timestamp))
        .y(d => yHumScale(d.value));

    for (dataset of humidityGraphData) {
        svgHum.append("path")
            .datum(dataset.filtered)
            .attr("d", humLine)
            .style("stroke", dataset.color)
            .style("fill", "none")
            .attr("clip-path", `url(#${clipIdHum})`);
        svgHum.append("path")
            .datum(dataset.clipped)
            .attr("d", humLine)
            .style("stroke", dataset.color)
            .style("stroke-opacity", 0.3)
            .style("stroke-dasharray", "4,2")
            .style("fill", "none")
            .attr("clip-path", `url(#${clipIdHum})`);
    }

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

    addLegend(svgHum, width * 0.75, humidityGraphData.map(a => `${a.name} [filtered]`), humidityGraphData.map(a => a.color));
}

// Load data
fetchData().then(data => {

    // Filter data based on date range input, then render it
    function filterDataAndRender() {
        const startDateValue = document.getElementById("startDate").value
        const endDateValue = document.getElementById("endDate").value
        const startDate = startDateValue === "" ? undefined : new Date(startDateValue);
        const endDate = endDateValue === "" ? undefined : new Date(endDateValue);

        const filteredData = filterData(data, startDate, endDate)
        render(
            filteredData.temperatureGraphData,
            filteredData.humidityGraphData,
            { data, startDate }
        );
    }

    // Event Listeners
    document.getElementById("startDate").addEventListener("change", filterDataAndRender);
    document.getElementById("endDate").addEventListener("change", filterDataAndRender);

    // Initial Render
    filterDataAndRender()
}).catch(err => console.error(err));
