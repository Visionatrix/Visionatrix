import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from .db_queries import (
    get_enabled_federated_instances,
    update_installed_flows_for_federated_instance,
    update_local_workers_from_federation,
)
from .pydantic_models import FederatedInstance, FederatedInstanceInfo, WorkerDetails
from .tasks_engine import (
    get_task_files,
    get_task_for_federated_worker,
    remove_task_lock,
)

LOGGER = logging.getLogger("visionatrix")


async def get_instance_data(federated_instance: FederatedInstance) -> [str, FederatedInstanceInfo | None]:
    url = federated_instance.url_address.rstrip("/") + "/vapi/federation/instance_info"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, auth=(federated_instance.username, federated_instance.password))
            if response.status_code == 200:
                instance_data = FederatedInstanceInfo.model_validate(response.json())
                LOGGER.debug(
                    "Fetched %d workers from instance %s", len(instance_data.workers), federated_instance.instance_name
                )
                return federated_instance.instance_name, instance_data
            LOGGER.error(
                "Instance %s returned status %s when fetching workers",
                federated_instance.instance_name,
                response.status_code,
            )
            return federated_instance.instance_name, []
    except httpx.ConnectError:
        LOGGER.error("Cannot connect to federated instance %s: %s", federated_instance.instance_name, url)
    except httpx.TimeoutException:
        LOGGER.error("Timeout reading from federated instance %s: %s", federated_instance.instance_name, url)
    except Exception as e:
        LOGGER.exception("Error fetching workers from federated instance %s: %s", federated_instance.instance_name, e)
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


async def send_task_to_federated_instance(instance: FederatedInstance, worker: WorkerDetails, task_details: dict):
    custom_headers = {
        "X-WORKER-ID": worker.worker_id.removesuffix(f":{worker.federated_instance_name}"),
        "X-FEDERATED-TASK": "1",
    }
    input_files = get_task_files(task_details["task_id"], "input")
    files_data = {
        Path(input_file[0].removeprefix(task_details["task_id"])).stem: input_file[1] for input_file in input_files
    }
    input_params = task_details["input_params"]
    if task_details.get("translated_input_params"):
        for i, v in task_details["translated_input_params"].items():
            input_params[i] = v
    form_data = {
        "count": 1,
        **input_params,
    }
    async with httpx.AsyncClient(auth=(instance.username, instance.password)) as client:
        try:
            response = await client.put(
                f"{instance.url_address}/vapi/tasks/create/{task_details['name']}",
                data=form_data,
                files=files_data,
                headers=custom_headers,
                timeout=30,
            )
            print("send!:", response.status_code)
        finally:
            await remove_task_lock(task_details["task_id"])
