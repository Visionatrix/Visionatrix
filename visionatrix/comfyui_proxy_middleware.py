import asyncio
import contextlib
import re
import urllib.parse

import httpx
import websockets
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send

# "/scripts", "/kjweb_async", "/ollama" are here temporarily until someone fixes the situation upstream.
PATHS_TO_PROXY = ["/comfy", "/scripts", "/kjweb_async", "/ollama"]
USERDATA_MOVE_PATTERN = re.compile(r"^/api/userdata/(.+?)/move/(.+)$")


class ComfyUIProxyMiddleware:
    """
    This middleware intercepts any request whose path starts with /api
    and proxies it to http://127.0.0.1:8188. It handles both HTTP and WS.
    """

    def __init__(self, app: ASGIApp, comfy_url: str):
        self.app = app
        self.comfy_url_http = f"http://{comfy_url}"
        self.comfy_url_ws = f"ws://{comfy_url}"

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        path = scope.get("path", "").lower()
        if any(path.startswith(proxy_path) for proxy_path in PATHS_TO_PROXY) and scope["type"] in ("http", "websocket"):
            user_info = scope.get("user_info")
            if not user_info or not user_info.is_admin:
                unauthorized_response = Response("Only admins allow to access ComfyUI", status_code=403)
                await unauthorized_response(scope, receive, send)
                return

            if scope["type"] == "http":
                await self.handle_http(scope, receive, send)
            else:
                await self.handle_websocket(scope, receive, send)
        else:
            await self.app(scope, receive, send)  # Not a ComfyUI request -> pass through to the normal app

    async def handle_http(self, scope: Scope, receive: Receive, send: Send):
        """
        Proxy HTTP requests using httpx.
        """
        # Reconstruct the incoming request
        # ---------------------------------------------------------------
        # 1) Get method, headers, and path
        method = scope["method"]
        headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
        full_path = str(scope["path"]).removeprefix("/comfy")

        # Temporary solution until it is fixed on the ComfyUI side: https://github.com/comfyanonymous/ComfyUI/pull/6963
        api_userdata = "/api/userdata/"
        if full_path.startswith(api_userdata) and method in ("GET", "DELETE"):
            full_path = api_userdata + urllib.parse.quote(full_path[len(api_userdata) :], safe="")
        elif full_path.startswith(api_userdata) and method == "POST":
            match = USERDATA_MOVE_PATTERN.match(full_path)
            if match:
                full_path = (
                    api_userdata
                    + urllib.parse.quote(match.group(1), safe="")
                    + "/move/"
                    + urllib.parse.quote(match.group(2), safe="")
                )
            else:
                full_path = api_userdata + urllib.parse.quote(full_path[len(api_userdata) :], safe="")
        # =======================

        query_string = scope["query_string"].decode("latin-1")
        if query_string:
            url = f"{self.comfy_url_http}{full_path}?{query_string}"
        else:
            url = f"{self.comfy_url_http}{full_path}"

        # 2) Get body
        body = b""
        more_body = True
        while more_body:
            message = await receive()
            if message["type"] == "http.request":
                body += message.get("body", b"")
                more_body = message.get("more_body", False)
            else:
                # If it's not http.request, break
                break

        # ---------------------------------------------------------------
        # 3) Forward the request to ComfyUI with httpx
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.request(method, url, headers=headers, content=body)

        # ---------------------------------------------------------------
        # 4) Build a response back to the original caller
        response_headers = [(k.encode("latin-1"), v.encode("latin-1")) for k, v in resp.headers.items()]
        # Send the response start
        await send(
            {
                "type": "http.response.start",
                "status": resp.status_code,
                "headers": response_headers,
            }
        )
        # Send the response body
        await send(
            {
                "type": "http.response.body",
                "body": resp.content,
                "more_body": False,
            }
        )

    async def handle_websocket(self, scope: Scope, receive: Receive, send: Send):
        """
        Proxy WebSocket requests using the websockets library.
        We'll connect from this server to ComfyUIs WS, then bridge messages.
        """
        # 1) Accept WebSocket from the client
        await send({"type": "websocket.accept"})

        # 2) Build the target URL for Comfy
        path = str(scope["path"]).removeprefix("/comfy")  # e.g. "/comfy", "/comfy/api/ws"
        query_string = scope["query_string"].decode("utf-8")
        ws_url = f"{self.comfy_url_ws}{path}?{query_string}" if query_string else f"{self.comfy_url_ws}{path}"

        # 3) Connect to ComfyUIs WebSocket
        async with websockets.connect(ws_url) as comfy_ws:
            # We'll run two tasks:
            #   A) reading from client, sending to Comfy
            #   B) reading from Comfy, sending to client
            #
            # We'll gather these tasks and wait for either to complete or error.

            async def client_to_comfy():
                while True:
                    msg = await receive()
                    if msg["type"] == "websocket.receive":
                        if "text" in msg:
                            await comfy_ws.send(msg["text"])
                        elif "bytes" in msg:
                            await comfy_ws.send(msg["bytes"])
                        else:
                            # If no text/bytes, treat as close
                            return
                    elif msg["type"] == "websocket.disconnect":
                        # Client disconnected, we close Comfy side
                        with contextlib.suppress(Exception):
                            await comfy_ws.close()
                        return

            async def comfy_to_client():
                while True:
                    try:
                        incoming = await comfy_ws.recv()
                    except websockets.ConnectionClosed:
                        # The Comfy side closed; let's close on our side
                        with contextlib.suppress(RuntimeError):
                            await send({"type": "websocket.close", "code": 1000, "reason": "ComfyUI closed WS"})
                        return

                    if isinstance(incoming, str):
                        await send({"type": "websocket.send", "text": incoming})
                    else:
                        await send({"type": "websocket.send", "bytes": incoming})

            # 4) Run the tasks concurrently
            _done, pending = await asyncio.wait(
                [asyncio.create_task(client_to_comfy()), asyncio.create_task(comfy_to_client())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Cancel whatever is still pending
            for task in pending:
                task.cancel()
