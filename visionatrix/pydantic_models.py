from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class TaskRunResults(BaseModel):
    tasks_ids: list[int] = Field(..., description="List of IDs representing the tasks that were created.")


class SubFlow(BaseModel):
    """
    A SubFlow modifies or extends a Flow by overwriting certain parameters like display_name and input_params.
    """

    display_name: str = Field(..., description="The new display name when this subflow's parameters are used.")
    type: str = Field(..., description="The type of object this subflow is applicable to, e.g., 'image' or 'video'.")
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
    regexes: list[dict] = Field(
        default=[],
        description="List of regex patterns that dynamically resolve model details based on workflow configurations.",
    )


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
    sub_flows: list[SubFlow] = Field(
        default=[], description="A list of subflows derived from this flow, allowing customization or extension."
    )
    models: list[AIResourceModel] = Field(default=[], description="A list of models used by the ComfyUI workflow.")
    input_params: list[dict] = Field(
        ..., description="Initial set of parameters required to launch the flow, potentially modifiable by subflows."
    )


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
    file_size: int = Field(-1, description="Size of file in bytes.")


class TaskDetailsShort(BaseModel):
    """Brief information about the Task."""

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


class TaskDetails(TaskDetailsShort):
    """Detailed information about the Task."""

    created_at: datetime = Field(..., description="Task creation time.")
    updated_at: datetime | None = Field(None, description="Last task update time.")
    finished_at: datetime | None = Field(None, description="Finish time of the task.")
    task_id: int = Field(..., description="Unique identifier of the task.")
    flow_comfy: dict = Field(..., description="The final generated ComfyUI workflow.")
    user_id: str = Field(..., description="User ID to whom the task belongs.")


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
    """Consolidates system and device information relevant to a worker handling AI tasks."""

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
    last_seen: datetime = Field(..., description="The timestamp of the worker's last activity, stored in UTC.")

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
