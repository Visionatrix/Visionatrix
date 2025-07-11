from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Self


class TaskRunResults(BaseModel):
    tasks_ids: list[int] = Field(..., description="List of IDs representing the tasks that were created.")
    outputs: list[TaskDetailsOutput] = Field(..., description="List of outputs for the created tasks.")


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
    types: list[str] = Field([], description="ComfyUI model types to which model belongs(e.g 'checkpoints', 'loras').")
    filename: str = Field(
        "", description="Overridden file name under which the model should be stored in the file system."
    )
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
    gated: bool = Field(False, description="Flag showing is the model closed to public access.")
    file_size: int = Field(..., description="The size of the model file in bytes.")
    installed: bool | None = Field(
        None,
        description="Flag indicating whether the model is already installed. "
        "Currently, this field is populated only by the "
        "`/flows/installed` and `/flows/not-installed` endpoints.",
    )

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, AIResourceModel) and self.name == other.name


class CustomLoraDefinition(AIResourceModel):
    """Definition of custom LoRA added to the flow. Backend will automatically generate inputs for it."""

    strength_model: float = Field(1.0, description="Default strength of the LoRA model.")
    display_name: str = Field("", description="Text to display for the LoRA slider.")
    trigger_words: list[str] = Field([], description="List of words to trigger the LoRA.")
    node_id: str = Field(..., description="ComfyUI Node ID from which this definition was created.")


class LoraConnectionPoint(BaseModel):
    """
    Represents a connection point in the flow where LoRAs can be added.
    Provides details necessary for the UI to manage dynamic LoRA integration within the flow.
    """

    description: str = Field(
        "",
        description="A brief description of the functionality or purpose"
        " of this connection point for integrating LoRAs into the flow.",
    )
    base_model_type: str = Field(
        ...,
        description="Specifies the base model type in the CivitAI format "
        "that is compatible with this connection point, allowing the UI to filter applicable LoRAs.",
    )
    connected_loras: list[CustomLoraDefinition] = Field(
        [], description="A list of LoRAs that are currently connected to this point in the flow."
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
    tags: list[str] = Field([], description="Tags describing this flow.")
    sub_flows: list[SubFlow] = Field(
        [], description="A list of subflows derived from this flow, allowing customization or extension."
    )
    models: list[AIResourceModel] = Field([], description="A list of models used by the ComfyUI workflow.")
    input_params: list[dict] = Field(
        ..., description="Initial set of parameters required to launch the flow, potentially modifiable by subflows."
    )
    version: str = Field("", description="Internal version of the flow in major.minor format.")
    requires: list[str] = Field([], description="Required external workflow dependencies.")
    private: bool = Field(False, description="Whether the workflow is missing from the `FLOWS_CATALOG_URL`")
    hidden: bool = Field(
        False, description="Flag for hiding flow from UI when flow is intended for use only in some special cases."
    )
    new_version_available: str = Field("", description="If not empty, contains the new version of the workflow.")
    is_seed_supported: bool = Field(
        True, description="Flag determining if 'Random Seed' input will be displayed in the UI."
    )
    is_count_supported: bool = Field(
        True, description="Flag determining if 'Number of images' input will be displayed in the UI."
    )
    is_translations_supported: bool = Field(
        False, description="Flag that determines whether Flow supports prompt translations."
    )
    is_macos_supported: bool = Field(
        True, description="Flag indicating whether the macOS PyTorch version can correctly run this flow."
    )
    is_supported_by_workers: bool = Field(
        True, description="Flag indicating if this flow can run on workers based on their capabilities."
    )
    required_memory_gb: float = Field(
        0.0, description="Minimum amount of memory (in gigabytes) required to execute this flow."
    )
    lora_connect_points: dict[str, LoraConnectionPoint] = Field(
        {},
        description="Connection points in the flow where LoRAs can be dynamically integrated, "
        "enabling the addition of custom LoRAs at specific locations. "
        "Key is a unique ID that used to reference specific connection during Flow editing.",
    )
    is_surprise_me_supported: bool = Field(
        False, description="Flag indicating if Flow supports random prompt generation feature."
    )
    remote_vae: bool = Field(False, description="Flag indicating whether Flow supports remote VAE decoding.")

    @field_validator("name", mode="after")
    @classmethod
    def lowercase_name(cls, value: str) -> str:
        return value.lower()

    def __hash__(self):
        return hash(self.name)

    def __eq__(self, other):
        return isinstance(other, AIResourceModel) and self.name == other.name

    @model_validator(mode="after")
    def fill_surprise_me(self) -> Self:
        self.is_surprise_me_supported = bool(
            self.is_count_supported and any(param.get("name") == "prompt" for param in self.input_params)
        )
        return self


class FlowProgressInstall(BaseModel):
    """Represents the progress status of a flow installation process."""

    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="The name of the flow being installed.")
    flow: Flow | None = Field(None, description="Parsed information about Flow in Visionatrix format.")
    flow_comfy: dict = Field(..., description="The ComfyUI workflow which are installed.")
    progress: float = Field(..., description="The current progress of the installation, ranging from 0 to 100.")
    error: str = Field("", description="Details of any error encountered during the installation process.")
    started_at: datetime = Field(..., description="Timestamp when the installation process started.")
    updated_at: datetime = Field(..., description="Timestamp of the last update to the installation progress.")

    @classmethod
    def from_orm_with_progress(cls, orm_obj, progress: float) -> Self:
        data = orm_obj.__dict__.copy()
        data["progress"] = progress
        return cls.model_validate(data)

    @field_validator("name", mode="after")
    @classmethod
    def lowercase_name(cls, value: str) -> str:
        return value.lower()


class ModelProgressInstall(BaseModel):
    """Represents the progress status of a model installation process."""

    model_config = ConfigDict(from_attributes=True)
    name: str = Field(..., description="Unique name of the model being installed.")
    flow_name: str = Field(..., description="Name of the flow requesting the installation.")
    progress: float = Field(..., description="The current progress of the installation, ranging from 0 to 100.")
    error: str = Field("", description="Details of any error encountered during the installation process.")
    started_at: datetime = Field(..., description="Timestamp when the installation process started.")
    updated_at: datetime = Field(..., description="Timestamp of the last update to the installation record.")
    file_mtime: float | None = Field(
        None, description="Last modification time of the model file, as a floating-point timestamp."
    )
    filename: str | None = Field(None, description="Filename of the model on the filesystem.")


class TaskDetailsInput(BaseModel):
    """Information about input file to a ComfyUI workflow."""

    file_name: str = Field(..., description="Format of name is 'task_id' + '_' + 'index'")
    file_size: int = Field(..., description="Size of file in bytes.")


class TaskDetailsOutput(BaseModel):
    """Contains information for retrieving the results of a ComfyUI workflow."""

    comfy_node_id: int = Field(..., description="ID of the ComfyUI node containing the result.")
    type: str = Field(
        ...,
        description="Type of the result from the ComfyUI node - "
        "can be either 'image', 'image-mask', 'image-animated', 'video' or 'audio'.",
    )
    file_size: int = Field(-1, description="Size of file(s) in bytes.")
    batch_size: int = Field(-1, description="Count of outputs(files) produced by node.")


class TaskDetailsShort(BaseModel):
    """Brief information about the Task."""

    task_id: int = Field(..., description="Unique identifier of the task.")
    priority: int = Field(0, description="Local task priority, from 0 to 15. Default is 0.")
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
    translated_input_params: dict | None = Field(
        None, description="If auto-translation feature is enabled, contains translations for input values."
    )
    extra_flags: ExtraFlags | None = Field(
        None, description="Set of additional options and flags that affect how the task is executed."
    )
    hidden: bool = Field(
        ..., description="Flag showing is this the internal task that should not be displayed by default."
    )

    @model_validator(mode="after")
    def adjust_priority(self) -> Self:
        """
        The database stores a global priority which is for internal use only,
        so we need to get the local priority only within the group, which is the last 4 bits of the number.
        """
        self.priority = self.priority & 0b1111
        return self

    @field_validator("hidden", mode="before")
    @classmethod
    def preprocess_hidden(cls, value: Any) -> bool:
        return bool(value)


class TaskDetails(TaskDetailsShort):
    """Detailed information about the Task."""

    created_at: datetime = Field(..., description="Task creation time.")
    updated_at: datetime | None = Field(None, description="Last task update time.")
    finished_at: datetime | None = Field(None, description="Finish time of the task.")
    flow_comfy: dict = Field(..., description="The final generated ComfyUI workflow.")
    user_id: str = Field(..., description="User ID to whom the task belongs.")
    webhook_url: str | None = Field(None, description="URL that was set to be called when the task state changes.")
    webhook_headers: dict | None = Field(None, description="Headers that were set to be sent to the webhook URL.")
    execution_details: ExecutionDetails | None = Field(
        None,
        description="Profiling information about task execution, present only if profiling was enabled for this task.",
    )
    custom_worker: str | None = Field(
        None, description="ID of the worker to which the task was explicitly assigned, if specified."
    )


class NodeProfiling(BaseModel):
    """Represents profiling information for a single node in the workflow."""

    execution_time: float = Field(..., description="Execution time of the node in seconds.")
    gpu_memory_usage: float = Field(..., description="GPU memory consumed by the node in MB.")
    class_type: str = Field(..., description="Class type of the node.")
    title: str = Field(..., description="Title of the node.")
    node_id: str = Field(..., description="Unique identifier of the node.")


class ComfyEngineDetails(BaseModel):
    """Performance options that ComfyUI is running with."""

    disable_smart_memory: bool | None = Field(
        None, description="Flag indicating whether ComfyUIs 'smart memory' was disabled."
    )
    vram_state: str | None = Field(None, description="Current VRAM management mode used by ComfyUI.")
    cache_type: str = Field("classic", description="The type of cache that is in use (classic, lru, none).")
    cache_size: int = Field(1, description="How many node results to cache (applies only when cache_type is lru).")
    vae_cpu: bool = Field(False, description="Does decoding VAE on CPU is enabled.")
    reserve_vram: float = Field(0.6, description="Amount of VRAM in GB reserved for use by other software.")


class ExecutionDetails(ComfyEngineDetails):
    """Contains profiling information for the entire task execution."""

    nodes_profiling: list[NodeProfiling] | None = Field(
        None, description="Profiling information for each node in the workflow."
    )
    max_memory_usage: float | None = Field(None, description="Maximum GPU memory usage during task execution in MB.")
    nodes_execution_time: float | None = Field(
        None, description="Execution time of all ComfyUI nodes in the workflow in seconds."
    )


class ExtraFlags(BaseModel):
    """Additional options and flags that were applied during task execution."""

    profiler_execution: bool = Field(False, description="Whether profiling was enabled during task execution.")
    unload_models: bool = Field(False, description="Whether all models were unloaded before task execution.")
    federated_task: bool = Field(False, description="Whether the task originated from a federated instance.")
    save_metadata: bool = Field(False, description="Whether the ComfyUI workflow metadata was saved.")
    smart_memory: bool = Field(False, description="Whether ComfyUI smart memory was enabled.")
    cache_type: str = Field("classic", description="The type of cache that was used (classic, lru, none).")
    cache_size: int = Field(1, description="How many node results were cached (applied only when cache_type was lru).")
    vae_cpu: bool = Field(False, description="Flag indicating was VAE decoded on the CPU or not.")
    reserve_vram: float = Field(0.6, description="Amount of VRAM in GB that was reserved for use by other software..")


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
    engine_details: ComfyEngineDetails = Field(...)


class WorkerSettingsRequest(BaseModel):
    """Custom settings available to be set dynamically for a worker."""

    worker_id: str = Field(..., description="ID of the worker")
    tasks_to_give: list[str] | None = Field(None, description="List of tasks the worker should ask for.")
    smart_memory: bool | None = Field(None, description="Should ComfyUI smart memory be enabled.")
    cache_type: str | None = Field(None, description="The type of cache to use (classic, lru, none).")
    cache_size: int | None = Field(None, description="How many node results to cache (when cache_type is lru).")
    vae_cpu: bool | None = Field(None, description="Should VAE be decoded on the CPU or not.")
    reserve_vram: float | None = Field(None, description="Amount of VRAM in GB to reserve for use.")


class WorkerDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: str = Field(..., description="The foreign key from the 'users' table, non-nullable.")
    worker_id: str = Field(
        ...,
        description="Uniq identifier for the worker, constructed from user_id, hostname, device name and device index."
        "If 'federated_instance_name' is specified it will be added to this field automatically.",
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
    pytorch_version: str | None = Field(None, description="Version of PyTorch.")
    engine_details: ComfyEngineDetails | None = Field(...)
    federated_instance_name: str = Field("", description="Name of the federated instance to which the worker belongs.")
    empty_task_requests_count: int = Field(
        0,
        description="Counts the number of times the worker requested a task but received none. "
        "A value of 0 indicates that the worker is busy, "
        "while a value of 1 or more indicates that the worker is free.",
    )
    last_asked_tasks: list[str] = Field(
        [], description="List of flows IDs that the worker last requested to be processed."
    )
    smart_memory: bool | None = Field(None, description="Should ComfyUI smart memory be enabled.")
    cache_type: str | None = Field(None, description="The type of cache to use (classic, lru, none).")
    cache_size: int | None = Field(None, description="How many node results to cache (when cache_type is lru).")
    vae_cpu: bool | None = Field(None, description="Should VAE be decoded on the CPU or not.")
    reserve_vram: float | None = Field(None, description="Amount of VRAM in GB to reserve for use.")

    @model_validator(mode="after")
    def adjust_worker_id(self) -> Self:
        """If federated_instance_name is present we add it to the worker_id."""
        if self.federated_instance_name and not self.worker_id.endswith(self.federated_instance_name):
            self.worker_id += f":{self.federated_instance_name}"
        return self


class UserInfo(BaseModel):
    """Minimum information provided by Authentication backends about user."""

    model_config = ConfigDict(from_attributes=True)
    user_id: str = Field(..., description="Unique user ID.")
    full_name: str = Field("", description="Full name of the user.")
    email: str = Field("", description="Email name of the user.")
    is_admin: bool = Field(False, description="Flag showing is user is admin.")
    record_expires_at: datetime | None = Field(
        None, description="UTC timestamp after which the user record is redundant."
    )


class ComfyUIFolderPath(BaseModel):
    """Represents a folder path in ComfyUI with metadata, including modification options, creation time, and size."""

    full_path: str = Field(..., description="The full filesystem path of the folder.")
    create_time: datetime = Field(..., description="The folder's creation time as a datetime object.")
    total_size: int = Field(..., description="The total size of the folder in bytes.")


class ComfyUIFolderPaths(BaseModel):
    """Represents a mapping of folder keys to their corresponding folder paths and metadata."""

    folders: dict[str, list[ComfyUIFolderPath]] = Field(
        ..., description="A mapping of folder keys to a list of folder paths with metadata."
    )


class ComfyUIFolderPathDefinition(BaseModel):
    """Represents a simplified version of ComfyUI folder paths for storage purposes in the database."""

    folder_key: str = Field(..., description="The folder key (e.g., 'checkpoints', 'vae').")
    path: str = Field(..., description="The full or relative filesystem path to the folder.")

    def __hash__(self):
        return hash((self.folder_key, self.path))

    def __eq__(self, other):
        if not isinstance(other, ComfyUIFolderPathDefinition):
            return False
        return self.folder_key == other.folder_key and self.path == other.path


class OrphanModel(BaseModel):
    """
    Represents an orphaned model file that is not associated with any currently installed flow.

    This model provides detailed information about the orphaned file, including its
    size, potential usage in flows, and any matching AIResourceModel, if available.
    """

    path: str = Field(..., description="The relative path of the orphaned model file within 'models_dir' directory.")
    full_path: str = Field(..., description="Full path to the orphaned model file.")
    size: int = Field(..., description="Size of the orphaned model file in bytes.")
    creation_time: float = Field(..., description="The file's creation time in seconds.")
    res_model: AIResourceModel | None = Field(None, description="AIResourceModel describing the file, if any matches.")
    possible_flows: list[Flow] = Field([], description="List of possible flows that could potentially use this model.")

    def __hash__(self):
        return hash(self.path)

    def __eq__(self, other):
        return isinstance(other, OrphanModel) and self.path == other.path


class TaskUpdateRequest(BaseModel):
    """
    Represents the fields that can be updated for a task that has not yet started execution.

    This model allows clients to specify new values for task properties that are editable
    before the task begins processing.
    """

    priority: Annotated[
        int | None,
        Field(
            strict=True,
            ge=0,
            le=15,
            description="New priority level for task. Higher numbers indicate higher priority. Maximum value is 15.",
        ),
    ]


class OllamaModelItem(BaseModel):
    """Represents a single model file on the Ollama server."""

    model: str = Field(..., description="Name of the model.")
    size: int = Field(..., description="Size of the model file in bytes.")
    modified_at: float = Field(..., description="Unix timestamp of the last modification time of the model file.")


class TranslatePromptRequest(BaseModel):
    """Represents the request data for translating an image generation prompt."""

    prompt: str = Field(..., description="The image generation prompt to translate.")
    system_prompt: str = Field(None, description="System instructions that are passed to the LLM.")


class TranslatePromptResponse(BaseModel):
    """
    Represents the response data after translating an image generation prompt.

    Contains the original prompt provided by the user, the translated prompt in English,
    and the reason the translation process completed.
    """

    prompt: str = Field(..., description="The original prompt provided in the request.")
    result: str = Field(..., description="The translated prompt in English.")
    done_reason: str = Field(..., description="The reason the translation generation was completed.")


class TaskCreationBasicParams(BaseModel):
    group_scope: int = Field(1, description="Group number to which task should be assigned.", ge=1, le=255)
    priority: int = Field(0, description="Execution priority. Higher numbers indicate higher priority.", ge=0, le=15)
    child_task: int = Field(0, description="Int boolean indicating whether to create a relation between tasks")
    webhook_url: str = Field(
        "",
        description=(
            "Optional. URL to call when task state changes."
            " Leave empty if not needed or if using `/progress` or `/progress-summary` endpoints."
        ),
    )
    webhook_headers: str = Field(
        "",
        description=(
            "Optional. Headers for webhook URL as an encoded JSON string. Used only when `webhook_url` is set."
        ),
    )


class TaskCreationCountParam(BaseModel):
    count: int = Field(1, description="Number of tasks to be created.", ge=1)


class TaskCreationTranslateParam(BaseModel):
    translate: int = Field(0, description="Should the prompt be translated if auto-translation option is enabled.")


class TaskCreationSeedParam(BaseModel):
    seed: int = Field(1, description="The `seed` parameter for reproducing the results of workflows.")


class TaskCreationWithTranslateParam(TaskCreationTranslateParam, TaskCreationBasicParams):
    model_config = ConfigDict(extra="ignore")


class TaskCreationWithCountParam(TaskCreationCountParam, TaskCreationBasicParams):
    model_config = ConfigDict(extra="ignore")


class TaskCreationWithSeedParam(TaskCreationSeedParam, TaskCreationBasicParams):
    model_config = ConfigDict(extra="ignore")


class TaskCreationWithTranslateAndSeedParams(
    TaskCreationTranslateParam, TaskCreationSeedParam, TaskCreationBasicParams
):
    model_config = ConfigDict(extra="ignore")


class TaskCreationWithTranslateAndCountParams(
    TaskCreationTranslateParam, TaskCreationCountParam, TaskCreationBasicParams
):
    model_config = ConfigDict(extra="ignore")


class TaskCreationWithCountAndSeedParams(TaskCreationCountParam, TaskCreationSeedParam, TaskCreationBasicParams):
    model_config = ConfigDict(extra="ignore")


class TaskCreationWithFullParams(
    TaskCreationTranslateParam, TaskCreationCountParam, TaskCreationSeedParam, TaskCreationBasicParams
):
    model_config = ConfigDict(extra="ignore")


class CustomLoraDefinitionRequest(BaseModel):
    """Represents a custom LoRA model to be embedded in the flow."""

    strength_model: float = Field(1.0, description="Default strength of the LoRA model.")
    display_name: str = Field(..., description="Text to display for the LoRA slider.")
    model_url: str = Field(..., description="The CivitAI URL for this model, allowing to embed this model in Flow.")


class FlowMetadataUpdate(BaseModel):
    display_name: str = Field(..., description="New display name for the flow.")
    description: str | None = Field(None, description="Updated description of the flow.")
    license: str | None = Field(None, description="Updated license for the flow.")
    required_memory_gb: float | None = Field(None, description="Updated required memory (in GB) for the flow.")
    version: str | None = Field(None, description="Updated version of the flow.")


class FlowCloneRequest(BaseModel):
    """
    Represents the data required to clone and modify an existing flow.

    This model is used to create a new flow by copying from an existing one
    and optionally updating its metadata, LoRA connection points, or other attributes.
    It allows for targeted customization while preserving the base functionality of the original flow.
    """

    original_flow_name: str = Field(..., description="Name of the installed flow to clone from.")

    new_name: str = Field(..., description="New internal name for the cloned flow (must be unique).")
    metadata: FlowMetadataUpdate = Field(..., description="New metadata to apply to the cloned flow.")

    lora_connection_points: dict[str, list[CustomLoraDefinitionRequest]] | None = Field(
        default=None,
        description="Optional LoRA connection points for the new flow. These should align with the connection points "
        "defined in the original flow.",
    )

    @field_validator("original_flow_name", "new_name", mode="after")
    @classmethod
    def lowercase_name(cls, value: str) -> str:
        return value.lower()


class VisionatrixUpdateStatus(BaseModel):
    """
    Represents the update status of Visionatrix.

    - current_version: The version currently running.
    - target_version: The version available for update (if any).
    """

    current_version: str = Field(..., description="The current version of Visionatrix.")
    next_version: str = Field("", description="The version for update if available.")


class FederatedInstanceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    instance_name: str = Field(..., description="Unique name of the federated instance.")
    url_address: str = Field(..., description="Address of the federated instance.")
    username: str = Field(..., description="The username present on the remote instance.")
    password: str = Field(..., description="Password for the username.")
    enabled: bool = Field(default=True, description="Indicates if the federated instance is currently active.")


class FederatedInstance(FederatedInstanceCreate):
    model_config = ConfigDict(from_attributes=True)
    created_at: datetime = Field(..., description="Timestamp when the federated instance record was created.")
    installed_flows: dict[str, str] = Field(
        ..., description="A dictionary with installed Flows identifiers and their versions."
    )


class FederatedInstanceUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    url_address: str | None = Field(None, description="New address of the federated instance.")
    username: str | None = Field(None, description="New username for the remote instance.")
    password: str | None = Field(None, description="New password for the username.")
    enabled: bool | None = Field(None, description="New active status for the federated instance.")


class FlowDelegationConfig(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    flow_name: str = Field(..., description="Unique identifier for the flow.")
    delegation_threshold: int = Field(
        ..., description="Queue length threshold for delegation (0 means delegate immediately)."
    )


class FederatedInstanceInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    workers: list[WorkerDetails] = Field([], description="List of available workers on the instance.")
    installed_flows: dict[str, str] = Field(
        {}, description="A dictionary with installed Flows identifiers and their versions."
    )


class BackgroundJobLockModel(BaseModel):
    """
    Represents the state and locking information for a background job
    as stored in the database, used for coordination across multiple web workers.
    """

    model_config = ConfigDict(from_attributes=True)

    job_name: str = Field(
        ..., description="Unique name identifying the background job (corresponds to the primary key)."
    )
    worker_id: str | None = Field(
        None, description="Identifier (e.g., 'hostname:pid') of the worker process currently holding the lock."
    )
    expires_at: datetime | None = Field(
        None,
        description="Timestamp (UTC) indicating when the current lock expires if not renewed by a heartbeat. "
        "Null if unlocked.",
    )
    last_run_at: datetime | None = Field(
        None, description="Timestamp (UTC) indicating when this job last started execution."
    )

    @field_validator("expires_at", "last_run_at", mode="before")
    @classmethod
    def ensure_aware_datetime(cls, value: Any) -> datetime | None:
        """
        Ensures that datetime fields read from the database are timezone-aware (UTC).

        SQLAlchemy/DB drivers might return naive datetimes even if stored aware,
        especially with backends like SQLite. We assume naive datetimes from DB represent UTC time.
        """
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
