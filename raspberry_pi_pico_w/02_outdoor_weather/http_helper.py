import ujson


# Common HTTP statuses
_HTTP_STATUS_OK_CODE = const(200)
_HTTP_STATUS_OK_MESSAGE = const("OK")
HTTP_STATUS_OK = (_HTTP_STATUS_OK_CODE, _HTTP_STATUS_OK_MESSAGE)
_HTTP_STATUS_FOUND_CODE = const(302)
_HTTP_STATUS_FOUND_MESSAGE = const("Found")
HTTP_STATUS_FOUND = (_HTTP_STATUS_FOUND_CODE, _HTTP_STATUS_FOUND_MESSAGE)
_HTTP_STATUS_NOT_MODIFIED_CODE = const(304)
_HTTP_STATUS_NOT_MODIFIED_MESSAGE = const("Not Modified")
HTTP_STATUS_NOT_MODIFIED = (_HTTP_STATUS_NOT_MODIFIED_CODE, _HTTP_STATUS_NOT_MODIFIED_MESSAGE)
_HTTP_STATUS_NOT_FOUND_CODE = const(404)
_HTTP_STATUS_NOT_FOUND_MESSAGE = const("Not Found")
HTTP_STATUS_NOT_FOUND = (_HTTP_STATUS_NOT_FOUND_CODE, _HTTP_STATUS_NOT_FOUND_MESSAGE)

# Common HTTP content types
HTTP_CONTENT_TYPE_HTML = const("text/html")
HTTP_CONTENT_TYPE_JSON = const("application/json")
HTTP_CONTENT_TYPE_JS = const("application/javascript")
HTTP_CONTENT_TYPE_TEXT = const("text/plain")
HTTP_CONTENT_TYPE_CSS = const("text/css")


def generate_http_response(
    body: str | None,
    content_type: str=HTTP_CONTENT_TYPE_HTML,
    status: tuple[int, str]=HTTP_STATUS_OK,
    etag: str | None=None,
    location: str | None=None,
    maxAge: int | None=None,
) -> str:
    """
    This generates a generic HTTP response with support for some advanced features.
    URL forwarding using a location.
    ETag for smaller messages.
    Cache-Control max-age for caching of static/not frequent changing responses.
    """
    response = [f"HTTP/1.1 {status[0]} {status[1]}"]
    if location is not None:
        response.append(f"Location: {location}")
    if body is not None:
        response.append(f"Content-Type: {content_type}")
    if etag is not None:
        response.append(f'ETag: "{etag}"')
    if maxAge is not None:
        response.append(f"Cache-Control: public, max-age={maxAge}")
    response.append("")
    if body is None:
        response.append("")
    else:
        response.append(body)
    return "\r\n".join(response)


def generate_etag(data) -> str:
    """
    This generates an ETag/hash of some given data.
    If a client sends a request with the previous response ETag and there is no change
    a not modified response can be sent instead of the same data again.
    """
    return str(hash(ujson.dumps(data)))
