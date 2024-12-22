import ujson


HTTP_STATUS_OK = (200, "OK")
HTTP_STATUS_NOT_MODIFIED = (304, "Not Modified")
HTTP_STATUS_NOT_FOUND = (404, "Not Found")

HTTP_CONTENT_TYPE_HTML = "text/html"
HTTP_CONTENT_TYPE_JSON = "application/json"
HTTP_CONTENT_TYPE_TEXT = "text/plain"


def generate_http_response(body, content_type=HTTP_CONTENT_TYPE_HTML, status=HTTP_STATUS_OK, etag=None):
    response = [f"HTTP/1.1 {status[0]} {status[1]}"]
    if body is not None:
        response.append(f"Content-Type: {content_type}")
    if etag is not None:
        response.append(f'ETag: "{etag}"')
    response.append("")
    if status[0] == 304 or body is None:
        response.append("")
    else:
        response.append(body)
    return "\r\n".join(response)


def generate_etag(data):
    return str(hash(ujson.dumps(data)))


