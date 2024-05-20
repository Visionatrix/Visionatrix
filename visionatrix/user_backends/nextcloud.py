import logging
from json import loads
from os import environ

from httpx import AsyncClient
from starlette.requests import HTTPConnection
from starlette.types import Scope

from ..pydantic_models import UserInfo

NEXTCLOUD_URL = environ.get("NEXTCLOUD_URL", "http://stable29.local").strip("/")
"""Url should be in format: https://cloud.nextcloud.com"""

LOGGER = logging.getLogger("visionatrix")


async def get_user_info(_scope: Scope, http_connection: HTTPConnection) -> UserInfo | None:
    headers = []
    headers_to_remove = ["host"]
    for header in http_connection.headers:
        if header not in headers_to_remove:
            headers.append((header, http_connection.headers[header]))
    async with AsyncClient(
        base_url=NEXTCLOUD_URL,
        cookies=http_connection.cookies,
        headers=headers,
    ) as client:
        r = await client.get("/ocs/v1.php/cloud/user?format=json", headers={"OCS-APIRequest": "true"})
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
        email=userinfo["email"],
        is_admin=is_admin,
    )
