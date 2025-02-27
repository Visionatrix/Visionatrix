import copy
import json
import logging
import typing

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    responses,
    status,
)
from packaging.version import parse

from ..db_queries import (
    delete_flow_progress_install,
    edit_flow_progress_install,
    flows_installation_in_progress,
    get_flows_progress_install,
)
from ..flows import (
    LAST_GOOD_INSTALLED_FLOWS,
    Flow,
    calculate_dynamic_fields_for_flows,
    create_new_flow,
    extract_metadata_dict,
    get_available_flows,
    get_installed_flows,
    get_not_installed_flows,
    get_vix_flow,
    install_custom_flow,
    store_metadata_dict,
    uninstall_flow,
)
from ..pydantic_models import FlowCloneRequest, FlowMetadataUpdate, FlowProgressInstall
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
    return list((await calculate_dynamic_fields_for_flows(await get_installed_flows())).values())


@ROUTER.get("/not-installed")
async def get_not_installed(request: Request) -> list[Flow]:
    """
    Return the list of flows that can be installed. This endpoint provides detailed information about each flow,
    similar to the installed flows, which includes metadata and configuration parameters.
    """
    if not request.scope["user_info"].is_admin:
        return []
    return list((await calculate_dynamic_fields_for_flows(await get_not_installed_flows())).values())


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
    for i in (await get_installed_flows()).values():
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


@ROUTER.get("/flow-details")
async def get_flow_details(
    request: Request, name: str = Query(..., description="Name of the flow to retrieve details for.")
):
    """
    Retrieves the Flow model and its associated flow_comfy dictionary.
    This endpoint is restricted to admin users.
    """
    require_admin(request)
    flow_name = name.lower()
    flows_comfy = {}
    flow = (await get_installed_flows(flows_comfy)).get(flow_name)
    if not flow:
        flow = (await get_available_flows(flows_comfy)).get(flow_name)
        if not flow:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Flow '{name}' not found.")
    return {"flow": flow, "flow_comfy": flows_comfy[flow_name]}


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
async def install(
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
    flow = (await get_available_flows(flows_comfy)).get(flow_name)
    if not flow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Can't find `{flow_name}` flow.")
    if await flows_installation_in_progress(flow.name):
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
async def install_from_file(
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
    if await flows_installation_in_progress(flow.name):
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
async def flow_update(
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
    _installed_flow_info = (await get_installed_flows()).get(flow_name)
    if not _installed_flow_info:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Can't find `{flow_name}` in installed flows.")
    flows_comfy = {}
    flow = (await get_available_flows(flows_comfy)).get(flow_name)
    if not flow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Can't find `{flow_name}` in available flows.")
    if parse(_installed_flow_info.version) >= parse(flow.version):
        raise HTTPException(status.HTTP_412_PRECONDITION_FAILED, f"Flow `{flow_name}` does not have a newer version.")
    if await flows_installation_in_progress(flow.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Installation of this flow is already in progress.")
    b_tasks.add_task(install_custom_flow, flow, flows_comfy[flow_name])


@ROUTER.get("/install-progress")
async def get_install_progress(request: Request) -> list[FlowProgressInstall]:
    """
    Retrieves the current installation progress of all flows.

    Requires administrative privileges.
    """
    require_admin(request)
    r = await get_flows_progress_install()
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
    if not await delete_flow_progress_install(name):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Can't find `{name}`.")


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
    await uninstall_flow(name)


@ROUTER.post(
    "/clone-flow",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Flow cloned successfully."},
        404: {"description": "Original flow not found."},
        400: {"description": "Error occurred while cloning the flow."},
        409: {
            "description": "Installation of the same flow is already in progress",
            "content": {
                "application/json": {"example": {"detail": "Installation of this flow is already in progress."}}
            },
        },
    },
)
async def clone_flow(request: Request, b_tasks: BackgroundTasks, data: FlowCloneRequest = Body(...)):
    """
    Clones an existing flow with updated metadata or LoRA connection points.
    Requires admin privileges.
    """

    require_admin(request)
    flows_comfy = {}
    flow = (await get_installed_flows(flows_comfy)).get(data.original_flow_name)
    if not flow:
        flow = (await get_available_flows(flows_comfy)).get(data.original_flow_name)
    if not flow:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Cannot find original flow named '{data.original_flow_name}'.",
        )
    try:
        new_flow_comfy = await create_new_flow(flow, flows_comfy[data.original_flow_name], data)
    except Exception as e:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Error cloning flow: {e}") from e

    flow = get_vix_flow(new_flow_comfy)
    if await flows_installation_in_progress(flow.name):
        raise HTTPException(status.HTTP_409_CONFLICT, "Installation of this flow is already in progress.")
    b_tasks.add_task(install_custom_flow, flow, new_flow_comfy)


@ROUTER.put(
    "/flow-metadata",
    response_class=responses.Response,
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        204: {"description": "Flow metadata updated successfully."},
        400: {
            "description": "Invalid metadata provided",
            "content": {"application/json": {"example": {"detail": "Flow metadata node not found."}}},
        },
        500: {
            "description": "Error during editing the flow",
            "content": {"application/json": {"example": {"detail": "Editing flow failed."}}},
        },
    },
)
async def edit_flow_metadata(
    request: Request,
    name: str = Query(..., description="Name of the flow to update metadata for."),
    metadata: FlowMetadataUpdate = Body(..., description="New metadata values for the flow."),
):
    require_admin(request)
    flow_name = name.lower()
    flows_comfy: dict[str, dict] = {}
    flow = (await get_installed_flows(flows_comfy)).get(flow_name)
    if not flow:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"Flow '{flow_name}' not found.")
    flow_comfy = flows_comfy[flow_name]

    metadata_node_id = None
    for node_id, node_details in flow_comfy.items():
        if node_details.get("class_type") == "VixUiWorkflowMetadata":
            metadata_node_id = node_id
            break
        if node_details.get("_meta", {}).get("title", "") == "WF_META":
            metadata_node_id = node_id
            break
    if not metadata_node_id:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Flow metadata node not found.")

    current_meta, mode = extract_metadata_dict(flow_comfy[metadata_node_id])
    current_meta["display_name"] = metadata.display_name
    current_meta["description"] = metadata.description
    current_meta["license"] = metadata.license
    current_meta["required_memory_gb"] = metadata.required_memory_gb
    current_meta["version"] = metadata.version
    store_metadata_dict(flow_comfy[metadata_node_id], current_meta, mode)
    if not await edit_flow_progress_install(flow_name, flow_comfy):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Editing flow failed.")
    LAST_GOOD_INSTALLED_FLOWS["update_time"] = 0.0
