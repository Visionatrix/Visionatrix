import asyncio
import builtins
import logging
import time
from contextlib import ExitStack
from datetime import datetime, timedelta, timezone
from email.message import Message
from pathlib import Path

import httpx

from . import options
from .db_queries import (
    get_enabled_federated_instances,
    update_installed_flows_for_federated_instance,
    update_local_workers_from_federation,
)
from .pydantic_models import (
    ExecutionDetails,
    FederatedInstance,
    FederatedInstanceInfo,
    WorkerDetails,
)
from .tasks_engine import (
    get_task_files,
    get_task_for_federated_worker,
    remove_task_lock,
    update_task_progress_database,
)
from .tasks_engine_async import update_task_outputs_async
from .webhooks import webhook_task_progress

LOGGER = logging.getLogger("visionatrix")
CONNECT_ERROR_COUNTS = {}


async def get_instance_data(federated_instance: FederatedInstance) -> [str, FederatedInstanceInfo | None]:
    url = federated_instance.url_address.rstrip("/") + "/vapi/federation/instance_info"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, auth=(federated_instance.username, federated_instance.password))
            if response.status_code == httpx.codes.OK:
                CONNECT_ERROR_COUNTS[federated_instance.instance_name] = 0
                json_response = response.json()
                for worker in json_response["workers"]:
                    worker["federated_instance_name"] = federated_instance.instance_name
                instance_data = FederatedInstanceInfo.model_validate(json_response)
                LOGGER.debug(
                    "Fetched %d workers from instance %s", len(instance_data.workers), federated_instance.instance_name
                )
                return federated_instance.instance_name, instance_data
            LOGGER.error(
                "Instance %s returned status %s when fetching workers",
                federated_instance.instance_name,
                response.status_code,
            )
    except httpx.ConnectError:
        count = CONNECT_ERROR_COUNTS.get(federated_instance.instance_name, 0) + 1
        CONNECT_ERROR_COUNTS[federated_instance.instance_name] = count
        if count % 5 == 0:
            LOGGER.warning("Cannot connect to federated instance %s: %s", federated_instance.instance_name, url)
    except httpx.TimeoutException:
        LOGGER.error("Timeout reading from federated instance %s: %s", federated_instance.instance_name, url)
    except httpx.RequestError:
        LOGGER.exception("Error fetching workers from federated instance %s.", federated_instance.instance_name)
    return federated_instance.instance_name, None


async def federation_engine(exit_event: asyncio.Event):
    background_tasks = set()

    while True:
        if exit_event.is_set():
            break

        start_time = time.perf_counter()

        federated_instances = await get_enabled_federated_instances()
        get_instance_data_tasks = [get_instance_data(instance) for instance in federated_instances]
        if get_instance_data_tasks:
            get_instance_data_tasks_results = await asyncio.gather(*get_instance_data_tasks)

            if exit_event.is_set():
                break

            time_threshold = datetime.now(timezone.utc) - timedelta(seconds=15.0)
            instances_dict = {
                instance.instance_name: {"instance": instance, "tasks": []} for instance in federated_instances
            }
            free_workers_dict: [str, WorkerDetails] = {}

            for res in get_instance_data_tasks_results:
                if res[1] is None:
                    continue
                instance_name = res[0]
                instance_data: FederatedInstanceInfo = res[1]
                await update_local_workers_from_federation(instance_name, instance_data.workers)
                await update_installed_flows_for_federated_instance(instance_name, instance_data.installed_flows)

                free_workers_dict[instance_name] = [
                    worker
                    for worker in instance_data.workers
                    if worker.last_seen.replace(tzinfo=timezone.utc) >= time_threshold
                    and worker.empty_task_requests_count > 1
                ]

            if exit_event.is_set():
                break

            for instance, workers in free_workers_dict.items():
                for worker in workers:
                    federated_task = await get_task_for_federated_worker(worker.last_asked_tasks)
                    if federated_task:
                        instances_dict[instance]["tasks"].append((worker, federated_task))

            for instance_data in instances_dict.values():
                instance = instance_data["instance"]
                for worker, federated_task in instance_data["tasks"]:
                    t = asyncio.create_task(send_task_to_federated_instance(instance, worker, federated_task))
                    background_tasks.add(t)
                    t.add_done_callback(background_tasks.discard)

        remaining = 3.0 - (time.perf_counter() - start_time)
        if remaining > 0:
            try:
                await asyncio.wait_for(exit_event.wait(), timeout=remaining)
            except asyncio.TimeoutError:
                continue


async def send_task_to_federated_instance(
    instance: FederatedInstance, worker: WorkerDetails, task_details: dict
) -> None:
    custom_headers = {
        "X-WORKER-ID": worker.worker_id.removesuffix(f":{worker.federated_instance_name}"),
        "X-FEDERATED-TASK": "1",
    }
    input_files = get_task_files(task_details["task_id"], "input")
    task_prefix = str(task_details["task_id"]) + "_"
    with ExitStack() as stack:
        files = {}
        for file_name, file_path in input_files:
            input_file_param_name = Path(file_name.removeprefix(task_prefix)).stem
            files[input_file_param_name] = stack.enter_context(builtins.open(file_path, "rb"))
        input_params = task_details["input_params"]
        if task_details.get("translated_input_params"):
            for i, v in task_details["translated_input_params"].items():
                input_params[i] = v
        form_data = {
            "count": 1,
            **input_params,
        }
        async with httpx.AsyncClient(
            base_url=f"{instance.url_address}", auth=(instance.username, instance.password), timeout=30
        ) as client:
            try:
                response = await client.put(
                    f"/vapi/tasks/create/{task_details['name']}",
                    data=form_data,
                    files=files,
                    headers=custom_headers,
                )
                if response.status_code != httpx.codes.OK:
                    if response.status_code == httpx.codes.BAD_REQUEST:
                        LOGGER.info("Remote server rejected task with error: %s.", response.content)
                    else:
                        LOGGER.warning("Remote server responded with unexpected status: %s.", response.status_code)
                    return
                await track_task_execution(client, response.json()["tasks_ids"][0], task_details, worker)
            except httpx.RequestError:
                LOGGER.exception("Failed to send task for execution.")
            finally:
                await remove_task_lock(task_details["task_id"])


async def track_task_execution(
    client: httpx.AsyncClient, remote_task_id: int, task_details: dict, worker: WorkerDetails
) -> None:
    task_id = task_details["task_id"]
    max_transport_errors = 3
    task_progress = 0.0
    execution_time = 0.0

    while True:
        try:
            response = await client.get(f"/vapi/tasks/progress/{remote_task_id}")
            max_transport_errors = 3
            if response.status_code == httpx.codes.OK:
                task_data = response.json()
                task_progress = task_data["progress"]
                execution_time = task_data["execution_time"]
                execution_details = task_data["execution_details"]
                if task_progress == 100.0:
                    await retrieve_task_results(client, task_id, remote_task_id, task_data)
                if not await update_task_progress_database(
                    task_id,
                    task_progress,
                    task_data["error"],
                    execution_time,
                    worker.worker_id,
                    None,
                    ExecutionDetails.model_validate(execution_details) if execution_details else None,
                ):
                    await federation_remove_task(client, remote_task_id)
                    if task_details["webhook_url"]:
                        await webhook_task_progress(
                            task_details["webhook_url"],
                            task_details["webhook_headers"],
                            task_id,
                            task_progress,
                            execution_time,
                            "Failed to update task progress.",
                        )
                    return
                if task_details["webhook_url"]:
                    await webhook_task_progress(
                        task_details["webhook_url"],
                        task_details["webhook_headers"],
                        task_id,
                        task_progress,
                        execution_time,
                        task_data["error"],
                    )
                if task_data["error"]:
                    await federation_remove_task(client, remote_task_id)
                    return
                if task_progress == 100.0:
                    await federation_remove_task(client, remote_task_id)
                    return
        except httpx.RequestError:
            max_transport_errors -= 1
            if not max_transport_errors:
                await federation_remove_task(client, remote_task_id)
                if task_details["webhook_url"]:
                    await webhook_task_progress(
                        task_details["webhook_url"],
                        task_details["webhook_headers"],
                        task_id,
                        task_progress,
                        execution_time,
                        "Federation: Transport error.",
                    )
        await asyncio.sleep(1.0)


async def federation_remove_task(client: httpx.AsyncClient, remote_task_id: int) -> None:
    try:
        response = await client.delete("/vapi/tasks/task", params={"task_id": remote_task_id})
        if response.status_code != httpx.codes.NO_CONTENT:
            LOGGER.error("Removing federated task returned %s status code.", response.status_code)
    except httpx.RequestError:
        LOGGER.exception("Failed to remove task %s from federation.", remote_task_id)


async def retrieve_task_results(client: httpx.AsyncClient, task_id: int, remote_task_id: int, task_details: dict):
    for output in task_details["outputs"]:
        node_id = output["comfy_node_id"]
        params = {
            "task_id": remote_task_id,
            "node_id": node_id,
        }
        try:
            for i in range(output["batch_size"]):
                params["batch_index"] = i
                result_response = await client.get("/vapi/tasks/results", params=params)
                if result_response.status_code != httpx.codes.OK:
                    LOGGER.error(
                        "Failed to retrieve result for task=%s, node=%s: %s",
                        remote_task_id,
                        node_id,
                        result_response.text,
                    )
                    continue
                msg = Message()
                msg["content-disposition"] = result_response.headers["content-disposition"]
                filename = str(task_id) + "_" + msg.get_filename().removeprefix(f"{remote_task_id}_")
                file_path = Path(options.OUTPUT_DIR).joinpath("visionatrix").joinpath(filename)
                with builtins.open(file_path, mode="wb") as out_file:
                    out_file.write(result_response.content)
            await update_task_outputs_async(task_id, task_details["outputs"])
        except httpx.RequestError:
            LOGGER.exception("Failed to retrieve result for task=%s, node=%s.", remote_task_id, node_id)
            continue
