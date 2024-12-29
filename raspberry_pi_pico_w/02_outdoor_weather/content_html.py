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
    function getUrlParameter(name) {
        return new URLSearchParams(window.location.search).get(name);
    }
    
    function renderTableArray(dataArray) {
        const table = document.createElement('table');
        table.border = 1;
        for (const row of dataArray) {
            const rowElement = document.createElement('tr');
            for (const col of row) {
                const colElement = document.createElement('td');
                colElement.textContent = col;
                rowElement.appendChild(colElement);
            }
            table.appendChild(rowElement);
        }
        return table;
    }
    
    function renderTableObject(dataObject) {
        const table = document.createElement('table');
        table.border = 1;
        for (const [key, value] of Object.entries(dataObject)) {
            const rowElement = document.createElement('tr');
            const colElementKey = document.createElement('td');
            colElementKey.textContent = key;
            rowElement.appendChild(colElementKey);
            const colElementValue = document.createElement('td');
            colElementValue.textContent = typeof(value) === "string" ? value : JSON.stringify(value);
            rowElement.appendChild(colElementValue);
            table.appendChild(rowElement);
        }
        return table;
    }
    
    function renderListObject(dataObject) {
        const children = [];
        for (const [key, value] of Object.entries(dataObject)) {
            const dataDiv = document.createElement('div');
            dataDiv.className = 'data-entry';

            const keySpan = document.createElement('strong');
            keySpan.textContent = `${key}: `;
            dataDiv.appendChild(keySpan);

            // If the value is an object stringify it's keys
            if (typeof value === 'object' && !Array.isArray(value)) {
                dataDiv.appendChild(renderTableObject(value));
            } else if (typeof value === 'object' && Array.isArray(value)) {
                dataDiv.appendChild(renderTableArray(value));
            } else {
                const valueSpan = document.createElement('span');
                valueSpan.textContent = value;
                dataDiv.appendChild(valueSpan);
            }

            children.push(dataDiv);
        }
        return children;
    }
    
    function renderJsonData(jsonData, endpoint) {
        document.title = jsonData.title;
        
        const titleH1 = document.getElementById('title');
        titleH1.textContent = `${jsonData.title} (/${endpoint})`;

        const contentDiv = document.getElementById('content');
        jsonData.sections.forEach(section => {
            const sectionDiv = document.createElement('div');
            sectionDiv.className = 'section';
            const title = document.createElement('h2');
            title.textContent = section.title;
            sectionDiv.appendChild(title);
            
            const data = section.data;
            if (!Array.isArray(data)) {
                for (const childList of renderListObject(data)) {
                    sectionDiv.appendChild(childList);
                }
            } else {
                sectionDiv.appendChild(renderTableArray(data));
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
        loadButton.disabled = false;
        loadButton.textContent = `Open JSON data from /${endpoint}`;
        loadButton.addEventListener('click', () => {
            window.open(url, '_blank');
        });
    } else {
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