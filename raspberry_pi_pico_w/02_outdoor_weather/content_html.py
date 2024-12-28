HTML_CSS_DEFAULT = const(
    """
    table {
        width: 50%;
        margin: 20px;
        border-collapse: collapse;
    }
    th, td {
        padding: 8px;
        text-align: left;
        border-bottom: 1px solid #ddd;
    }
    th {
        background-color: #f2f2f2;
    }
    h2 {
        color: #333;
    }
"""
)

HTML_JS_DYNAMIC_DATA_DEFAULT = const(
    """
    // Function to get URL parameters
    function getUrlParameter(name) {
        return new URLSearchParams(window.location.search).get(name);
    }
    
    // Function to render JSON data
    function renderJsonData(jsonData, endpoint) {
         // Set the page title
        document.title = jsonData.title;
        const titleH1 = document.getElementById('title');
        titleH1.textContent = `${jsonData.title} (/${endpoint})`;
        console.log(document.title, titleH1, titleH1.textContent);

        // Get the content div
        const contentDiv = document.getElementById('content');

        // Loop through each section
        jsonData.sections.forEach(section => {
            // Create section container
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'section';

            // Add section title
            const title = document.createElement('h2');
            title.textContent = section.title;
            sectionDiv.appendChild(title);
            
            // Add section data
            const data = section.data;
            if (!Array.isArray(data)) {
                for (const key in data) {
                    const value = data[key];

                    // Create a container for each key-value pair
                    const dataDiv = document.createElement('div');
                    dataDiv.className = 'data-entry';

                    // Add the key
                    const keySpan = document.createElement('strong');
                    keySpan.textContent = `${key}: `;
                    dataDiv.appendChild(keySpan);

                    // Check if the value is an object (e.g., Readings)
                    if (typeof value === 'object' && !Array.isArray(value)) {
                        // Render nested objects like Readings
                        const nestedTable = document.createElement('table');
                        nestedTable.border = 1;

                        // Loop through nested keys
                        for (const nestedKey in value) {
                            const row = document.createElement('tr');

                            // Key cell
                            const keyCell = document.createElement('td');
                            keyCell.textContent = nestedKey;
                            row.appendChild(keyCell);

                            // Value cell (stringified JSON for nested objects)
                            const valueCell = document.createElement('td');
                            valueCell.textContent = JSON.stringify(value[nestedKey]);
                            row.appendChild(valueCell);

                            nestedTable.appendChild(row);
                        }
                        dataDiv.appendChild(nestedTable);
                    } else {
                        // Render simple values
                        const valueSpan = document.createElement('span');
                        valueSpan.textContent = value;
                        dataDiv.appendChild(valueSpan);
                    }

                    sectionDiv.appendChild(dataDiv);
                }
            } else {
                // Render tables
                const sectionTable = document.createElement('table');
                sectionTable.border = 1;

                // Loop through nested keys
                for (const row of data) {
                    const rowElement = document.createElement('tr');

                    for (const col of row) {
                        const colElement = document.createElement('td');
                        colElement.textContent = col;
                        rowElement.appendChild(colElement);
                    }

                    sectionTable.appendChild(rowElement);
                }
                sectionDiv.appendChild(sectionTable);
            }

            // Append the section to the content div
            contentDiv.appendChild(sectionDiv);
        });
    }

    // Get 'endpoint' parameter from URL (e.g., ?endpoint=data)
    const endpoint = getUrlParameter('endpoint');
    const url = `/${endpoint}`;
    
    const loadButton = document.getElementById('loadButton');

    if (endpoint) {
        console.log("endpoint:", endpoint);

        loadButton.disabled = false;
        loadButton.textContent = `Open JSON data from /${endpoint}`;

        loadButton.addEventListener('click', () => {
            window.open(url, '_blank');
        });
    } else {
        console.error("No endpoint defined");

        loadButton.disabled = true;
        loadButton.textContent = "No endpoint detected";
    }

    fetch(url)
        .then(response => response.json())
        .then(data => {
            console.log("data", data);
            renderJsonData(data, endpoint);
        })
        .catch(error => {
            console.error('Error fetching JSON:', error);
        });
"""
)