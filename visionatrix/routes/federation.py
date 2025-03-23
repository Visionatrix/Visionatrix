import logging

from fastapi import APIRouter, Body, HTTPException, Query, Request, responses, status

from ..db_queries import (
    add_federated_instance,
    get_all_federated_instances,
    remove_federated_instance,
    update_federated_instance,
)
from ..pydantic_models import (
    FederatedInstance,
    FederatedInstanceCreate,
    FederatedInstanceUpdate,
)
from .helpers import require_admin

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/federation", tags=["federation"])


@ROUTER.get("/instances", response_model=list[FederatedInstance])
async def list_federated_instances(request: Request):
    """
    Retrieve a list of all federated instances.
    Requires administrative privileges.
    """
    require_admin(request)
    return await get_all_federated_instances()


@ROUTER.post(
    "/instance",
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Federated instance created successfully"},
        400: {"description": "Federated instance already exists or invalid data"},
    },
)
async def create_federated_instance(request: Request, data: FederatedInstanceCreate = Body(...)):
    """
    Create a new federated instance.
    Requires administrative privileges.
    """
    require_admin(request)
    if not await add_federated_instance(data):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create federated instance. It may already exist or the data is invalid.",
        )
    return responses.Response(status_code=status.HTTP_201_CREATED)


@ROUTER.delete(
    "/instance",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Federated instance deleted successfully"},
        404: {"description": "Federated instance not found"},
    },
)
async def delete_federated_instance(
    request: Request,
    instance_name: str = Query(..., description="Name of the federated instance to delete"),
):
    """
    Delete a federated instance by its name.
    Requires administrative privileges.
    """
    require_admin(request)
    if not await remove_federated_instance(instance_name):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Federated instance '{instance_name}' not found.",
        )
    return responses.Response(status_code=status.HTTP_204_NO_CONTENT)


@ROUTER.put(
    "/instance",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Federated instance updated successfully"},
        404: {"description": "Federated instance not found or no update performed"},
        400: {"description": "No valid fields provided for update"},
    },
)
async def update_federated_instance_endpoint(
    request: Request,
    instance_name: str = Query(..., description="Name of the federated instance to update"),
    data: FederatedInstanceUpdate = Body(...),
):
    """
    Update an existing federated instance.
    Requires administrative privileges.
    """
    require_admin(request)
    if not await update_federated_instance(instance_name, data):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Federated instance '{instance_name}' not found or no valid fields provided for update.",
        )
    return responses.Response(status_code=status.HTTP_204_NO_CONTENT)
