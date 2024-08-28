import logging
from json import loads
from os import environ

from httpx import AsyncClient
from starlette.requests import HTTPConnection
from starlette.types import Scope

from ..pydantic_models import UserInfo

NEXTCLOUD_URL = environ.get("NEXTCLOUD_URL", "http://nextcloud.local").removesuffix("/index.php").removesuffix("/")
"""Url should be in format: https://cloud.nextcloud.com"""

__nextcloud_headers_set = environ.get("NEXTCLOUD_HEADERS_SET", "{}")
NEXTCLOUD_HEADERS_SET: dict = loads(__nextcloud_headers_set)
"""
A dictionary of custom headers that will be added to each request to Nextcloud.
The headers should be defined in a JSON format string in the environment variable NEXTCLOUD_HEADERS_SET.
Example: '{"Content-Security-Policy": "frame-ancestors \\'self\\'", "Another-Header": "value"}'
"""
NEXTCLOUD_HEADERS_SET.update({"OCS-APIRequest": "true"})


LOGGER = logging.getLogger("visionatrix")


async def get_user_info(_scope: Scope, http_connection: HTTPConnection) -> UserInfo | None:
    headers = []
    headers_to_remove = ["host", "content-length"]
    for header in http_connection.headers:
        if header not in headers_to_remove:
            headers.append((header, http_connection.headers[header]))
    async with AsyncClient(
        base_url=NEXTCLOUD_URL,
        cookies=http_connection.cookies,
        headers=headers,
        timeout=5.0,
    ) as client:
        r = await client.get("/ocs/v1.php/cloud/user?format=json", headers=NEXTCLOUD_HEADERS_SET)
        if r.status_code != 200:
            LOGGER.error("Nextcloud return %s status code.", r.status_code)
            return None
    ocs_response = loads(r.text)
    ocs_meta = ocs_response["ocs"]["meta"]
    if ocs_meta["status"] != "ok":
        LOGGER.error("OCS status: %s, message: %s", ocs_meta["status"], ocs_meta["message"])
        return None
    userinfo = ocs_response["ocs"]["data"]
    is_admin = "admin" in userinfo.get("groups", [])
    return UserInfo(
        user_id=userinfo["id"],
        full_name=userinfo["displayname"],
        email=userinfo["email"] if userinfo["email"] else "",
        is_admin=is_admin,
    )
