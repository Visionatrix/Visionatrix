import logging

import httpx

LOGGER = logging.getLogger("visionatrix")


async def webhook_task_progress(
    url: str, headers: dict | None, task_id: int, progress: float, execution_time: float, error: str
) -> None:
    try:
        async with httpx.AsyncClient(base_url=url, timeout=3.0) as client:
            await client.post(
                url="task-progress",
                json={
                    "task_id": task_id,
                    "progress": progress,
                    "execution_time": execution_time,
                    "error": error,
                },
                headers=headers,
            )
    except httpx.RequestError as e:
        LOGGER.exception("Exception during calling webhook %s, progress=%s: %s", url, progress, e)
