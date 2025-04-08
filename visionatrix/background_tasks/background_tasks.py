import asyncio
import contextlib
import logging
import os
import platform
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import TypeVar

from sqlalchemy import null, or_, select, update
from sqlalchemy.exc import IntegrityError

from .. import database
from ..pydantic_models import BackgroundJobLockModel

DEFAULT_LOCK_TTL = timedelta(minutes=3)  # How long a lock is valid without renewal
CYCLE_SLEEP_TIME = 10  # How often the main cycle checks for jobs in seconds
BACKGROUND_JOB_WORKER_ID = f"{platform.node()}:{os.getpid()}"  # Unique ID for this worker process


@dataclass
class BackgroundJobDefinition:
    func: Callable[[asyncio.Event], Awaitable[None]]
    job_name: str
    run_immediately: bool = False  # Run as soon as possible after startup if never run
    interval: timedelta | None = None  # Run periodically if set
    lock_ttl: timedelta = DEFAULT_LOCK_TTL


JOB_REGISTRY: dict[str, BackgroundJobDefinition] = {}
LOGGER = logging.getLogger("visionatrix")
F = TypeVar("F", bound=Callable[[], Awaitable[None]])


def register_background_job(
    job_name: str,
    run_immediately: bool = False,
    interval: timedelta | None = None,
    lock_ttl: timedelta = DEFAULT_LOCK_TTL,
):
    """
    Decorator to register an async function as a background job.

    Args:
        job_name: Unique name for the job (used as DB lock key).
        run_immediately: If True, tries to run the job ASAP after startup if it hasn't run successfully before.
        interval: If set, runs the job periodically with this interval after successful completion.
        lock_ttl: Time duration the lock is held before expiring if not renewed.
    """

    def decorator(func: F) -> F:
        if not asyncio.iscoroutinefunction(func):
            raise TypeError(
                f"Background job function '{func.__name__}' must be an async function "
                f"(defined with 'async def'). Received type: {type(func)}"
            )
        if job_name in JOB_REGISTRY:
            raise ValueError(f"Background job '{job_name}' is already registered.")

        LOGGER.info(
            "Registering background job: '%s' (Function: %s, Interval: %s, Immediate: %s)",
            job_name,
            func.__name__,
            interval,
            run_immediately,
        )
        JOB_REGISTRY[job_name] = BackgroundJobDefinition(
            func=func,
            job_name=job_name,
            run_immediately=run_immediately,
            interval=interval,
            lock_ttl=lock_ttl,
        )
        return func  # Return the original function, as expected by decorators

    return decorator


async def run_background_jobs_cycle(exit_event: asyncio.Event):
    """The main loop that checks and potentially starts background jobs."""
    LOGGER.info("Worker %s: Starting background job cycle...", BACKGROUND_JOB_WORKER_ID)
    running_job_tasks: dict[str, asyncio.Task] = {}
    await asyncio.sleep(5)

    while not exit_event.is_set():
        now = datetime.now(timezone.utc)
        LOGGER.debug("Worker %s: Running background job check cycle at %s.", BACKGROUND_JOB_WORKER_ID, now)

        try:
            current_locks_list = await fetch_background_jobs_locks()
            current_locks = {lock.job_name: lock for lock in current_locks_list}
        except Exception as e:
            LOGGER.exception(
                "Worker %s: Failed to fetch background job locks, skipping cycle: %s", BACKGROUND_JOB_WORKER_ID, e
            )
            await asyncio.sleep(CYCLE_SLEEP_TIME)
            continue

        for job_name, job_def in JOB_REGISTRY.items():
            try:
                # 1. Skip if already running locally
                if job_name in running_job_tasks:
                    LOGGER.debug("Worker %s: Job '%s' is already running locally.", BACKGROUND_JOB_WORKER_ID, job_name)
                    continue

                lock_info = current_locks.get(job_name)
                should_attempt_acquire = False
                attempt_method = None  # Will be 'insert' or 'update'

                if lock_info:
                    # 2. Lock record exists in DB
                    # Check if locked by another VALID worker
                    is_locked_by_other_valid = (
                        lock_info.worker_id is not None
                        and lock_info.worker_id != BACKGROUND_JOB_WORKER_ID
                        and lock_info.expires_at is not None
                        and lock_info.expires_at > now
                    )

                    if is_locked_by_other_valid:
                        LOGGER.debug(
                            "Worker %s: Job '%s' is locked by another worker (%s) until %s.",
                            BACKGROUND_JOB_WORKER_ID,
                            job_name,
                            lock_info.worker_id,
                            lock_info.expires_at,
                        )
                        continue  # Skip this job for this cycle

                    # 3. Lock is NOT held by another valid worker. It might be expired, released, or held by us (stale).
                    # Determine if the job is DUE according to its schedule.
                    is_due_for_run = False
                    if job_def.interval:
                        if lock_info.last_run_at is None:
                            is_due_for_run = True
                            LOGGER.debug(
                                "Worker %s: Interval job '%s' due for first run (no last_run_at).",
                                BACKGROUND_JOB_WORKER_ID,
                                job_name,
                            )
                        elif now >= lock_info.last_run_at + job_def.interval:
                            is_due_for_run = True
                            LOGGER.debug(
                                "Worker %s: Interval (%s) passed for job '%s', due for run.",
                                BACKGROUND_JOB_WORKER_ID,
                                job_def.interval,
                                job_name,
                            )
                    elif job_def.run_immediately and lock_info.last_run_at is None:
                        is_due_for_run = True
                        LOGGER.debug(
                            "Worker %s: Immediate job '%s' due for first run (no last_run_at).",
                            BACKGROUND_JOB_WORKER_ID,
                            job_name,
                        )

                    # 3. Determine if the existing lock is EXPIRED (held by a worker, but past expiry)
                    # This indicates a previous run might have crashed
                    is_expired = (
                        lock_info.worker_id is not None  # Must have a worker_id to be expired
                        and lock_info.worker_id == BACKGROUND_JOB_WORKER_ID
                        and lock_info.expires_at is not None
                        and lock_info.expires_at <= now
                    )
                    if is_expired:
                        LOGGER.debug(
                            "Worker %s: Job '%s' lock held by worker '%s' appears expired (expired at %s).",
                            BACKGROUND_JOB_WORKER_ID,
                            job_name,
                            lock_info.worker_id,
                            lock_info.expires_at,
                        )

                    # 4. Decide whether to attempt acquisition via UPDATE
                    # Attempt ONLY if the job is due OR if the lock is expired (indicating crash recovery)
                    if is_due_for_run or is_expired:
                        should_attempt_acquire = True
                        attempt_method = "update"
                        LOGGER.debug(
                            "Worker %s: Job '%s' should attempt lock update (Due: %s, Expired: %s).",
                            BACKGROUND_JOB_WORKER_ID,
                            job_name,
                            is_due_for_run,
                            is_expired,
                        )
                else:
                    # Lock record does NOT exist in DB

                    # 5. Decide whether to attempt acquisition via INSERT (first run)
                    if job_def.run_immediately or job_def.interval:
                        should_attempt_acquire = True
                        attempt_method = "insert"
                        LOGGER.debug(
                            "Worker %s: Job '%s' has no lock info, attempting initial run (immediate=%s, interval=%s).",
                            BACKGROUND_JOB_WORKER_ID,
                            job_name,
                            job_def.run_immediately,
                            job_def.interval is not None,
                        )

                # --- Acquisition and Execution ---
                if should_attempt_acquire:
                    lock_acquired = False
                    if attempt_method == "insert":
                        lock_acquired = await try_insert_background_job_lock(job_name, job_def.lock_ttl)
                    elif attempt_method == "update":
                        lock_acquired = await try_update_background_job_lock(job_name, job_def.lock_ttl)
                    else:
                        # Should not happen with current logic, but safety check
                        LOGGER.error(
                            "Worker %s: Job '%s' should attempt acquire but method is unknown!",
                            BACKGROUND_JOB_WORKER_ID,
                            job_name,
                        )

                    if lock_acquired:
                        LOGGER.info(
                            "Worker %s: Acquired lock for '%s' via %s, starting job.",
                            BACKGROUND_JOB_WORKER_ID,
                            job_name,
                            attempt_method,
                        )

                        task = asyncio.create_task(run_background_job(exit_event, job_def))
                        task.add_done_callback(_make_done_callback(running_job_tasks, job_name))
                        running_job_tasks[job_name] = task

            except Exception as e:
                LOGGER.exception(
                    "Worker %s: Error processing background job '%s' in main cycle: %s",
                    BACKGROUND_JOB_WORKER_ID,
                    job_name,
                    e,
                )

        finished_jobs = [name for name, task in running_job_tasks.items() if task.done()]
        for name in finished_jobs:
            LOGGER.warning(
                "Worker %s: Cleaning up finished job '%s' detected in main loop (callback might have missed?).",
                BACKGROUND_JOB_WORKER_ID,
                name,
            )
            try:
                running_job_tasks[name].result()
            except Exception as task_exc:
                LOGGER.debug(
                    "Worker %s: Exception from fallback cleanup for job '%s': %s",
                    BACKGROUND_JOB_WORKER_ID,
                    name,
                    task_exc,
                )
            finally:
                running_job_tasks.pop(name, None)

        try:
            await asyncio.wait_for(exit_event.wait(), timeout=CYCLE_SLEEP_TIME)
            LOGGER.info("Worker %s: Exit event detected during sleep.", BACKGROUND_JOB_WORKER_ID)
            break
        except asyncio.TimeoutError:
            pass

    LOGGER.info("Worker %s: Background job cycle stopped.", BACKGROUND_JOB_WORKER_ID)
    if running_job_tasks:
        LOGGER.info(
            "Worker %s: Waiting for %d running job(s) to finish gracefully.",
            BACKGROUND_JOB_WORKER_ID,
            len(running_job_tasks),
        )
        await asyncio.gather(*running_job_tasks.values(), return_exceptions=True)
        LOGGER.info("Worker %s: All running jobs finished processing.", BACKGROUND_JOB_WORKER_ID)


def _make_done_callback(running_job_tasks, name):
    def _callback(fut: asyncio.Future):
        try:
            exc = fut.exception()
            if exc:
                LOGGER.error(
                    "Worker %s: Job '%s' task finished with exception: %s",
                    BACKGROUND_JOB_WORKER_ID,
                    name,
                    exc,
                    exc_info=exc,
                )
            else:
                LOGGER.debug(
                    "Worker %s: Job '%s' task finished successfully.",
                    BACKGROUND_JOB_WORKER_ID,
                    name,
                )
        except asyncio.CancelledError:
            LOGGER.info("Worker %s: Job '%s' task was cancelled.", BACKGROUND_JOB_WORKER_ID, name)
        finally:
            # Remove from local tracking ONLY when task is truly done
            finished_task = running_job_tasks.pop(name, None)
            if finished_task:
                LOGGER.debug(
                    "Worker %s: Removed job '%s' from local tracking via callback.",
                    BACKGROUND_JOB_WORKER_ID,
                    name,
                )
            else:
                LOGGER.warning(
                    "Worker %s: Done callback for job '%s' triggered, but task not found in local tracking.",
                    BACKGROUND_JOB_WORKER_ID,
                    name,
                )

    return _callback


async def release_job_lock(job_name: str):
    """Releases the lock. Will be called automatically after background job is finished."""
    async with database.SESSION() as session:
        stmt = (
            update(database.BackgroundJobLock)
            .where(
                database.BackgroundJobLock.job_name == job_name,
                database.BackgroundJobLock.worker_id == BACKGROUND_JOB_WORKER_ID,
            )
            .values(
                worker_id=None,
                expires_at=None,
                last_run_at=datetime.now(timezone.utc),
            )
        )
        try:
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Worker %s: Error releasing lock for job '%s': %s", BACKGROUND_JOB_WORKER_ID, job_name, e)


async def update_lock_heartbeat(exit_event: asyncio.Event, job_name: str, lock_ttl: timedelta):
    """Updates the expires_at timestamp for the held background task lock.

    Cancels background task if error or exit flag is raised.
    """

    updating_period = lock_ttl.seconds / 4
    while True:
        new_expires_at = datetime.now(timezone.utc) + lock_ttl
        async with database.SESSION() as session:
            try:
                stmt = (
                    update(database.BackgroundJobLock)
                    .where(
                        database.BackgroundJobLock.job_name == job_name,
                        database.BackgroundJobLock.worker_id == BACKGROUND_JOB_WORKER_ID,
                    )
                    .values(expires_at=new_expires_at)
                )
                result = await session.execute(stmt)
                await session.commit()
                if result.rowcount == 1:
                    LOGGER.debug(
                        "Worker %s: Renewed lock for job '%s' until %s.",
                        BACKGROUND_JOB_WORKER_ID,
                        job_name,
                        new_expires_at,
                    )
                else:
                    LOGGER.info(
                        "Worker %s: Failed to renew lock for job '%s'. "
                        "Lock may have expired or been taken. Stopping job.",
                        BACKGROUND_JOB_WORKER_ID,
                        job_name,
                    )
                    return
            except Exception as e:
                await session.rollback()
                LOGGER.exception(
                    "Worker %s: Unexpected error renewing lock for job '%s': %s. Stopping job.",
                    BACKGROUND_JOB_WORKER_ID,
                    job_name,
                    e,
                )
                return
        try:
            await asyncio.wait_for(exit_event.wait(), timeout=updating_period)
            return
        except asyncio.TimeoutError:
            pass


async def run_background_job(exit_event: asyncio.Event, job_def: BackgroundJobDefinition):
    """Runs the target background job and the update_lock_heartbeat task in parallel.

    If the heartbeat task fails (for example, cannot renew the lock), it will cancel
    the background job. Once the job is finished or canceled, the lock is released.
    """
    try:
        job_task = asyncio.create_task(job_def.func(exit_event))
        heartbeat_task = asyncio.create_task(
            update_lock_heartbeat(exit_event, job_def.job_name, job_def.lock_ttl),
        )
        done, pending = await asyncio.wait([job_task, heartbeat_task], return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if job_task in done and job_task.exception():
            LOGGER.exception(
                "Worker %s: Job '%s' raised an exception: %s",
                BACKGROUND_JOB_WORKER_ID,
                job_def.job_name,
                job_task.exception(),
            )
        else:
            LOGGER.info("Worker %s: Job '%s' completed.", BACKGROUND_JOB_WORKER_ID, job_def.job_name)
    except Exception as e:
        LOGGER.exception(
            "Worker %s: Error running job '%s': %s",
            BACKGROUND_JOB_WORKER_ID,
            job_def.job_name,
            e,
        )
    finally:
        await release_job_lock(job_def.job_name)


async def fetch_background_jobs_locks() -> list[BackgroundJobLockModel]:
    """Fetches all background job lock records from the database."""
    async with database.SESSION() as session:
        result = await session.execute(select(database.BackgroundJobLock))
        locks = result.scalars().all()
        return [BackgroundJobLockModel.model_validate(lock) for lock in locks]


async def try_insert_background_job_lock(job_name: str, lock_ttl: timedelta) -> bool:
    now = datetime.now(timezone.utc)
    async with database.SESSION() as session:
        new_lock = database.BackgroundJobLock(
            job_name=job_name,
            worker_id=BACKGROUND_JOB_WORKER_ID,
            expires_at=now + lock_ttl,
            last_run_at=now,
        )
        session.add(new_lock)
        try:
            await session.commit()
            LOGGER.info("Worker %s: Acquired lock for job '%s' by insertion.", BACKGROUND_JOB_WORKER_ID, job_name)
            return True
        except IntegrityError:
            LOGGER.debug(
                "Worker %s: Lock already exists for job '%s', cannot insert.", BACKGROUND_JOB_WORKER_ID, job_name
            )
            return False
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Worker %s: Failed to insert lock for job '%s': %s", BACKGROUND_JOB_WORKER_ID, job_name, e)
            return False


async def try_update_background_job_lock(job_name: str, lock_ttl: timedelta) -> bool:
    now = datetime.now(timezone.utc)
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.BackgroundJobLock)
                .where(
                    database.BackgroundJobLock.job_name == job_name,
                    or_(
                        database.BackgroundJobLock.worker_id == null(),
                        database.BackgroundJobLock.expires_at == null(),
                        database.BackgroundJobLock.expires_at < now,
                    ),
                )
                .values(
                    worker_id=BACKGROUND_JOB_WORKER_ID,
                    expires_at=now + lock_ttl,
                    last_run_at=now,
                )
            )
            result = await session.execute(stmt)
            if result.rowcount > 0:
                await session.commit()
                LOGGER.info("Worker %s: Acquired lock for job '%s' by update.", BACKGROUND_JOB_WORKER_ID, job_name)
                return True
            LOGGER.debug(
                "Worker %s: Failed to update lock for job '%s'; it may be held by another worker.",
                BACKGROUND_JOB_WORKER_ID,
                job_name,
            )
            return False
        except Exception as e:
            await session.rollback()
            LOGGER.exception(
                "Worker %s: Exception when trying to update lock for job '%s': %s",
                BACKGROUND_JOB_WORKER_ID,
                job_name,
                e,
            )
            return False
