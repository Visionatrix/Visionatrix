import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, false, or_, select, true, update
from sqlalchemy.exc import IntegrityError

from . import database
from .pydantic_models import (
    FederatedInstance,
    FederatedInstanceCreate,
    FederatedInstanceUpdate,
    FlowProgressInstall,
    ModelProgressInstall,
    WorkerDetails,
    WorkerSettingsRequest,
)

LOGGER = logging.getLogger("visionatrix")


def __get_worker_query(user_id: str | None, worker_id: str):
    query = select(database.Worker).filter(database.Worker.worker_id == worker_id)
    if user_id is not None:
        query = query.filter(database.Worker.user_id == user_id)
    return query


def __get_workers_query(user_id: str | None, last_seen_interval: int, worker_id: str, include_federated: bool):
    query = select(database.Worker)
    if user_id is not None:
        query = query.filter(database.Worker.user_id == user_id)
    if last_seen_interval > 0:
        time_threshold = datetime.now(timezone.utc) - timedelta(seconds=last_seen_interval)
        query = query.filter(database.Worker.last_seen >= time_threshold)
    if worker_id:
        query = query.filter(database.Worker.worker_id == worker_id)
    if include_federated is False:
        query = query.filter(database.Worker.federated_instance_name == "")
    return query


async def get_setting(user_id: str, key: str, admin: bool) -> str:
    if value := await get_user_setting(user_id, key):
        return value
    return await get_global_setting(key, admin)


async def get_global_setting(key: str, admin: bool, crc32: int | None = None) -> str:
    async with database.SESSION() as session:
        try:
            query = select(database.GlobalSettings.value, database.GlobalSettings.sensitive).where(
                database.GlobalSettings.name == key
            )
            if crc32 is not None:
                query = query.where(database.GlobalSettings.crc32 != crc32)
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


async def get_user_setting(user_id: str, key: str) -> str:
    async with database.SESSION() as session:
        try:
            query = select(database.UserSettings.value).where(
                database.UserSettings.user_id == user_id, database.UserSettings.name == key
            )
            result = (await session.execute(query)).scalar_one_or_none()
            return result if result is not None else ""
        except Exception:
            LOGGER.exception("Failed to retrieve user setting for `%s`: `%s`", user_id, key)
            raise


async def get_system_setting(key: str) -> str:
    async with database.SESSION() as session:
        try:
            query = select(database.SystemSettings.value).where(database.SystemSettings.name == key)
            result = (await session.execute(query)).scalar_one_or_none()
            return result if result is not None else ""
        except Exception:
            LOGGER.exception("Failed to retrieve system setting for `%s`", key)
            raise


async def set_global_setting(key: str, value: str, sensitive: bool) -> None:
    async with database.SESSION() as session:
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


async def set_user_setting(user_id: str, key: str, value: str) -> None:
    async with database.SESSION() as session:
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


async def set_system_setting(key: str, value: str) -> None:
    async with database.SESSION() as session:
        try:
            if value:
                stmt = update(database.SystemSettings).where(database.SystemSettings.name == key).values(value=value)
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    session.add(database.SystemSettings(name=key, value=value))
                await session.commit()
            else:
                result = await session.execute(
                    delete(database.SystemSettings).where(database.SystemSettings.name == key)
                )
                if result.rowcount:
                    await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to set system setting for `%s`", key)
            raise


async def get_all_settings(user_id: str, admin: bool) -> dict[str, str]:
    """Retrieve all settings with user settings having higher priority over global settings."""
    user_settings = await get_user_settings(user_id)
    global_settings = await get_all_global_settings(admin)

    # Merge user settings with global settings, giving priority to user settings
    return {**global_settings, **user_settings}


async def get_all_global_settings(admin: bool) -> dict[str, str]:
    """Retrieve all global settings as a dictionary."""
    async with database.SESSION() as session:
        try:
            query = select(
                database.GlobalSettings.name, database.GlobalSettings.value, database.GlobalSettings.sensitive
            )
            results = (await session.execute(query)).all()
            return {name: value for name, value, sensitive in results if not sensitive or (sensitive and admin)}
        except Exception:
            LOGGER.exception("Failed to retrieve all global settings")
            raise


async def get_user_settings(user_id: str) -> dict[str, str]:
    """Retrieve all settings for a specific user as a dictionary."""
    async with database.SESSION() as session:
        try:
            query = select(database.UserSettings.name, database.UserSettings.value).where(
                database.UserSettings.user_id == user_id
            )
            results = (await session.execute(query)).all()
            return {name: value for name, value in results}  # noqa pylint: disable=unnecessary-comprehension
        except Exception:
            LOGGER.exception("Failed to retrieve all user settings for user `%s`", user_id)
            raise


async def get_all_system_settings() -> dict[str, str]:
    async with database.SESSION() as session:
        try:
            query = select(database.SystemSettings.name, database.SystemSettings.value)
            results = (await session.execute(query)).all()
            return {name: value for name, value in results}  # noqa pylint: disable=unnecessary-comprehension
        except Exception:
            LOGGER.exception("Failed to retrieve all system settings")
            raise


async def get_all_global_settings_for_task_execution() -> dict[str, bool | int | str | float]:
    """Retrieve all global settings related to task execution to init the ExtraFlags model."""
    async with database.SESSION() as session:
        try:
            query = select(database.GlobalSettings.name, database.GlobalSettings.value).where(
                database.GlobalSettings.name.in_(
                    ("save_metadata", "smart_memory", "cache_type", "cache_size", "vae_cpu", "reserve_vram")
                )
            )
            results = (await session.execute(query)).all()
            settings = {name: value or "" for name, value in results}

            save_metadata = settings.get("save_metadata", "") not in ("", "0")
            smart_memory = settings.get("smart_memory", "") != "0"

            cache_type = settings.get("cache_type") or "classic"
            cache_size_raw = settings.get("cache_size", "")
            try:
                cache_size = int(cache_size_raw) if cache_size_raw not in ("", None) else 1
            except ValueError:
                LOGGER.warning("Invalid cache_size '%s' in GlobalSettings, defaulting to 1", cache_size_raw)
                cache_size = 1

            vae_cpu = settings.get("vae_cpu", "") not in ("", "0")

            reserve_vram_raw = float(settings.get("reserve_vram", "0.6"))
            try:
                reserve_vram = float(reserve_vram_raw)
            except ValueError:
                LOGGER.warning("Invalid reserve_vram '%s' in GlobalSettings, defaulting to 0.6 GB", reserve_vram_raw)
                reserve_vram = 0.6

            return {
                "save_metadata": save_metadata,
                "smart_memory": smart_memory,
                "cache_type": cache_type,
                "cache_size": cache_size,
                "vae_cpu": vae_cpu,
                "reserve_vram": reserve_vram,
            }
        except Exception:
            LOGGER.exception("Failed to retrieve all global task execution settings")
            raise


async def get_flow_progress_install(name: str) -> FlowProgressInstall | None:
    async with database.SESSION() as session:
        try:
            query = select(database.FlowsInstallStatus).where(database.FlowsInstallStatus.name == name)
            flow_status = (await session.execute(query)).scalar_one_or_none()
            if not flow_status:
                return None
            computed_progress = await _compute_flow_progress(flow_status, session)
            return FlowProgressInstall.from_orm_with_progress(flow_status, computed_progress)
        except Exception:
            LOGGER.exception("Failed to retrieve flow progress install for name `%s`.", name)
            raise


async def get_flows_progress_install() -> list[FlowProgressInstall]:
    async with database.SESSION() as session:
        try:
            query = select(database.FlowsInstallStatus)
            flows = (await session.execute(query)).scalars().all()
            result_list = []
            for flow_status in flows:
                computed_progress = await _compute_flow_progress(flow_status, session)
                result_list.append(FlowProgressInstall.from_orm_with_progress(flow_status, computed_progress))
            return result_list
        except Exception:
            LOGGER.exception("Failed to retrieve flow installation progress.")
            raise


async def delete_flow_progress_install(name: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = delete(database.FlowsInstallStatus).where(database.FlowsInstallStatus.name == name)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to delete flow installation progress for `%s`", name)
            raise


async def delete_flows_progress_install() -> None:
    async with database.SESSION() as session:
        try:
            stmt = delete(database.FlowsInstallStatus)
            await session.execute(stmt)
            await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to delete all flows progress install records.")
            raise


async def add_flow_progress_install(name: str, flow_comfy: dict, models: list[str]) -> None:
    async with database.SESSION() as session:
        try:
            new_flow = database.FlowsInstallStatus(name=name, flow_comfy=flow_comfy, models=models)
            session.add(new_flow)
            await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to add flow installation progress for `%s`", name)
            raise


async def edit_flow_progress_install(name: str, flow_comfy: dict) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.FlowsInstallStatus)
                .where(database.FlowsInstallStatus.name == name)
                .values(flow_comfy=flow_comfy, updated_at=datetime.now(timezone.utc))
            )
            result = await session.execute(stmt)
            await session.commit()
            return bool(result.rowcount == 1)
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to edit flow progress install for `%s`.", name)
            raise


async def mark_flow_as_installed(name: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.FlowsInstallStatus)
                .where(database.FlowsInstallStatus.name == name)
                .values(installed=True, updated_at=datetime.now(timezone.utc))
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                LOGGER.warning("Flow installation for `%s` not found or already installed.", name)
                return False
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to mark flow `%s` as installed.", name)
            raise


async def update_flow_updated_at(name: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.FlowsInstallStatus)
                .where(
                    database.FlowsInstallStatus.name == name,
                    database.FlowsInstallStatus.error == "",
                )
                .values(updated_at=datetime.now(timezone.utc))
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                LOGGER.warning("Error updating flow installation 'updated_at' for `%s`.", name)
                return False
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to update 'updated_at' for flow `%s`.", name)
            raise


async def set_flow_progress_install_error(name: str, error: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.FlowsInstallStatus)
                .where(
                    database.FlowsInstallStatus.name == name,
                    database.FlowsInstallStatus.error == "",
                )
                .values(
                    error=error,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                LOGGER.warning(
                    "Flow installation for `%s` already encountered an error, skipping setting error: %s",
                    name,
                    error,
                )
                return False
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to update flow installation progress for `%s`", name)
            raise


async def flows_installation_in_progress(name: str | None = None) -> dict[str, FlowProgressInstall]:
    async with database.SESSION() as session:
        try:
            time_threshold = datetime.now(timezone.utc) - timedelta(minutes=5)
            query = select(database.FlowsInstallStatus).where(
                database.FlowsInstallStatus.installed == false(),
                database.FlowsInstallStatus.updated_at >= time_threshold,
                database.FlowsInstallStatus.error == "",
            )
            if name:
                query = query.where(database.FlowsInstallStatus.name == name)
            results = (await session.execute(query)).scalars().all()
            flows_dict = {}
            for flow in results:
                computed_progress = await _compute_flow_progress(flow, session)
                flows_dict[flow.name] = FlowProgressInstall.from_orm_with_progress(flow, computed_progress)
            return flows_dict
        except Exception:
            LOGGER.exception("Failed to check if any flow installation is in progress")
            raise


async def get_installed_flows() -> list[FlowProgressInstall]:
    async with database.SESSION() as session:
        try:
            query = select(database.FlowsInstallStatus).where(database.FlowsInstallStatus.installed == true())
            results = (await session.execute(query)).scalars().all()
            return [FlowProgressInstall.from_orm_with_progress(flow, 100.0) for flow in results]
        except Exception as e:
            LOGGER.exception("Failed to retrieve installed flows.")
            raise e


async def delete_old_model_progress_install(name: str) -> bool:
    async with database.SESSION() as session:
        try:
            time_threshold = datetime.now(timezone.utc) - timedelta(minutes=3)
            stmt = (
                delete(database.ModelsInstallStatus)
                .where(database.ModelsInstallStatus.name == name)
                .where(
                    or_(
                        database.ModelsInstallStatus.error != "",
                        database.ModelsInstallStatus.updated_at < time_threshold,
                    )
                )
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount != 0
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to delete installation progress for model `%s`.", name)
            raise


async def delete_model_by_time_and_filename(mtime: float, file_name: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                delete(database.ModelsInstallStatus)
                .where(database.ModelsInstallStatus.file_mtime == mtime)
                .where(database.ModelsInstallStatus.filename.like(f"%{file_name}"))
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to delete model by mtime `%s` and filename `%s`", mtime, file_name)
            raise


async def add_model_progress_install(name: str, flow_name: str, filename: str | None = None) -> datetime | None:
    async with database.SESSION() as session:
        try:
            new_updated_at = datetime.now(timezone.utc)
            new_model = database.ModelsInstallStatus(
                name=name,
                flow_name=flow_name,
                progress=0.0,
                started_at=datetime.now(timezone.utc),
                updated_at=new_updated_at,
                filename=filename,
            )
            session.add(new_model)
            await session.commit()
            return new_updated_at
        except IntegrityError:
            await session.rollback()
            LOGGER.info("Model installation progress for `%s` already exists.", name)
            return None
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to add model installation progress for `%s` under flow `%s`.", name, flow_name)
            raise


async def update_model_progress_install(name: str, flow_name: str, progress: float, not_critical=False) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.ModelsInstallStatus)
                .where(
                    database.ModelsInstallStatus.name == name,
                    database.ModelsInstallStatus.error == "",
                    database.ModelsInstallStatus.flow_name == flow_name,
                )
                .values(progress=progress, updated_at=datetime.now(timezone.utc))
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                LOGGER.log(
                    logging.INFO if not_critical else logging.ERROR,
                    "Model installation progress not updated for `%s`. It doesn't exist or already has an error.",
                    name,
                )
                return False
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to update installation progress for model `%s`.", name)
            raise


async def complete_model_progress_install(name: str, flow_name: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.ModelsInstallStatus)
                .where(database.ModelsInstallStatus.name == name)
                .values(
                    flow_name=flow_name,
                    progress=100.0,
                    error="",
                    file_mtime=None,
                    filename="",
                    updated_at=datetime.now(timezone.utc),
                )
            )
            result = await session.execute(stmt)

            if result.rowcount == 0:
                now_time = datetime.now(timezone.utc)
                new_model = database.ModelsInstallStatus(
                    name=name,
                    flow_name=flow_name,
                    progress=100.0,
                    error="",
                    started_at=now_time,
                    updated_at=now_time,
                )
                session.add(new_model)

            await session.commit()
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to finalize model installation progress for `%s` under flow `%s`", name, flow_name)
            raise


async def set_model_progress_install_error(name: str, flow_name: str, error: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.ModelsInstallStatus)
                .where(
                    database.ModelsInstallStatus.name == name,
                    database.ModelsInstallStatus.error == "",
                    database.ModelsInstallStatus.flow_name == flow_name,
                )
                .values(error=error)
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                LOGGER.warning(
                    "Models installation for `%s` already encountered an error, skipping setting error: %s",
                    name,
                    error,
                )
                return False
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to update model installation progress for `%s`", name)
            raise


async def reset_model_progress_install_error(name: str, flow_name: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.ModelsInstallStatus)
                .where(
                    database.ModelsInstallStatus.name == name,
                    database.ModelsInstallStatus.error != "",
                    database.ModelsInstallStatus.flow_name == flow_name,
                )
                .values(error="")
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                LOGGER.info("Failed to reset model installation error for `%s`", name)
                return False
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to reset model installation error for `%s`", name)
            raise


async def update_model_mtime(
    name: str, new_mtime: float, flow_name: str | None = None, new_filename: str | None = None
) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = update(database.ModelsInstallStatus).where(database.ModelsInstallStatus.name == name)
            if flow_name:
                stmt = stmt.where(database.ModelsInstallStatus.flow_name == flow_name)
            stmt = (
                stmt.values(file_mtime=new_mtime, filename=new_filename)
                if new_filename
                else stmt.values(file_mtime=new_mtime)
            )
            result = await session.execute(stmt)
            await session.commit()
            if result.rowcount == 0:
                LOGGER.warning("Model `%s` not found or no updates were made for mtime.", name)
                return False
            return True
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to update file mtime for model `%s`", name)
            raise


async def models_installation_in_progress(name: str | None = None) -> dict[str, ModelProgressInstall]:
    async with database.SESSION() as session:
        try:
            time_threshold = datetime.now(timezone.utc) - timedelta(minutes=3)
            query = select(database.ModelsInstallStatus).where(
                database.ModelsInstallStatus.progress < 100.0,
                database.ModelsInstallStatus.updated_at >= time_threshold,
                database.ModelsInstallStatus.error == "",
            )
            if name:
                query = query.where(database.ModelsInstallStatus.name == name)
            results = (await session.execute(query)).scalars().all()
            return {model.name: ModelProgressInstall.model_validate(model) for model in results}
        except Exception:
            LOGGER.exception("Failed to check if any model installation is in progress")
            raise


async def get_installed_models() -> dict[str, ModelProgressInstall]:
    async with database.SESSION() as session:
        try:
            query = select(database.ModelsInstallStatus).where(database.ModelsInstallStatus.progress >= 100.0)
            results = (await session.execute(query)).scalars().all()
            return {model.name: ModelProgressInstall.model_validate(model) for model in results}
        except Exception as e:
            LOGGER.exception("Failed to retrieve installed models.")
            raise e


async def get_workers_details(
    user_id: str | None, last_seen_interval: int, worker_id: str, include_federated=False
) -> list[WorkerDetails]:
    async with database.SESSION() as session:
        try:
            query = __get_workers_query(user_id, last_seen_interval, worker_id, include_federated)
            results = (await session.execute(query)).scalars().all()
            return [WorkerDetails.model_validate(i) for i in results]
        except Exception:
            LOGGER.exception("Failed to retrieve workers: `%s`, %s, %s", user_id, last_seen_interval, worker_id)
            raise


async def get_free_federated_workers(last_seen_interval: int, instance_name: list[str]) -> list[WorkerDetails]:
    async with database.SESSION() as session:
        try:
            query = select(database.Worker)
            time_threshold = datetime.now(timezone.utc) - timedelta(seconds=last_seen_interval)
            query = query.filter(database.Worker.last_seen >= time_threshold)
            query = query.filter(database.Worker.federated_instance_name.in_(instance_name))
            query = query.filter(database.Worker.empty_task_requests_count > 1)
            results = (await session.execute(query)).scalars().all()
            return [WorkerDetails.model_validate(i) for i in results]
        except Exception as e:
            LOGGER.exception("Failed to retrieve federated workers: %s", e)
            return []


async def get_worker_details(user_id: str | None, worker_id: str) -> WorkerDetails | None:
    async with database.SESSION() as session:
        try:
            query = __get_worker_query(user_id, worker_id)
            result = (await session.execute(query)).scalar()
            return None if result is None else WorkerDetails.model_validate(result)
        except Exception:
            LOGGER.exception("Failed to retrieve worker: `%s`, %s", user_id, worker_id)
            raise


async def save_worker_settings(user_id: str | None, data: WorkerSettingsRequest) -> bool:
    async with database.SESSION() as session:
        try:
            query = update(database.Worker).where(database.Worker.worker_id == data.worker_id)
            if user_id is not None:
                query = query.where(database.Worker.user_id == user_id)
            if data.tasks_to_give is None:
                query_values = query.values(
                    smart_memory=data.smart_memory,
                    cache_type=data.cache_type,
                    cache_size=data.cache_size,
                    vae_cpu=data.vae_cpu,
                    reserve_vram=data.reserve_vram,
                )
            else:
                query_values = query.values(
                    tasks_to_give=data.tasks_to_give,
                    smart_memory=data.smart_memory,
                    cache_type=data.cache_type,
                    cache_size=data.cache_size,
                    vae_cpu=data.vae_cpu,
                    reserve_vram=data.reserve_vram,
                )
            result = await session.execute(query_values)
            await session.commit()
            return result.rowcount > 0
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to update settings for worker(`%s`, `%s`): %s", user_id, data.worker_id, e)
            return False


async def _compute_flow_progress(flow_status, session) -> float:
    if flow_status.installed:
        return 100.0
    models_list = flow_status.models
    if not models_list:
        return 0.0
    query_models = select(database.ModelsInstallStatus.progress).where(
        database.ModelsInstallStatus.name.in_(models_list)
    )
    model_progresses = (await session.execute(query_models)).scalars().all()
    if not model_progresses:
        return 0.0
    return min(99.0, sum(model_progresses) / len(models_list))


async def get_all_federated_instances() -> list[FederatedInstance]:
    async with database.SESSION() as session:
        try:
            query = select(database.FederatedInstances)
            results = (await session.execute(query)).scalars().all()
            return [FederatedInstance.model_validate(instance) for instance in results]
        except Exception as e:
            LOGGER.exception("Failed to retrieve federated instances: %s.", e)
            return []


async def get_enabled_federated_instances() -> list[FederatedInstance]:
    async with database.SESSION() as session:
        try:
            query = select(database.FederatedInstances).where(database.FederatedInstances.enabled == true())
            results = (await session.execute(query)).scalars().all()
            return [FederatedInstance.model_validate(instance) for instance in results]
        except Exception as e:
            LOGGER.exception("Failed to retrieve enabled federated instances: %s.", e)
            return []


async def add_federated_instance(instance: FederatedInstanceCreate) -> bool:
    async with database.SESSION() as session:
        try:
            session.add(database.FederatedInstances(**instance.model_dump()))
            await session.commit()
            return True
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to add federated instance `%s`: %s.", instance.instance_name, e)
            return False


async def remove_federated_instance(instance_name: str) -> bool:
    async with database.SESSION() as session:
        try:
            stmt = delete(database.FederatedInstances).where(database.FederatedInstances.instance_name == instance_name)
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to remove federated instance `%s`: %s", instance_name, e)
            return False


async def update_federated_instance(instance_name: str, data: FederatedInstanceUpdate) -> bool:
    async with database.SESSION() as session:
        try:
            update_values = data.model_dump(exclude_unset=True)
            if not update_values:
                return False
            stmt = (
                update(database.FederatedInstances)
                .where(database.FederatedInstances.instance_name == instance_name)
                .values(**update_values)
            )
            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount > 0
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to update federated instance `%s`: %s", instance_name, e)
            return False


async def update_installed_flows_for_federated_instance(instance_name: str, installed_flows: dict[str, str]) -> None:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.FederatedInstances)
                .where(database.FederatedInstances.instance_name == instance_name)
                .values(installed_flows=installed_flows)
            )
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to update installed flows for federated instance `%s`: %s", instance_name, e)


async def update_local_workers_from_federation(federation_instance_name: str, workers_list: list[WorkerDetails]):
    """For each worker from a federated instance, update/insert the corresponding record in the local table.
    This function fetches all existing workers for the given federation instance in one query,
    then updates each record by assigning all fields from the corresponding WorkerDetails.
    """
    async with database.SESSION() as session:
        query = select(database.Worker).where(database.Worker.federated_instance_name == federation_instance_name)
        result = await session.execute(query)
        existing_workers = {w.worker_id: w for w in result.scalars().all()}
        for worker in workers_list:
            worker_data = worker.model_dump()
            if worker.worker_id in existing_workers:
                existing_worker = existing_workers[worker.worker_id]
                for key, value in worker_data.items():
                    setattr(existing_worker, key, value)
            else:
                new_worker = database.Worker(**worker_data)
                session.add(new_worker)
        await session.commit()


async def worker_reset_empty_task_requests_count(worker_id: str) -> None:
    async with database.SESSION() as session:
        try:
            stmt = (
                update(database.Worker)
                .where(database.Worker.worker_id == worker_id)
                .values(empty_task_requests_count=0)
            )
            await session.execute(stmt)
            await session.commit()
        except Exception as e:
            await session.rollback()
            LOGGER.exception("Failed to reset worker empty tasks count `%s`: %s", worker_id, e)


async def worker_increment_empty_task_requests_count(worker_id: str) -> None:
    try:
        async with database.SESSION() as session:
            stmt = (
                update(database.Worker)
                .where(database.Worker.worker_id == worker_id)
                .values(empty_task_requests_count=database.Worker.empty_task_requests_count + 1)
            )
            await session.execute(stmt)
            await session.commit()
    except Exception as e:
        await session.rollback()
        LOGGER.exception("Failed to increment worker empty tasks count `%s`: %s", worker_id, e)


async def is_custom_worker_free(custom_worker: str) -> bool:
    async with database.SESSION() as session:
        try:
            query = select(database.TaskDetails).where(
                database.TaskDetails.custom_worker == custom_worker,
                database.TaskDetails.progress < 100,
                database.TaskDetails.error == "",
            )
            return (await session.execute(query)).scalars().first() is None
        except Exception:
            LOGGER.exception("Failed to check unfinished tasks for custom worker '%s'", custom_worker)
            raise


async def delete_workers(user_id: str | None, worker_ids: list[str]) -> int:
    if not worker_ids:
        return 0
    async with database.SESSION() as session:
        try:
            stmt = delete(database.Worker).where(database.Worker.worker_id.in_(worker_ids))
            if user_id is not None:
                stmt = stmt.where(database.Worker.user_id == user_id)

            result = await session.execute(stmt)
            await session.commit()
            return result.rowcount
        except Exception as exc:
            await session.rollback()
            LOGGER.exception("Failed to delete workers %s for user %s: %s", worker_ids, user_id, exc)
            raise
