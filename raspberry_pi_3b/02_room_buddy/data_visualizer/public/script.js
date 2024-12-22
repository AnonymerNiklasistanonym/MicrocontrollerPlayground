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
    const availableData = await fetch('/api/available_data').then(res => res.json());
    const data = {};
    for (const [category, sensors] of Object.entries(availableData)) {
        data[category] = {};
        for (const sensor of sensors) {
            const {name,locations} = sensor;
            for (const location of locations) {
                data[category][`${name} (${location})`] = await fetch(`/api/${location}/${name}`).then(res => res.json());
            }
        }
    }
    console.log(data);
    return data;
}

function addIntermediateEntries(data, intermediateTimeDiff = 30 * 60 * 1000) {
    let result = [];

    for (let i = 0; i < data.length - 1; i++) {
        const current = data[i];
        const next = data[i + 1];

        result.push(current); // Always include the current entry

        // Calculate time difference between current and next timestamps
        const currentTime = current.timestamp.getTime();
        const nextTime = next.timestamp.getTime();

        // If the difference exceeds x minutes, add intermediate entry
        if (nextTime - currentTime > intermediateTimeDiff) {
            result.push({
                value: current.value,
                timestamp: new Date(nextTime - intermediateTimeDiff)
            });
        }
    }

    // Always include the last entry
    if (data.length > 0) {
        result.push(data[data.length - 1]);
    }

    return result;
}

function filterData(data, startDate, endDate) {

    const filteredData = {};
    for (const [category, sensor_data] of Object.entries(data)) {
        filteredData[category] = {};
        for (const [sensor, sensor_data_entry] of Object.entries(sensor_data)) {
            filteredData[category][sensor] = {};
            filteredData[category][sensor]["clipped"] = sensor_data_entry.map(a => ({
                ...a,
                timestamp: new Date(a.timestamp),
            })).filter(dateRangeFilter(startDate, endDate, sensor));
            if (category === "temperature_celsius") {
                if (sensor.startsWith("dht22")) {
                    filteredData[category][sensor]["clipped"] = filteredData[category][sensor]["clipped"].filter(clipFilter(-40, 80, sensor));
                }
                if (sensor.startsWith("bmp280")) {
                    filteredData[category][sensor]["clipped"] = filteredData[category][sensor]["clipped"].filter(clipFilter(-40, 85, sensor));
                }
            }
            if (category === "relative_humidity_percent") {
                if (sensor.startsWith("dht22")) {
                    filteredData[category][sensor]["clipped"] = filteredData[category][sensor]["clipped"].filter(clipFilter(0, 100, sensor));
                }
            }
            if (category === "air_pressure_pa") {
                if (sensor.startsWith("bmp280")) {
                    filteredData[category][sensor]["clipped"] = filteredData[category][sensor]["clipped"].filter(clipFilter(300 * 100, 1100 * 100, sensor));
                }
            }
            filteredData[category][sensor]["filtered"] = addIntermediateEntries(filteredData[category][sensor]["clipped"]).filter(rollingThresholdFilter(5, 1, sensor));
        }
    }

    return filteredData
}

/**
 * Render the data in graphs
 * @param {[{name:string;color:string;clipped:[{value:number;timestamp:Date}];filtered:[{value:number;timestamp:Date}]}]} temperatureGraphData
 * @param {[{name:string;color:string;clipped:[{value:number;timestamp:Date}];filtered:[{value:number;timestamp:Date}]}]} humidityGraphData
 * @param {{startDate?: Date;endDate?: Date}} dateClipRange
 */
function render(data, dateClipRange) {
    const { startDate, endDate } = dateClipRange;

    // Dimensions and margins for both graphs
    const margin = { top: 20, right: 20, bottom: 40, left: 100 },
        width = 800 - margin.left - margin.right,
        height = 300 - margin.top - margin.bottom;

    function removeElement(id) {
        var elem = document.getElementById(id);
        if (elem !== null) {
            elem.parentNode.removeChild(elem);
        }
    }

    // Function to create an SVG container
    function createSvg(id) {
        removeElement(id);
        const chartsDiv = document.getElementById("charts");
        const chart = document.createElement("div");
        chart.id = id;
        chartsDiv.appendChild(chart);
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

    for (const [category, sensorData] of Object.entries(data)) {
        const combinedFilteredData = Object.entries(sensorData).flatMap(([name, dataset]) => dataset.filtered);

        const svg = createSvg(`${category}Chart`);

        const xTimeScale = d3.scaleTime()
            .domain([
                startDate || d3.min(combinedFilteredData, d => d.timestamp),
                endDate || d3.max(combinedFilteredData, d => d.timestamp)
            ])
            .range([0, width]);

        let yValueScale;
        let unit;

        if (category === "temperature_celsius") {
            unit = "Temperature (°C)";
            yValueScale = d3.scaleLinear()
            .domain([
                d3.min(combinedFilteredData, d => d.value - 5),
                d3.max(combinedFilteredData, d => d.value + 5),
            ])
            .range([height, 0]);
        }
        if (category === "relative_humidity_percent") {
            unit = "Relative Humidity (%)";
            yValueScale = d3.scaleLinear()
                .domain([
                    0,
                    100,
                ])
                .range([height, 0]);
        }
        if (category === "air_pressure_pa") {
            unit = "Air Pressure (Pa)";
            yValueScale = d3.scaleLinear()
                .domain([
                    d3.min(combinedFilteredData, d => d.value - 500),
                    d3.max(combinedFilteredData, d => d.value + 500),
                ])
                .range([height, 0]);
        }

        svg.append("g")
            .attr("transform", `translate(0,${height})`)
            .call(d3.axisBottom(xTimeScale));

        svg.append("g").call(d3.axisLeft(yValueScale));

        const clipId = `${category}Clip`;
        createClippingPath(svg, clipId, xTimeScale, yValueScale);

        const line = d3.line()
            .x(d => xTimeScale(d.timestamp))
            .y(d => yValueScale(d.value));

        const colors = d3.scaleOrdinal(d3.schemeCategory10);
        let colorId = 0;
        const legendNames = [];
        const legendColors = [];
        for (const [name, dataset] of Object.entries(sensorData)) {
            const color = colors(colorId);
            colorId += 1;
            legendNames.push(name);
            legendColors.push(color);
            console.warn({ name, color, dataset});
            svg.append("path")
                .datum(dataset.filtered)
                .attr("d", line)
                .style("stroke", color)
                .style("fill", "none")
                .attr("clip-path", `url(#${clipId})`);
            svg.append("path")
                .datum(dataset.clipped)
                .attr("d", line)
                .style("stroke", color)
                .style("stroke-opacity", 0.3)
                .style("stroke-dasharray", "4,2")
                .style("fill", "none")
                .attr("clip-path", `url(#${clipId})`);
        }
        svg.append("text")
            .attr("x", width / 2)
            .attr("y", height + margin.bottom)
            .attr("text-anchor", "middle")
            .text("Time");

        svg.append("text")
            .attr("transform", "rotate(-90)")
            .attr("x", -height / 2)
            .attr("y", -margin.left / 2)
            .attr("text-anchor", "middle")
            .text(unit);

        addLegend(svg, width * 0.75, legendNames, legendColors);
    }
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
        render(filteredData, { startDate, endDate });
    }

    // Event Listeners
    document.getElementById("startDate").addEventListener("change", filterDataAndRender);
    document.getElementById("endDate").addEventListener("change", filterDataAndRender);

    // Initial Render
    filterDataAndRender()
}).catch(err => console.error(err));
