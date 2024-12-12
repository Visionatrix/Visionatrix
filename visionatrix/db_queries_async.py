import logging

from sqlalchemy import delete, select, update

from . import database
from .db_queries import __get_worker_query, __get_workers_query
from .pydantic_models import FlowProgressInstall, ModelProgressInstall, WorkerDetails

LOGGER = logging.getLogger("visionatrix")


async def get_setting_async(user_id: str, key: str, admin: bool) -> str:
    if value := await get_user_setting_async(user_id, key):
        return value
    return await get_global_setting_async(key, admin)


async def get_global_setting_async(key: str, admin: bool) -> str:
    async with database.SESSION_ASYNC() as session:
        try:
            query = select(database.GlobalSettings.value, database.GlobalSettings.sensitive).where(
                database.GlobalSettings.name == key
            )
            result = (await session.execute(query)).one_or_none()
            if result is None:
                return ""
            value, sensitive = result
            if sensitive and not admin:
                return ""
            return value
        except Exception:
            LOGGER.exception("Failed to retrieve global setting for `%s`", key)
            raise


async def get_user_setting_async(user_id: str, key: str) -> str:
    async with database.SESSION_ASYNC() as session:
        try:
            query = select(database.UserSettings.value).where(
                database.UserSettings.user_id == user_id, database.UserSettings.name == key
            )
            result = (await session.execute(query)).scalar_one_or_none()
            return result if result is not None else ""
        except Exception:
            LOGGER.exception("Failed to retrieve user setting for `%s`: `%s`", user_id, key)
            raise


async def set_global_setting_async(key: str, value: str, sensitive: bool) -> None:
    async with database.SESSION_ASYNC() as session:
        try:
            if value:
                stmt = (
                    update(database.GlobalSettings)
                    .where(database.GlobalSettings.name == key)
                    .values(value=value, sensitive=sensitive)
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    session.add(database.GlobalSettings(name=key, value=value, sensitive=sensitive))
                await session.commit()
            else:
                result = await session.execute(
                    delete(database.GlobalSettings).where(database.GlobalSettings.name == key)
                )
                if result.rowcount:
                    await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to set global setting for `%s`", key)
            raise


async def set_user_setting_async(user_id: str, key: str, value: str) -> None:
    async with database.SESSION_ASYNC() as session:
        try:
            if value:
                stmt = (
                    update(database.UserSettings)
                    .where(database.UserSettings.user_id == user_id, database.UserSettings.name == key)
                    .values(value=value)
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    session.add(database.UserSettings(user_id=user_id, name=key, value=value))
                await session.commit()
            else:
                result = await session.execute(
                    delete(database.UserSettings).where(
                        database.UserSettings.user_id == user_id, database.UserSettings.name == key
                    )
                )
                if result.rowcount:
                    await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to set user setting for `%s`: `%s`", user_id, key)
            raise


async def get_all_settings_async(user_id: str, admin: bool) -> dict[str, str]:
    """Retrieve all settings with user settings having higher priority over global settings."""
    user_settings = await get_user_settings_async(user_id)
    global_settings = await get_all_global_settings_async(admin)

    # Merge user settings with global settings, giving priority to user settings
    return {**global_settings, **user_settings}


async def get_all_global_settings_async(admin: bool) -> dict[str, str]:
    """Retrieve all global settings as a dictionary."""
    async with database.SESSION_ASYNC() as session:
        try:
            query = select(
                database.GlobalSettings.name, database.GlobalSettings.value, database.GlobalSettings.sensitive
            )
            results = (await session.execute(query)).all()
            return {name: value for name, value, sensitive in results if not sensitive or (sensitive and admin)}
        except Exception:
            LOGGER.exception("Failed to retrieve all global settings")
            raise


async def get_user_settings_async(user_id: str) -> dict[str, str]:
    """Retrieve all settings for a specific user as a dictionary."""
    async with database.SESSION_ASYNC() as session:
        try:
            query = select(database.UserSettings.name, database.UserSettings.value).where(
                database.UserSettings.user_id == user_id
            )
            results = (await session.execute(query)).all()
            return {name: value for name, value in results}  # noqa pylint: disable=unnecessary-comprehension
        except Exception:
            LOGGER.exception("Failed to retrieve all user settings for user `%s`", user_id)
            raise


async def get_workers_details_async(
    user_id: str | None, last_seen_interval: int, worker_id: str
) -> list[WorkerDetails]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_workers_query(user_id, last_seen_interval, worker_id)
            results = (await session.execute(query)).scalars().all()
            return [WorkerDetails.model_validate(i) for i in results]
        except Exception:
            LOGGER.exception("Failed to retrieve workers: `%s`, %s, %s", user_id, last_seen_interval, worker_id)
            raise


async def get_worker_details_async(user_id: str | None, worker_id: str) -> WorkerDetails | None:
    async with database.SESSION_ASYNC() as session:
        try:
            query = __get_worker_query(user_id, worker_id)
            result = (await session.execute(query)).scalar()
            return None if result is None else WorkerDetails.model_validate(result)
        except Exception:
            LOGGER.exception("Failed to retrieve worker: `%s`, %s", user_id, worker_id)
            raise


async def set_worker_tasks_to_give_async(user_id: str | None, worker_id: str, tasks_to_give: list[str]) -> bool:
    async with database.SESSION_ASYNC() as session:
        try:
            query = update(database.Worker).where(database.Worker.worker_id == worker_id)
            if user_id is not None:
                query = query.where(database.Worker.user_id == user_id)
            result = session.execute(query.values(tasks_to_give=tasks_to_give))
            await session.commit()
            return result.rowcount > 0
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to update tasks for worker(`%s`, `%s`): %s", user_id, worker_id, e)
            return False


async def get_flows_progress_install_async() -> list[FlowProgressInstall]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = select(database.FlowsInstallStatus)
            results = (await session.execute(query)).scalars().all()
            return [FlowProgressInstall.model_validate(i) for i in results]
        except Exception:
            LOGGER.exception("Failed to retrieve flow installation progress.")
            raise


async def delete_flow_progress_install_async(name: str) -> bool:
    async with database.SESSION_ASYNC() as session:
        try:
            stmt = delete(database.FlowsInstallStatus).where(database.FlowsInstallStatus.name == name)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to delete flow installation progress for `%s`", name)
            raise


async def get_installed_models_async() -> dict[str, ModelProgressInstall]:
    async with database.SESSION_ASYNC() as session:
        try:
            query = select(database.ModelsInstallStatus).where(database.ModelsInstallStatus.progress >= 100.0)
            results = (await session.execute(query)).scalars().all()
            return {model.name: ModelProgressInstall.model_validate(model) for model in results}
        except Exception as e:
            LOGGER.exception("Failed to retrieve installed models.")
            raise e
