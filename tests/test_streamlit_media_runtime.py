"""Check the HTTP path that AppTest does not exercise."""

import asyncio

import pytest


@pytest.mark.parametrize("encoding", [b"identity", b"gzip"])
@pytest.mark.parametrize("mimetype", ["image/png", "image/jpeg"])
def test_receipt_preview_media_sends_headers_before_image_bytes(encoding, mimetype):
    starlette_app = pytest.importorskip("streamlit.web.server.starlette.starlette_app")
    from starlette.applications import Starlette
    from streamlit.runtime.media_file_storage import MediaFileKind
    from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
    from streamlit.web.server.starlette.starlette_routes import create_media_routes

    storage = MemoryMediaFileStorage("/media")
    content = b"synthetic image payload"
    file_id = storage.load_and_get_id(content, mimetype, MediaFileKind.MEDIA)
    path = storage.get_url(file_id)
    app = Starlette(routes=create_media_routes(storage, None), middleware=starlette_app.create_streamlit_middleware())
    messages = []

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        messages.append(message)

    asyncio.run(app({
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": "GET",
        "scheme": "http", "path": path, "raw_path": path.encode(), "query_string": b"",
        "headers": [(b"accept-encoding", encoding)], "client": ("127.0.0.1", 1234),
        "server": ("127.0.0.1", 8501), "root_path": "",
    }, receive, send))
    assert messages[0]["type"] == "http.response.start"
    assert messages[0]["status"] == 200
    assert b"".join(item.get("body", b"") for item in messages) == content
