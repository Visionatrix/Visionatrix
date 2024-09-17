from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class TaskRunResults(BaseModel):
    tasks_ids: list[int] = Field(..., description="List of IDs representing the tasks that were created.")


class SubFlow(BaseModel):
    """
    A SubFlow modifies or extends a Flow by overwriting certain parameters like display_name and input_params.
    """

    display_name: str = Field(..., description="The new display name when this subflow's parameters are used.")
    type: str = Field(
        ...,
        description="The type of object this subflow is applicable to, e.g., 'image', 'image-inpaint' or 'video'.",
    )
    input_params: list[dict] = Field(
        default=[],
        description="List of input parameters specific to this subflow, replacing the original flow's parameters.",
    )


class AIResourceModel(BaseModel):
    """
    Represents an AI model resource within a Flow.

    This model provides a structured way to handle AI
    models that are integral to workflows, ensuring that each model can be dynamically
    resolved, downloaded, and verified before use.
    """

    name: str = Field(..., description="Unique name of the model.")
    save_path: str = Field(..., description="Subpath where the model is stored within the local system.")
    url: str = Field(..., description="URL from which the model can be downloaded.")
    homepage: str = Field("", description="Webpage with detailed information about the model.")
    hash: str = Field(..., description="SHA256 hash of the model file for integrity verification.")
    hashes: dict = Field(
        {},
        description="For archives, may contain filename:hash pairs for integrity checks after the archive is deleted.",
    )
    regexes: list[dict] = Field(
        default=[],
        description="List of regex patterns that dynamically resolve model details based on workflow configurations.",
    )
    gated: bool = Field(False, description="Flag showing is the model closed to public access")

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, AIResourceModel) and self.name == other.name


class Flow(BaseModel):
    """
    Flows serve as add-ons to ComfyUI workflows, determining the parameters to be displayed and populated.
    They also allow for the modification of ComfyUI workflow behavior based on incoming parameters.
    """

    name: str = Field(..., description="The unique identifier of the flow.")
    display_name: str = Field(..., description="The user-friendly name of the flow.")
    description: str = Field("", description="A brief explanation of the flow's purpose and functionality.")
    author: str = Field(..., description="The creator or maintainer of the flow.")
    homepage: str = Field("", description="A URL to the flow's homepage or the author's website.")
    license: str = Field("", description="The type of license under which the flow is made available.")
    documentation: str = Field("", description="A URL linking to detailed documentation for the flow.")
    tags: list[str] = Field(default=[], description="Tags describing this flow.")
    sub_flows: list[SubFlow] = Field(
        default=[], description="A list of subflows derived from this flow, allowing customization or extension."
    )
    models: list[AIResourceModel] = Field(default=[], description="A list of models used by the ComfyUI workflow.")
    input_params: list[dict] = Field(
        ..., description="Initial set of parameters required to launch the flow, potentially modifiable by subflows."
    )
    version: str = Field("", description="Internal version of the flow in major.minor format.")
    requires: list[str] = Field(default=[], description="Required external workflow dependencies.")
    private: bool = Field(False, description="Whether the workflow is missing from the `FLOWS_CATALOG_URL`")
    new_version_available: str = Field("", description="If not empty, contains the new version of the workflow.")
    is_seed_supported: bool = Field(
        True, description="Flag determining if 'Random Seed' input will be displayed in the UI."
    )
    is_count_supported: bool = Field(
        True, description="Flag determining if 'Number of images' input will be displayed in the UI."
    )

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, AIResourceModel) and self.name == other.name


class FlowProgressInstall(BaseModel):
    """Represents the progress status of a flow installation process."""

    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="The name of the flow being installed.")
    flow: Flow | None = Field(None, description="Parsed information about Flow in Visionatrix format.")
    flow_comfy: dict = Field(..., description="The ComfyUI workflow which are installed.")
    progress: float = Field(..., description="The current progress of the installation, ranging from 0 to 100.")
    error: str = Field("", description="Details of any error encountered during the installation process.")
    started_at: datetime = Field(..., description="Timestamp when the installation process started.")
    updated_at: datetime | None = Field(None, description="Timestamp of the last update to the installation progress.")
    finished_at: datetime | None = Field(None, description="Timestamp when the installation process completed.")


class TaskDetailsInput(BaseModel):
    """Information about input file to a ComfyUI workflow."""

    file_name: str = Field(..., description="Format of name is 'task_id' + '_' + 'index'")
    file_size: int = Field(..., description="Size of file in bytes.")


class TaskDetailsOutput(BaseModel):
    """Contains information for retrieving the results of a ComfyUI workflow."""

    comfy_node_id: int = Field(..., description="ID of the ComfyUI node containing the result.")
    type: str = Field(
        ..., description="Type of the result from the ComfyUI node - currently can be either 'image' or 'video'."
    )
    file_size: int = Field(-1, description="Size of file(s) in bytes.")
    batch_size: int = Field(-1, description="Count of outputs(files) produced by node.")


class TaskDetailsShort(BaseModel):
    """Brief information about the Task."""

    task_id: int = Field(..., description="Unique identifier of the task.")
    progress: float = Field(
        ..., description="Progress from 0 to 100, task results are only available once progress reaches 100."
    )
    error: str = Field(
        ..., description="If this field is not empty, it indicates an error that occurred during task execution."
    )
    name: str = Field(..., description="The unique identifier of the flow.")
    input_params: dict = Field(
        ..., description="Incoming textual parameters based on which the ComfyUI workflow was generated."
    )
    outputs: list[TaskDetailsOutput] = Field(..., description="ComfyUI nodes from which results can be retrieved.")
    input_files: list[TaskDetailsInput] = Field(
        ..., description="Incoming file parameters based on which the ComfyUI workflow was generated."
    )
    locked_at: datetime | None = Field(None, description="Lock time if task is locked.")
    worker_id: str | None = Field(None, description="Unique identifier of the worker working on the task.")
    execution_time: float = Field(..., description="Execution time of the ComfyUI workflow in seconds.")
    group_scope: int = Field(default=1, description="Group number to which task is assigned.")
    parent_task_id: int | None = Field(None, description="Parent task ID if is a child task.")
    parent_task_node_id: int | None = Field(None, description="Parent task Node ID if is a child task.")
    child_tasks: list[TaskDetailsShort] = Field(
        [], description="List of child tasks of type `TaskDetailsShort` if any."
    )


class TaskDetails(TaskDetailsShort):
    """Detailed information about the Task."""

    created_at: datetime = Field(..., description="Task creation time.")
    updated_at: datetime | None = Field(None, description="Last task update time.")
    finished_at: datetime | None = Field(None, description="Finish time of the task.")
    task_id: int = Field(..., description="Unique identifier of the task.")
    flow_comfy: dict = Field(..., description="The final generated ComfyUI workflow.")
    user_id: str = Field(..., description="User ID to whom the task belongs.")
    webhook_url: str | None = Field(None, description="The URL that will be called when the task state changes.")
    webhook_headers: dict | None = Field(None, description="Headers to send to webhook.")


class WorkerDetailsSystemRequest(BaseModel):
    """Provides OS and Python environment details of the worker."""

    hostname: str = Field(..., description="Hostname of the worker machine")
    os: str = Field(..., description="Operating system type, e.g., 'posix', 'nt'")
    version: str = Field(..., description="Python version information")
    embedded_python: bool = Field(..., description="Flag indicating if Python is embedded (portable) or not")


class WorkerDetailsDeviceRequest(BaseModel):
    """Provides detailed information about the computing device and memory status."""

    name: str = Field(..., description="Full computing device name")
    type: str = Field("", description="Type of the device such as 'cuda' or 'cpu'")
    index: int = Field(0, description="Computing device index")
    vram_total: int = Field(0, description="Total VRAM available on the device in bytes")
    vram_free: int = Field(0, description="Free VRAM available on the device in bytes")
    torch_vram_total: int = Field(0, description="Total VRAM managed by PyTorch in bytes")
    torch_vram_free: int = Field(0, description="Free VRAM managed by PyTorch in bytes")


class WorkerDetailsRequest(BaseModel):
    """Consolidates information relevant to a worker handling AI tasks."""

    worker_version: str = Field(..., description="Version of the worker")
    pytorch_version: str = Field("", description="Torch version used by the worker")
    system: WorkerDetailsSystemRequest = Field(...)
    devices: list[WorkerDetailsDeviceRequest] = Field(...)
    ram_total: int = Field(0, description="Total RAM on the worker in bytes")
    ram_free: int = Field(0, description="Free RAM on the worker in bytes")
    last_seen: datetime = Field(datetime.now(timezone.utc), description="Last seen time")


class WorkerDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="The primary key for the worker record, automatically incremented.")
    user_id: str = Field(..., description="The foreign key from the 'users' table, non-nullable.")
    worker_id: str = Field(
        ...,
        description="Uniq identifier for the worker, constructed from user_id, hostname, device name and device index.",
    )
    worker_version: str = Field(..., description="Version of the worker")
    last_seen: datetime = Field(..., description="The timestamp of the worker's last activity, stored in UTC.")
    tasks_to_give: list[str] = Field(
        ...,
        description="Specifies tasks that the worker can execute. An empty list indicates that all tasks are allowed.",
    )

    os: str | None = Field(None, description="Operating system type of the worker's machine, such as 'posix' or 'nt'.")
    version: str | None = Field(None, description="The version of Python running on the worker's machine.")
    embedded_python: bool = Field(
        default=False, description="Indicates whether the Python environment is embedded (portable)."
    )

    device_name: str | None = Field(None, description="Name of the computing device.")
    device_type: str | None = Field(None, description="Type of the computing device, such as 'cuda' or 'cpu'.")
    vram_total: int | None = Field(None, description="Total VRAM available on the device in bytes.")
    vram_free: int | None = Field(None, description="Free VRAM available on the device in bytes.")
    torch_vram_total: int | None = Field(None, description="Total VRAM managed by PyTorch in bytes.")
    torch_vram_free: int | None = Field(None, description="Free VRAM managed by PyTorch that is currently unused.")
    ram_total: int | None = Field(None, description="Total RAM available on the worker in bytes.")
    ram_free: int | None = Field(None, description="Free RAM available on the worker in bytes.")


class UserInfo(BaseModel):
    """Minimum information provided by Authentication backends about user."""

    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="Unique user ID.")
    full_name: str = Field("", description="Full name of the user.")
    email: str = Field("", description="Email name of the user.")
    is_admin: bool = Field(False, description="Flag showing is user is admin.")


class OrphanModel(BaseModel):
    """
    Represents an orphaned model file that is not associated with any currently installed flow.

    This model provides detailed information about the orphaned file, including its
    size, potential usage in flows, and any matching AIResourceModel, if available.
    """

    path: str = Field(..., description="The relative path of the orphaned model file within 'models_dir' directory.")
    size: float = Field(..., description="Size of the orphaned file in megabytes.")
    creation_time: float = Field(..., description="The file's creation time in UNIX timestamp format.")
    res_model: AIResourceModel | None = Field(None, description="AIResourceModel describing the file, if any matches.")
    possible_flows: list[Flow] = Field([], description="List of possible flows that could potentially use this model.")
