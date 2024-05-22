import logging

from starlette.requests import HTTPConnection
from starlette.types import Scope

from ..options import USER_BACKENDS
from ..pydantic_models import UserInfo
from . import nextcloud, vix_db

LOGGER = logging.getLogger("visionatrix")


async def perform_auth(scope: Scope, http_connection: HTTPConnection) -> UserInfo | None:
    for backend in USER_BACKENDS:
        if backend == "vix_db":
            result = await vix_db.get_user_info(scope, http_connection)
        elif backend == "nextcloud":
            result = await nextcloud.get_user_info(scope, http_connection)
        else:
            raise ValueError(f"Unknown auth backend: `{backend}`")  # Make a PR to Vix if you wish to add own backend.

        if result:
            LOGGER.debug("Authenticated using `%s` backend: %s", backend, result)
            return result
    return None
