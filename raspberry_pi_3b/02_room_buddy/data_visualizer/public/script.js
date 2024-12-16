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
// Fetch and visualize data
async function fetchData() {
    const [indoorResponse, outdoorResponse] = await Promise.all([
        fetch('/api/indoor').then(res => res.json()),
        fetch('/api/outdoor').then(res => res.json())
    ]);

    console.log("read data:", indoorResponse, outdoorResponse)
    // Extract temperature and humidity data
    const indoorTemperature = indoorResponse.temperatureData
        .filter(d => d.temperature_celsius >= -40 && d.temperature_celsius <= 80)
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.temperature_celsius
        }));
    const indoorHumidity = indoorResponse.humidityData
        .filter(d => d.relative_humidity_percent >= 0 && d.relative_humidity_percent <= 100)
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.relative_humidity_percent
        }));

    const outdoorTemperature = outdoorResponse.temperatureData
        .filter(d => d.temperature_celsius >= -40 && d.temperature_celsius <= 80)
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.temperature_celsius
        }));
    const outdoorHumidity = outdoorResponse.humidityData
        .filter(d => d.relative_humidity_percent >= 0 && d.relative_humidity_percent <= 100)
        .map(d => ({
            timestamp: new Date(d.timestamp),
            value: d.relative_humidity_percent
        }));

    visualizeData(indoorTemperature, outdoorTemperature, indoorHumidity, outdoorHumidity);
}

function visualizeData(indoorTemperature, outdoorTemperature, indoorHumidity, outdoorHumidity) {
    const combinedTemperatureData = [...indoorTemperature, ...outdoorTemperature];
    const combinedHumidityData = [...indoorHumidity, ...outdoorHumidity];

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
        .datum(indoorTemperature)
        .attr("d", tempLine)
        .style("stroke", "blue")
        .style("fill", "none");

    svgTemp.append("path")
        .datum(outdoorTemperature)
        .attr("d", tempLine)
        .style("stroke", "red")
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
    addLegend(svgTemp, width, ["Indoor", "Outdoor"], ["blue", "red"]);

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
        .datum(indoorHumidity)
        .attr("d", humLine)
        .style("stroke", "blue")
        .style("fill", "none");

    svgHum.append("path")
        .datum(outdoorHumidity)
        .attr("d", humLine)
        .style("stroke", "red")
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
    addLegend(svgHum, width, ["Indoor", "Outdoor"], ["blue", "red"]);
}

// Load data
fetchData();