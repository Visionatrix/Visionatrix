import asyncio
import logging

import httpx

from .db_queries import (
    get_enabled_federated_instances,
    update_installed_flows_for_federated_instance,
    update_local_workers_from_federation,
)
from .pydantic_models import FederatedInstance, FederatedInstanceInfo

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
    except Exception as e:
        LOGGER.exception("Error fetching workers from federated instance %s: %s", federated_instance.instance_name, e)
    return federated_instance.instance_name, None


async def federation_sync_engine(exit_event: asyncio.Event):
    """Periodically synchronizes workers from federated instances into the local workers table."""
    while True:
        if exit_event.is_set():
            break

        federated_instances = await get_enabled_federated_instances()

        tasks = [get_instance_data(instance) for instance in federated_instances]
        results = await asyncio.gather(*tasks)

        if exit_event.is_set():
            break

        for res in results:
            if res[1] is None:
                continue
            instance_name = res[0]
            instance_data: FederatedInstanceInfo = res[1]
            await update_local_workers_from_federation(instance_name, instance_data.workers)
            await update_installed_flows_for_federated_instance(instance_name, instance_data.installed_flows)
        try:
            await asyncio.wait_for(exit_event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            continue


async def federation_tasks_engine(exit_event: asyncio.Event):
    while True:
        if exit_event.is_set():
            break

        # federated_instances = await get_enabled_federated_instances()
        # workers = get_free_federated_workers(5)

        # Get current Queue (that includes all non-locked tasks)
        # Sort it by flow's names
        # Apply filtering by `delegation_threshold` (we skip this step for now)
        # Lock the tasks that will be send.
        # Create the tasks (1 task for worker for 1 federated instance).
        #   Note: Remote instance should reject the task creation if the worker becomes busy.
        # Unlock tasks which creation were rejected.
        # For each created task a new background job is spawned to track it's process.

        try:
            await asyncio.wait_for(exit_event.wait(), timeout=1.0)
        except asyncio.TimeoutError:
            continue
