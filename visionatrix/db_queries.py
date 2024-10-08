import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select, update

from . import database
from .pydantic_models import FlowProgressInstall, WorkerDetails

LOGGER = logging.getLogger("visionatrix")


def __get_worker_query(user_id: str | None, worker_id: str):
    query = select(database.Worker).filter(database.Worker.worker_id == worker_id)
    if user_id is not None:
        query = query.filter(database.Worker.user_id == user_id)
    return query


def __get_workers_query(user_id: str | None, last_seen_interval: int, worker_id: str):
    query = select(database.Worker)
    if user_id is not None:
        query = query.filter(database.Worker.user_id == user_id)
    if last_seen_interval > 0:
        time_threshold = datetime.now(timezone.utc) - timedelta(seconds=last_seen_interval)
        query = query.filter(database.Worker.last_seen >= time_threshold)
    if worker_id:
        query = query.filter(database.Worker.worker_id == worker_id)
    return query


def get_setting(user_id: str, key: str, admin: bool) -> str:
    if value := get_user_setting(user_id, key):
        return value
    return get_global_setting(key, admin)


def get_global_setting(key: str, admin: bool) -> str:
    session = database.SESSION()
    try:
        query = select(database.GlobalSettings.value, database.GlobalSettings.sensitive).where(
            database.GlobalSettings.name == key
        )
        result = session.execute(query).one_or_none()
        if result is None:
            return ""
        value, sensitive = result
        if sensitive and not admin:
            return ""
        return value
    except Exception:
        LOGGER.exception("Failed to retrieve global setting for `%s`", key)
        raise
    finally:
        session.close()


def get_user_setting(user_id: str, key: str) -> str:
    session = database.SESSION()
    try:
        query = select(database.UserSettings.value).where(
            database.UserSettings.user_id == user_id, database.UserSettings.name == key
        )
        result = session.execute(query).scalar_one_or_none()
        return result if result is not None else ""
    except Exception:
        LOGGER.error("Failed to retrieve user setting for `%s`: `%s`", user_id, key)
        raise
    finally:
        session.close()


def set_global_setting(key: str, value: str, sensitive: bool) -> None:
    session = database.SESSION()
    try:
        if value:
            stmt = (
                update(database.GlobalSettings)
                .where(database.GlobalSettings.name == key)
                .values(value=value, sensitive=sensitive)
            )
            result = session.execute(stmt)
            if result.rowcount == 0:
                session.add(database.GlobalSettings(name=key, value=value, sensitive=sensitive))
            session.commit()
        else:
            result = session.execute(delete(database.GlobalSettings).where(database.GlobalSettings.name == key))
            if result.rowcount:
                session.commit()
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to set global setting for `%s`", key)
        raise
    finally:
        session.close()


def set_user_setting(user_id: str, key: str, value: str) -> None:
    session = database.SESSION()
    try:
        if value:
            stmt = (
                update(database.UserSettings)
                .where(database.UserSettings.user_id == user_id, database.UserSettings.name == key)
                .values(value=value)
            )
            result = session.execute(stmt)
            if result.rowcount == 0:
                session.add(database.UserSettings(user_id=user_id, name=key, value=value))
            session.commit()
        else:
            result = session.execute(
                delete(database.UserSettings).where(
                    database.UserSettings.user_id == user_id, database.UserSettings.name == key
                )
            )
            if result.rowcount:
                session.commit()
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to set user setting for `%s`: `%s`", user_id, key)
        raise
    finally:
        session.close()


def get_all_settings(user_id: str, admin: bool) -> dict[str, str]:
    """Retrieve all settings with user settings having higher priority over global settings."""
    user_settings = get_user_settings(user_id)
    global_settings = get_all_global_settings(admin)

    # Merge user settings with global settings, giving priority to user settings
    return {**global_settings, **user_settings}


def get_all_global_settings(admin: bool) -> dict[str, str]:
    """Retrieve all global settings as a dictionary."""
    session = database.SESSION()
    try:
        query = select(database.GlobalSettings.name, database.GlobalSettings.value, database.GlobalSettings.sensitive)
        results = session.execute(query).all()
        return {name: value for name, value, sensitive in results if not sensitive or (sensitive and admin)}
    except Exception:
        LOGGER.exception("Failed to retrieve all global settings")
        raise
    finally:
        session.close()


def get_user_settings(user_id: str) -> dict[str, str]:
    """Retrieve all settings for a specific user as a dictionary."""
    session = database.SESSION()
    try:
        query = select(database.UserSettings.name, database.UserSettings.value).where(
            database.UserSettings.user_id == user_id
        )
        results = session.execute(query).all()
        return {name: value for name, value in results}  # noqa pylint: disable=unnecessary-comprehension
    except Exception:
        LOGGER.exception("Failed to retrieve all user settings for user `%s`", user_id)
        raise
    finally:
        session.close()


def get_workers_details(user_id: str | None, last_seen_interval: int, worker_id: str) -> list[WorkerDetails]:
    with database.SESSION() as session:
        try:
            query = __get_workers_query(user_id, last_seen_interval, worker_id)
            results = session.execute(query).scalars().all()
            return [WorkerDetails.model_validate(i) for i in results]
        except Exception:
            LOGGER.exception("Failed to retrieve workers: `%s`, %s, %s", user_id, last_seen_interval, worker_id)
            raise


def get_worker_details(user_id: str | None, worker_id: str) -> WorkerDetails | None:
    with database.SESSION() as session:
        try:
            query = __get_worker_query(user_id, worker_id)
            result = session.execute(query).scalar()
            return None if result is None else WorkerDetails.model_validate(result)
        except Exception:
            LOGGER.exception("Failed to retrieve worker: `%s`, %s", user_id, worker_id)
            raise


def set_worker_tasks_to_give(user_id: str | None, worker_id: str, tasks_to_give: list[str]) -> bool:
    with database.SESSION() as session:
        try:
            query = update(database.Worker).where(database.Worker.worker_id == worker_id)
            if user_id is not None:
                query = query.where(database.Worker.user_id == user_id)
            result = session.execute(query.values(tasks_to_give=tasks_to_give))
            session.commit()
            return result.rowcount > 0
        except Exception as e:
            session.rollback()
            LOGGER.exception("Failed to update tasks for worker(`%s`, `%s`): %s", user_id, worker_id, e)
            return False


def get_flows_progress_install() -> list[FlowProgressInstall]:
    session = database.SESSION()
    try:
        query = select(database.FlowsInstallStatus)
        results = session.execute(query).scalars().all()
        return [FlowProgressInstall.model_validate(i) for i in results]
    except Exception:
        LOGGER.exception("Failed to retrieve flow installation progress.")
        raise
    finally:
        session.close()


def delete_flows_progress_install(name: str) -> bool:
    session = database.SESSION()
    try:
        stmt = delete(database.FlowsInstallStatus).where(database.FlowsInstallStatus.name == name)
        result = session.execute(stmt)
        session.commit()
        return result.rowcount > 0
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to delete flow installation progress for `%s`", name)
        raise
    finally:
        session.close()


def add_flow_progress_install(name: str, flow_comfy: dict) -> None:
    session = database.SESSION()
    try:
        new_flow = database.FlowsInstallStatus(name=name, flow_comfy=flow_comfy)
        session.add(new_flow)
        session.commit()
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to add flow installation progress for `%s`", name)
        raise
    finally:
        session.close()


def update_flow_progress_install(name: str, progress: float, relative_progress: bool) -> bool:
    session = database.SESSION()
    try:
        # Ensure we only update if there is no error already set
        if relative_progress:
            stmt = (
                update(database.FlowsInstallStatus)
                .where(database.FlowsInstallStatus.name == name)
                .where(database.FlowsInstallStatus.error == "")
                .values(
                    progress=database.FlowsInstallStatus.progress + progress,  # Increment progress
                    updated_at=datetime.now(timezone.utc),
                )
            )
        else:
            stmt = (
                update(database.FlowsInstallStatus)
                .where(database.FlowsInstallStatus.name == name)
                .where(database.FlowsInstallStatus.error == "")
                .values(
                    progress=progress,
                    updated_at=datetime.now(timezone.utc),
                )
            )
        result = session.execute(stmt)
        session.commit()

        # If no rows were updated, this means an error was already set
        if result.rowcount == 0:
            LOGGER.warning(
                "Flow installation for `%s` already encountered an error, skipping progress update: %s%s",
                name,
                "+" if relative_progress else "",
                progress,
            )
            return False
        return True
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to update flow installation progress for `%s`", name)
        raise
    finally:
        session.close()


def set_flow_progress_install_error(name: str, error: str) -> bool:
    session = database.SESSION()
    try:
        # Ensure we only update if there is no error already set
        stmt = (
            update(database.FlowsInstallStatus)
            .where(database.FlowsInstallStatus.name == name)
            .where(database.FlowsInstallStatus.error == "")
            .values(
                error=error,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = session.execute(stmt)
        session.commit()

        # If no rows were updated, this means an error was already set
        if result.rowcount == 0:
            LOGGER.warning(
                "Flow installation for `%s` already encountered an error, skipping setting error: %s",
                name,
                error,
            )
            return False
        return True
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to update flow installation progress for `%s`", name)
        raise
    finally:
        session.close()


def finish_flow_progress_install(name: str) -> bool:
    session = database.SESSION()
    try:
        # Ensure we only update if there is no error already set
        stmt = (
            update(database.FlowsInstallStatus)
            .where(database.FlowsInstallStatus.name == name)
            .where(database.FlowsInstallStatus.error == "")
            .values(
                progress=100.0,
                finished_at=datetime.now(timezone.utc),
            )
        )
        result = session.execute(stmt)
        session.commit()
        # If no rows were updated, this means an error was already set
        if result.rowcount == 0:
            LOGGER.warning(
                "Flow installation for `%s` already encountered an error, skipping finalizing install.",
                name,
            )
            return False
        return True
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to update flow installation progress for `%s`", name)
        raise
    finally:
        session.close()


def flows_installation_in_progress() -> list[str]:
    session = database.SESSION()
    try:
        time_threshold = datetime.now(timezone.utc) - timedelta(minutes=3)
        query = select(database.FlowsInstallStatus.name).where(
            database.FlowsInstallStatus.finished_at.is_(None), database.FlowsInstallStatus.updated_at >= time_threshold
        )
        return session.execute(query).scalars().all()
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to check if any flow installation is in progress")
        raise
    finally:
        session.close()
