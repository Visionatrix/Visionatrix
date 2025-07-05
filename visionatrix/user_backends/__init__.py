import logging

from starlette.requests import HTTPConnection
from starlette.types import Scope

from ..options import USER_BACKENDS
from ..pydantic_models import UserInfo
from . import ldap, nextcloud, vix_db

LOGGER = logging.getLogger("visionatrix")


async def perform_auth_http(scope: Scope, conn: HTTPConnection) -> UserInfo | None:
    for backend in USER_BACKENDS:
        if backend == "vix_db":
            userinfo = await vix_db.get_user_info_http(scope, conn)
        elif backend == "nextcloud":
            userinfo = await nextcloud.get_user_info_http(scope, conn)
        elif backend == "ldap":
            userinfo = await ldap.get_user_info_http(scope, conn)
        else:
            raise ValueError(f"Unknown auth backend: `{backend}`")

        if userinfo is not None:
            LOGGER.debug("Authenticated via `%s` backend: %s", backend, userinfo)
            return userinfo
    return None


async def perform_auth_ws(scope: Scope, headers: dict[str, str], cookies: dict[str, str]) -> UserInfo | None:
    for backend in USER_BACKENDS:
        if backend == "vix_db":
            userinfo = await vix_db.get_user_info_ws(scope, headers, cookies)
        elif backend == "nextcloud":
            userinfo = await nextcloud.get_user_info_ws(scope, headers, cookies)
        elif backend == "ldap":
            userinfo = await ldap.get_user_info_ws(scope, headers, cookies)
        else:
            raise ValueError(f"Unknown auth backend: `{backend}`")

        if userinfo is not None:
            LOGGER.debug("WS Authenticated via `%s` backend: %s", backend, userinfo)
            return userinfo
    return None
