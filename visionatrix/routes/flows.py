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
    add_flow_progress_install,
    delete_flows_progress_install,
    finish_flow_progress_install,
    flows_installation_in_progress,
    get_flows_progress_install,
    set_flow_progress_install_error,
    update_flow_progress_install,
)
from ..db_queries_async import (
    delete_flows_progress_install_async,
    get_flows_progress_install_async,
)
from ..flows import (
    Flow,
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
    return list(get_installed_flows().values())


@ROUTER.get("/not-installed")
async def get_not_installed() -> list[Flow]:
    """
    Return the list of flows that can be installed. This endpoint provides detailed information about each flow,
    similar to the installed flows, which includes metadata and configuration parameters.
    """
    return list(get_not_installed_flows().values())


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
            "description": "Another flow installation is in progress",
            "content": {"application/json": {"example": {"detail": "Another flow installation is in progress."}}},
        },
    },
)
def install(
    request: Request,
    b_tasks: BackgroundTasks,
    name: str = Query(..., description="Name of the flow you wish to install"),
):
    """
    Endpoint to initiate the installation of a flow based on its name. This endpoint requires admin privileges
    to perform the installation. If another flow installation is already in progress, it prevents a new
    installation to avoid conflicts, returning a 409 Conflict HTTP status.

    This endpoint schedules a background task for the installation process using the specified flow name. It
    checks the availability of the flow in the list of available flows and starts the installation if the flow
    is found. It ensures that no two installations can run concurrently.
    """
    require_admin(request)
    if flows_installation_in_progress():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another flow installation is in progress.")

    flow_name = name.lower()
    flows_comfy = {}
    flow = get_available_flows(flows_comfy).get(flow_name)
    if not flow:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Can't find `{flow_name}` flow.")
    delete_flows_progress_install(flow_name)
    add_flow_progress_install(flow_name, flows_comfy[flow_name])
    b_tasks.add_task(install_custom_flow, flow, flows_comfy[flow_name], __progress_install_callback)
    return responses.Response(status_code=status.HTTP_204_NO_CONTENT)


@ROUTER.put(
    "/flow",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Successful start of installation"},
        409: {
            "description": "Another flow installation is in progress",
            "content": {"application/json": {"example": {"detail": "Another flow installation is in progress."}}},
        },
    },
)
def install_from_file(
    request: Request,
    b_tasks: BackgroundTasks,
    flow_file: UploadFile = File(..., description="The ComfyUI workflow file to be uploaded and installed"),
):
    """
    Endpoint to initiate the installation of a flow from an uploaded file. This endpoint requires admin privileges
    to perform the installation. If another flow installation is already in progress, it prevents a parallel flow
    installation to avoid conflicts, returning a 409 Conflict HTTP status.

    This endpoint schedules a background task for the installation process using the uploaded flow file.
    """
    require_admin(request)
    if flows_installation_in_progress():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Another flow installation is in progress.")

    flow_comfy = json.loads(flow_file.file.read())
    flow = get_vix_flow(flow_comfy)
    delete_flows_progress_install(flow.name)
    add_flow_progress_install(flow.name, flow_comfy)
    b_tasks.add_task(install_custom_flow, flow, flow_comfy, __progress_install_callback)


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
            "description": "Another flow installation or update is in progress",
            "content": {
                "application/json": {"example": {"detail": "Another flow installation or update is in progress."}}
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
    Endpoint to initiate the update process of an installed flow based on its name.
    This endpoint requires admin privileges to perform the update. If another flow installation or update is already
    in progress, it prevents a new update to avoid conflicts, returning a 409 Conflict HTTP status.

    This endpoint schedules a background task for the update process using the specified flow name. It checks the
    availability of a newer version of the flow and starts the update if a newer version is found. It ensures that no
    two installations or updates can run concurrently.
    """
    require_admin(request)
    if flows_installation_in_progress():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Another flow installation or update is in progress."
        )

    flow_name = name.lower()
    _installed_flow_info = get_installed_flows().get(flow_name)
    if not _installed_flow_info:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Can't find `{flow_name}` in installed flows."
        )

    flows_comfy = {}
    flow = get_available_flows(flows_comfy).get(flow_name)
    if not flow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Can't find `{flow_name}` in available flows."
        )

    if parse(_installed_flow_info.version) >= parse(flow.version):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail=f"Flow `{flow_name}` does not have a newer version.",
        )
    delete_flows_progress_install(flow_name)
    add_flow_progress_install(flow_name, flows_comfy[flow_name])
    b_tasks.add_task(install_custom_flow, flow, flows_comfy[flow_name], __progress_install_callback)
    return responses.Response(status_code=status.HTTP_204_NO_CONTENT)


@ROUTER.get("/install-progress")
async def get_install_progress(request: Request) -> list[FlowProgressInstall]:
    """
    Retrieves the current installation progress of all flows from an in-memory dictionary. This endpoint
    returns a dictionary showing the installation status for each flow.

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
        r = await delete_flows_progress_install_async(name)
    else:
        r = delete_flows_progress_install(name)
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


def __progress_install_callback(name: str, progress: float, error: str, relative_progress: bool) -> bool:
    """Returns `True` if no errors occurred."""

    if error:
        set_flow_progress_install_error(name, error)
        return False  # we return "False" because we are setting an error and "installation" should be stopped anyway
    if progress == 100.0:
        LOGGER.debug("Installation of %s flow completed", name)
        return finish_flow_progress_install(name)
    return update_flow_progress_install(name, progress, relative_progress)
