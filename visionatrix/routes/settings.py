import logging

from fastapi import APIRouter, Body, Query, Request, responses, status

from .. import options
from ..db_queries import (
    get_all_global_settings,
    get_all_settings,
    get_global_setting,
    get_setting,
    get_user_setting,
    get_user_settings,
    set_global_setting,
    set_user_setting,
)
from ..db_queries_async import (
    get_all_global_settings_async,
    get_all_settings_async,
    get_global_setting_async,
    get_setting_async,
    get_user_setting_async,
    get_user_settings_async,
    set_global_setting_async,
    set_user_setting_async,
)
from .helpers import require_admin

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/settings", tags=["settings"])


@ROUTER.get(
    "/get",
    response_class=responses.Response,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved setting",
            "content": {"text/plain": {"example": "value_of_setting"}},
        }
    },
)
async def get(request: Request, key: str = Query(..., description="The key of the setting to retrieve")) -> str:
    """
    Returns the value as a string or an empty string if the setting is not found.

    Default endpoint for retrieving settings.
    User settings have higher priority than global settings.
    """
    if options.VIX_MODE == "SERVER":
        return await get_setting_async(request.scope["user_info"].user_id, key, request.scope["user_info"].is_admin)
    return get_setting(request.scope["user_info"].user_id, key, request.scope["user_info"].is_admin)


@ROUTER.get(
    "/global",
    response_class=responses.Response,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved global setting",
            "content": {"text/plain": {"example": "value_of_global_setting"}},
        }
    },
)
async def get_global(
    request: Request, key: str = Query(..., description="The key of the global setting to retrieve")
) -> str:
    """Retrieve the global setting value or an empty string if the global setting is not found."""
    if options.VIX_MODE == "SERVER":
        return await get_global_setting_async(key, request.scope["user_info"].is_admin)
    return get_global_setting(key, request.scope["user_info"].is_admin)


@ROUTER.get(
    "/user",
    response_class=responses.Response,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved user setting",
            "content": {"text/plain": {"example": "value_of_user_setting"}},
        }
    },
)
async def get_user(
    request: Request, key: str = Query(..., description="The key of the user setting to retrieve")
) -> str:
    """Retrieve the user setting value or an empty string if the user setting is not found."""
    if options.VIX_MODE == "SERVER":
        return await get_user_setting_async(request.scope["user_info"].user_id, key)
    return get_user_setting(request.scope["user_info"].user_id, key)


@ROUTER.post(
    "/global",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Global setting updated successfully"},
        401: {
            "description": "Unauthorized - Admin privilege required",
            "content": {"application/json": {"example": {"detail": "Admin privilege required"}}},
        },
    },
)
async def set_global(
    request: Request,
    key: str = Body(..., description="The key of the setting to update"),
    value: str = Body(..., description="The value of the setting to update, or an empty string to delete the setting"),
    sensitive: bool = Body(..., description="Flag that determines whether the value can be available to users or not"),
):
    """
    Creates, updates, or deletes a global setting.

    To delete a setting, specify an empty string as the value.
    Access is restricted to administrators only.
    """
    require_admin(request)
    if options.VIX_MODE == "SERVER":
        await set_global_setting_async(key, value, sensitive)
    else:
        set_global_setting(key, value, sensitive)


@ROUTER.post(
    "/user",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "User setting updated successfully"},
    },
)
async def set_user(
    request: Request,
    key: str = Body(..., description="The key of the setting to update"),
    value: str = Body(..., description="The value of the setting to update, or an empty string to delete the setting"),
):
    """
    Creates, updates, or deletes a user setting.

    To delete a setting, specify an empty string as the value.
    """
    if options.VIX_MODE == "SERVER":
        await set_user_setting_async(request.scope["user_info"].user_id, key, value)
    else:
        set_user_setting(request.scope["user_info"].user_id, key, value)


@ROUTER.get(
    "/get_all",
    response_class=responses.JSONResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved all settings for the user",
            "content": {"application/json": {"example": {"setting_key": "value"}}},
        }
    },
)
async def get_all(request: Request) -> dict[str, str]:
    """
    Returns all settings for the user.
    User settings have higher priority than global settings.
    """
    user_id = request.scope["user_info"].user_id
    is_admin = request.scope["user_info"].is_admin

    if options.VIX_MODE == "SERVER":
        return await get_all_settings_async(user_id, is_admin)
    return get_all_settings(user_id, is_admin)


@ROUTER.get(
    "/global_all",
    response_class=responses.JSONResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved all global settings",
            "content": {"application/json": {"example": {"global_setting_key": "value"}}},
        }
    },
)
async def get_global_all(request: Request) -> dict[str, str]:
    """Retrieve all global settings or an empty dictionary if none are found."""
    is_admin = request.scope["user_info"].is_admin

    if options.VIX_MODE == "SERVER":
        return await get_all_global_settings_async(is_admin)
    return get_all_global_settings(is_admin)


@ROUTER.get(
    "/user_all",
    response_class=responses.JSONResponse,
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Successfully retrieved all user settings",
            "content": {"application/json": {"example": {"user_setting_key": "value"}}},
        }
    },
)
async def get_user_all(request: Request) -> dict[str, str]:
    """Retrieve all user settings or an empty dictionary if none are found."""
    user_id = request.scope["user_info"].user_id

    if options.VIX_MODE == "SERVER":
        return await get_user_settings_async(user_id)
    return get_user_settings(user_id)
