import base64
import time

from passlib.context import CryptContext
from sqlalchemy import select
from starlette.requests import HTTPConnection
from starlette.types import Scope

from .. import database
from ..pydantic_models import UserInfo

AUTH_CACHE = {}
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def get_user_info_http(_scope: Scope, http_connection: HTTPConnection) -> UserInfo | None:
    authorization: str = http_connection.headers.get("Authorization")
    if not authorization:
        return None
    return await _parse_and_verify(authorization)


async def get_user_info_ws(_scope: Scope, headers: dict[str, str], _cookies: dict[str, str]) -> UserInfo | None:
    authorization = headers.get("authorization")
    if not authorization:
        return None
    return await _parse_and_verify(authorization)


async def _parse_and_verify(authorization: str) -> UserInfo | None:
    try:
        scheme, encoded_credentials = authorization.split()
        if scheme.lower() != "basic":
            return None

        decoded_credentials = base64.b64decode(encoded_credentials).decode("ascii")
        username, _, password = decoded_credentials.partition(":")
        if (userinfo := await get_user(username, password)) is None or userinfo.disabled is True:
            return None
    except ValueError:
        return None
    return UserInfo.model_validate(userinfo)


async def get_user(username: str, password: str) -> database.UserInfo | None:
    current_time = time.time()
    if (cache_entry := AUTH_CACHE.get(username)) and (current_time - cache_entry["time"] < 15):
        if cache_entry["password"] == password:
            return cache_entry["data"]
        del AUTH_CACHE[username]

    async with database.SESSION() as session:
        results = await session.execute(select(database.UserInfo).filter_by(user_id=username))
        user_info = results.scalar_one_or_none()
        if user_info and PWD_CONTEXT.verify(password, user_info.hashed_password):
            AUTH_CACHE[username] = {"data": user_info, "time": current_time, "password": password}
            return user_info
    return None
