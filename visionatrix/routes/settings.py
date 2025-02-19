import logging

import ollama
from fastapi import APIRouter, Body, HTTPException, Query, Request, responses, status

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
from ..pydantic_models import OllamaModelItem
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
    return await get_setting(request.scope["user_info"].user_id, key, request.scope["user_info"].is_admin)


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
    return await get_global_setting(key, request.scope["user_info"].is_admin)


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
    return await get_user_setting(request.scope["user_info"].user_id, key)


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
    await set_global_setting(key, value, sensitive)


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
    await set_user_setting(request.scope["user_info"].user_id, key, value)


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
    return await get_all_settings(request.scope["user_info"].user_id, request.scope["user_info"].is_admin)


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
    return await get_all_global_settings(request.scope["user_info"].is_admin)


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
    return await get_user_settings(request.scope["user_info"].user_id)


@ROUTER.get(
    "/ollama/models",
    response_model=list[OllamaModelItem],
    responses={
        200: {
            "description": "Successfully retrieved list of models installed in Ollama",
        },
        401: {
            "description": "Unauthorized - Admin privilege required",
            "content": {"application/json": {"example": {"detail": "Admin privilege required"}}},
        },
        404: {
            "description": "Invalid Ollama URL configured or error fetching models",
            "content": {
                "application/json": {"example": {"detail": "Invalid Ollama URL configured or error fetching models."}}
            },
        },
    },
)
async def get_ollama_models(request: Request) -> list[OllamaModelItem]:
    """
    Fetches a list of models from the configured Ollama server (filename, size, modified).
    Requires admin privileges.
    """
    require_admin(request)

    ollama_url = await get_global_setting("ollama_url", True)
    if not ollama_url:
        LOGGER.debug("No custom Ollama URL defined, trying default one.")
        ollama_url = None

    ollama_client = ollama.AsyncClient(host=ollama_url)
    try:
        models_response = await ollama_client.list()
    except Exception as e:
        LOGGER.exception("Error fetching Ollama models: %s", e)
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Error fetching Ollama models: {e}") from None

    results = []
    for m in models_response.models:
        results.append(
            OllamaModelItem(
                model=m.model or "unknown",
                size=m.size if m.size else 0,
                modified_at=m.modified_at.timestamp() if m.modified_at else 0.0,
            )
        )
    return results
