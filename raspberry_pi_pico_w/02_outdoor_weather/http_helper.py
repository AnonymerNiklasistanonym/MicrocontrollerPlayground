def generate_http_response(body, content_type="text/html", status=(200, "OK")):
    return f"HTTP/1.1 {status[0]} {status[1]}\r\nContent-Type: {content_type}\r\n\r\n{body}"
