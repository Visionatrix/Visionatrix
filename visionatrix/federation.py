import asyncio
import logging

import httpx

from .db_queries import (
    get_enabled_federated_instances,
    update_local_workers_from_federation,
)
from .pydantic_models import FederatedInstance, WorkerDetails

LOGGER = logging.getLogger("visionatrix")


async def get_workers_from_instance(federated_instance: FederatedInstance) -> [str, list[WorkerDetails]]:
    """Contacts a federated instance (given by the database record) to fetch its current workers.
    Assumes the instance provides a GET endpoint at /workers/info and uses HTTP Basic auth.
    """
    url = federated_instance.url_address.rstrip("/") + "/vapi/workers/info"
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(url, auth=(federated_instance.username, federated_instance.password))
            if response.status_code == 200:
                workers_data = response.json()
                workers = [WorkerDetails.model_validate(worker) for worker in workers_data]
                LOGGER.debug("Fetched %d workers from instance %s", len(workers), federated_instance.instance_name)
                return federated_instance.instance_name, workers
            LOGGER.error(
                "Instance %s returned status %s when fetching workers",
                federated_instance.instance_name,
                response.status_code,
            )
            return federated_instance.instance_name, []
    except Exception as e:
        LOGGER.exception("Error fetching workers from federated instance %s: %s", federated_instance.instance_name, e)
        return federated_instance.instance_name, []


async def federation_sync_engine(exit_event: asyncio.Event):
    """Periodically synchronizes workers from federated instances into the local workers table."""
    while True:
        if exit_event.is_set():
            break

        federated_instances = await get_enabled_federated_instances()

        tasks = [get_workers_from_instance(instance) for instance in federated_instances]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        if exit_event.is_set():
            break

        for res in results:
            if isinstance(res, Exception):
                continue
            federation_instance_name, workers_list = res
            await update_local_workers_from_federation(federation_instance_name, workers_list)

        try:
            await asyncio.wait_for(exit_event.wait(), timeout=3.0)
        except asyncio.TimeoutError:
            continue
