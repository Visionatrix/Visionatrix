import importlib.resources
import logging
import os
from datetime import datetime, timezone

from alembic import command
from alembic.config import Config
from passlib.context import CryptContext
from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    create_engine,
    delete,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from . import options, pydantic_models

LOGGER = logging.getLogger("visionatrix")
SESSION: sessionmaker
SESSION_ASYNC: async_sessionmaker  # only for the "SERVER" mode
Base = declarative_base()


DEFAULT_USER = pydantic_models.UserInfo(
    user_id="admin",
    full_name="John Doe",
    email="admin@example.com",
    is_admin=True,
)


class TaskQueue(Base):
    __tablename__ = "tasks_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)


class TaskDetails(Base):
    __tablename__ = "tasks_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks_queue.id"), nullable=False, unique=True)
    user_id = Column(String, nullable=False, index=True)
    worker_id = Column(String, ForeignKey("workers.worker_id"), nullable=True, default=None, index=True)
    progress = Column(Float, default=0.0, index=True)
    error = Column(String, default="")
    name = Column(String, default="")
    input_params = Column(JSON, default={})
    outputs = Column(JSON, default=[])
    input_files = Column(JSON, default=[])
    flow_comfy = Column(JSON, default={})
    task_queue = relationship("TaskQueue")
    created_at = Column(DateTime, default=datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True, default=None, index=True)
    finished_at = Column(DateTime, nullable=True, default=None)
    execution_time = Column(Float, default=0.0)


class TaskLock(Base):
    __tablename__ = "task_locks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks_queue.id"), nullable=False, unique=True)
    locked_at = Column(DateTime, default=datetime.now(timezone.utc))
    task_queue = relationship("TaskQueue", backref="lock")


class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    worker_id = Column(String, comment="user_id:hostname:device_name:device_index", unique=True)
    worker_version = Column(String, default="")
    last_seen = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    tasks_to_give = Column(JSON, default=[])

    os = Column(String)
    version = Column(String)
    embedded_python = Column(Boolean, default=False)

    device_name = Column(String)
    device_type = Column(String)

    vram_total = Column(BigInteger)
    vram_free = Column(BigInteger)
    torch_vram_total = Column(BigInteger)
    torch_vram_free = Column(BigInteger)
    ram_total = Column(BigInteger)
    ram_free = Column(BigInteger)


class UserInfo(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True)
    full_name = Column(String, default="")
    email = Column(String, default="")
    is_admin = Column(Boolean, default=False)
    hashed_password = Column(String)
    disabled = Column(Boolean, default=False)


class GlobalSettings(Base):
    __tablename__ = "global_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)
    sensitive = Column(Boolean, default=True)


class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "name", name="user_id_name_uc"),)


def init_database_engine() -> None:
    global SESSION, SESSION_ASYNC
    connect_args = {}
    database_uri = options.DATABASE_URI
    if database_uri.startswith("sqlite:"):
        connect_args = {"check_same_thread": False}
        if database_uri.startswith("sqlite:///."):
            database_uri = f"sqlite:///{os.path.abspath(os.path.join(os.getcwd(), database_uri[10:]))}"
    engine = create_engine(database_uri, connect_args=connect_args)
    SESSION = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    run_db_migrations(database_uri)
    if options.VIX_MODE == "SERVER":
        async_engine = create_async_engine(
            os.environ.get("DATABASE_URI_ASYNC", database_uri), connect_args=connect_args
        )
        SESSION_ASYNC = async_sessionmaker(
            bind=async_engine, class_=AsyncSession, autocommit=False, autoflush=False, expire_on_commit=False
        )


def create_user(username: str, full_name: str, email: str, password: str, is_admin: bool, disabled: bool) -> bool:
    session = SESSION()
    try:
        session.add(
            UserInfo(
                user_id=username,
                full_name=full_name,
                email=email,
                hashed_password=CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password),
                is_admin=is_admin,
                disabled=disabled,
            )
        )
        session.commit()
        return True
    finally:
        session.close()


def run_db_migrations(database_url: str):
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(importlib.resources.files("visionatrix").joinpath("alembic")))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(alembic_cfg, "head")


def get_setting(user_id: str, key: str, admin: bool) -> str:
    if value := get_user_setting(user_id, key):
        return value
    return get_global_setting(key, admin)


async def get_setting_async(user_id: str, key: str, admin: bool) -> str:
    if value := await get_user_setting_async(user_id, key):
        return value
    return await get_global_setting_async(key, admin)


def get_global_setting(key: str, admin: bool) -> str:
    session = SESSION()
    try:
        query = select(GlobalSettings.value, GlobalSettings.sensitive).where(GlobalSettings.name == key)
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


async def get_global_setting_async(key: str, admin: bool) -> str:
    async with SESSION_ASYNC() as session:
        try:
            query = select(GlobalSettings.value, GlobalSettings.sensitive).where(GlobalSettings.name == key)
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


def get_user_setting(user_id: str, key: str) -> str:
    session = SESSION()
    try:
        query = select(UserSettings.value).where(UserSettings.user_id == user_id, UserSettings.name == key)
        result = session.execute(query).scalar_one_or_none()
        return result if result is not None else ""
    except Exception:
        LOGGER.error("Failed to retrieve user setting for `%s`: `%s`", user_id, key)
        raise
    finally:
        session.close()


async def get_user_setting_async(user_id: str, key: str) -> str:
    async with SESSION_ASYNC() as session:
        try:
            query = select(UserSettings.value).where(UserSettings.user_id == user_id, UserSettings.name == key)
            result = (await session.execute(query)).scalar_one_or_none()
            return result if result is not None else ""
        except Exception:
            LOGGER.exception("Failed to retrieve user setting for `%s`: `%s`", user_id, key)
            raise


def set_global_setting(key: str, value: str, sensitive: bool) -> None:
    session = SESSION()
    try:
        if value:
            stmt = update(GlobalSettings).where(GlobalSettings.name == key).values(value=value, sensitive=sensitive)
            result = session.execute(stmt)
            if result.rowcount == 0:
                session.add(GlobalSettings(name=key, value=value, sensitive=sensitive))
            session.commit()
        else:
            result = session.execute(delete(GlobalSettings).where(GlobalSettings.name == key))
            if result.rowcount:
                session.commit()
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to set global setting for `%s`", key)
        raise
    finally:
        session.close()


async def set_global_setting_async(key: str, value: str, sensitive: bool) -> None:
    async with SESSION_ASYNC() as session:
        try:
            if value:
                stmt = update(GlobalSettings).where(GlobalSettings.name == key).values(value=value, sensitive=sensitive)
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    session.add(GlobalSettings(name=key, value=value, sensitive=sensitive))
                await session.commit()
            else:
                result = await session.execute(delete(GlobalSettings).where(GlobalSettings.name == key))
                if result.rowcount:
                    await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to set global setting for `%s`", key)
            raise


def set_user_setting(user_id: str, key: str, value: str) -> None:
    session = SESSION()
    try:
        if value:
            stmt = (
                update(UserSettings)
                .where(UserSettings.user_id == user_id, UserSettings.name == key)
                .values(value=value)
            )
            result = session.execute(stmt)
            if result.rowcount == 0:
                session.add(UserSettings(user_id=user_id, name=key, value=value))
            session.commit()
        else:
            result = session.execute(
                delete(UserSettings).where(UserSettings.user_id == user_id, UserSettings.name == key)
            )
            if result.rowcount:
                session.commit()
    except Exception:
        session.rollback()
        LOGGER.exception("Failed to set user setting for `%s`: `%s`", user_id, key)
        raise
    finally:
        session.close()


async def set_user_setting_async(user_id: str, key: str, value: str) -> None:
    async with SESSION_ASYNC() as session:
        try:
            if value:
                stmt = (
                    update(UserSettings)
                    .where(UserSettings.user_id == user_id, UserSettings.name == key)
                    .values(value=value)
                )
                result = await session.execute(stmt)
                if result.rowcount == 0:
                    session.add(UserSettings(user_id=user_id, name=key, value=value))
                await session.commit()
            else:
                result = await session.execute(
                    delete(UserSettings).where(UserSettings.user_id == user_id, UserSettings.name == key)
                )
                if result.rowcount:
                    await session.commit()
        except Exception:
            await session.rollback()
            LOGGER.exception("Failed to set user setting for `%s`: `%s`", user_id, key)
            raise
