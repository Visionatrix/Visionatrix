import copy
import json
import logging
import typing

from fastapi import (
    APIRouter,
    BackgroundTasks,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    responses,
    status,
)
from packaging.version import parse

from .. import options
from ..db_queries import (
    delete_flow_progress_install,
    flows_installation_in_progress,
    get_flows_progress_install,
)
from ..db_queries_async import (
    delete_flow_progress_install_async,
    get_flows_progress_install_async,
)
from ..flows import (
    Flow,
    calculate_dynamic_fields_for_flows,
    get_available_flows,
    get_installed_flows,
    get_not_installed_flows,
    get_vix_flow,
    install_custom_flow,
    uninstall_flow,
)
from ..pydantic_models import FlowProgressInstall
from .helpers import require_admin

LOGGER = logging.getLogger("visionatrix")
ROUTER = APIRouter(prefix="/flows", tags=["flows"])


@ROUTER.get("/installed")
async def get_installed() -> list[Flow]:
    """
    Return the list of installed flows. Each flow can potentially be converted into a task. The response
    includes details such as the name, display name, description, author, homepage URL, and other relevant
    information about each flow.
    """
    return list((await calculate_dynamic_fields_for_flows(get_installed_flows())).values())


@ROUTER.get("/not-installed")
async def get_not_installed() -> list[Flow]:
    """
    Return the list of flows that can be installed. This endpoint provides detailed information about each flow,
    similar to the installed flows, which includes metadata and configuration parameters.
    """
    return list((await calculate_dynamic_fields_for_flows(get_not_installed_flows())).values())


@ROUTER.get("/subflows")
async def get_subflows(input_type: typing.Literal["image", "image-inpaint", "video"]) -> list[Flow]:
    """
    Retrieves a list of flows designed to post-process the results from other flows, filtering by the type
    of input they handle, either 'image', 'image-inpaint' or 'video'. This endpoint is particularly useful for chaining
    workflows where the output of one flow becomes the input to another.
    It modifies the main flow's structure by adopting sub-flow's display name and selectively merging input parameters
    from the sub-flows into the main flow's parameters based on matching names.
    """
    r = []
    for i in get_installed_flows().values():
        for sub_flow in i.sub_flows:
            if sub_flow.type == input_type:
                transformed_flow = copy.deepcopy(i)
                transformed_flow.display_name = sub_flow.display_name
                for sub_flow_input_params in sub_flow.input_params:
                    for k2 in transformed_flow.input_params:
                        if k2["name"] == sub_flow_input_params["name"]:
                            k2.update(**sub_flow_input_params)
                            break
                r.append(transformed_flow)
    return r


@ROUTER.post(
    "/flow",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successful start of installation"},
        404: {
            "description": "Flow not found",
            "content": {"application/json": {"example": {"detail": "Can't find `flow_name` flow."}}},
        },
        409: {
            "description": "Installation of the same flow is already in progress",
            "content": {
                "application/json": {"example": {"detail": "Installation of this flow is already in progress."}}
            },
        },
    },
)
def install(
    request: Request,
    b_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of the flow you wish to install"),
):
    """
    Initiates the installation of a flow based on its name. Requires admin privileges.

    If the specified flow is already being installed, a `409 Conflict` status is returned. However,
    the installation of other flows is allowed concurrently.
    """
    require_admin(request)
    flow_name = name.lower()
    flows_comfy = {}
    flow = get_available_flows(flows_comfy).get(flow_name)
    if not flow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Can't find `{flow_name}` flow.")
    if flows_installation_in_progress(flow.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Installation of this flow is already in progress.")
    b_tasks.add_task(install_custom_flow, flow, flows_comfy[flow_name])


@ROUTER.put(
    "/flow",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successful start of installation"},
        409: {
            "description": "Installation of the same flow is already in progress",
            "content": {
                "application/json": {"example": {"detail": "Installation of this flow is already in progress."}}
            },
        },
    },
)
def install_from_file(
    request: Request,
    b_tasks: BackgroundTasks,
    flow_file: UploadFile = File(..., description="The ComfyUI workflow file to be uploaded and installed"),
):
    """
    Initiates the installation of a flow from an uploaded file. Requires admin privileges.

    If the specified flow is already being installed, a `409 Conflict` status is returned. However,
    the installation of other flows is allowed concurrently.
    """
    require_admin(request)
    flow_comfy = json.loads(flow_file.file.read())
    flow = get_vix_flow(flow_comfy)
    if flows_installation_in_progress(flow.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Installation of this flow is already in progress.")
    b_tasks.add_task(install_custom_flow, flow, flow_comfy)


@ROUTER.post(
    "/flow-update",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successful start of update process"},
        404: {
            "description": "Flow not found",
            "content": {"application/json": {"example": {"detail": "Can't find `flow_name` flow."}}},
        },
        409: {
            "description": "Update or installation of the same flow is already in progress",
            "content": {
                "application/json": {"example": {"detail": "Installation of this flow is already in progress."}}
            },
        },
        412: {
            "description": "Flow does not have a newer version",
            "content": {"application/json": {"example": {"detail": "Flow `flow_name` does not have a newer version."}}},
        },
    },
)
def flow_update(
    request: Request,
    b_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of the flow you wish to update"),
):
    """
    Initiates the update process for an installed flow. Requires admin privileges.

    If the specified flow is already being installed or updated, a `409 Conflict` status is returned.
    However, updates or installations of other flows are allowed concurrently.
    """
    require_admin(request)
    flow_name = name.lower()
    _installed_flow_info = get_installed_flows().get(flow_name)
    if not _installed_flow_info:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Can't find `{flow_name}` in installed flows.")
    flows_comfy = {}
    flow = get_available_flows(flows_comfy).get(flow_name)
    if not flow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Can't find `{flow_name}` in available flows.")
    if parse(_installed_flow_info.version) >= parse(flow.version):
        raise HTTPException(status.HTTP_412_PRECONDITION_FAILED, f"Flow `{flow_name}` does not have a newer version.")
    if flows_installation_in_progress(flow.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Installation of this flow is already in progress.")
    b_tasks.add_task(install_custom_flow, flow, flows_comfy[flow_name])


@ROUTER.get("/install-progress")
async def get_install_progress(request: Request) -> list[FlowProgressInstall]:
    """
    Retrieves the current installation progress of all flows.

    Requires administrative privileges.
    """
    require_admin(request)
    if options.VIX_MODE == "SERVER":
        r = await get_flows_progress_install_async()
    else:
        r = get_flows_progress_install()
    for i in r:
        i.flow = get_vix_flow(i.flow_comfy)
    return r


@ROUTER.delete(
    "/install-progress",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Flow progress installation entry deleted successfully"},
        404: {
            "description": "Flow progress installation entry not found",
            "content": {"application/json": {"example": {"detail": "Can't find `flow_name`."}}},
        },
    },
)
async def delete_install_progress(
    request: Request, name: str = Query(..., description="Name of the flow progress you wish to delete")
):
    """
    Deletes the installation progress entry for a specified flow.

    Requires administrative privileges.
    """
    require_admin(request)
    if options.VIX_MODE == "SERVER":
        r = await delete_flow_progress_install_async(name)
    else:
        r = delete_flow_progress_install(name)
    if not r:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Can't find `{name}`.")


@ROUTER.delete(
    "/flow",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={204: {"description": "Flow deleted successfully"}},
)
async def delete(request: Request, name: str = Query(..., description="Name of the flow you wish to delete")):
    """
    Endpoint to delete an installed flow by its name. Requires administrative privileges to execute.
    This endpoint will succeed even if the flow does not exist.
    """
    require_admin(request)
    uninstall_flow(name)
