const ip = "192.168.2.166"
const url = `http://${ip}/json_measurements`
let startTime = performance.now();
fetch(url)
  .then(response => {
    const endTime = performance.now();
    const responseTime = endTime - startTime;
    console.log("First response:", response, `${(endTime - startTime).toFixed(2)} ms`);
    const etag = response.headers.get('ETag');
    startTime = performance.now();
    return fetch(url, {
      headers: {'If-None-Match': etag} // Send the ETag on the second request
    });
  })
  .then(response => {
    const endTime = performance.now();
    const responseTime = endTime - startTime;
    console.log("Second response:", response, `${(endTime - startTime).toFixed(2)} ms`);
    if (response.status === 304) {
      console.log('Resource not modified, using cached data');
      return null;
    }
    return response.json(); // Unexpected but parse new data
  })
  .then(data => {
    if (data !== null) {
      console.log('Updated data:', data);
    }
  })
  .catch(error => console.error('Error:', error));
