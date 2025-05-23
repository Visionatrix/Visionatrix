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
    Index,
    Integer,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from . import options, pydantic_models

LOGGER = logging.getLogger("visionatrix")
SESSION: async_sessionmaker | None = None
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
    priority = Column(Integer, nullable=True, default=0, index=True)
    worker_id = Column(String, ForeignKey("workers.worker_id"), nullable=True, default=None, index=True)
    progress = Column(Float, default=0.0, index=True)
    error = Column(String, default="")
    name = Column(String, default="", nullable=False)
    input_params = Column(JSON, default={})
    outputs = Column(JSON, default=[])
    input_files = Column(JSON, default=[])
    flow_comfy = Column(JSON, default={}, nullable=False)
    task_queue = relationship("TaskQueue")
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, nullable=True, default=None, index=True)
    finished_at = Column(DateTime, nullable=True, default=None)
    execution_time = Column(Float, default=0.0)
    group_scope = Column(Integer, default=1, index=True)
    webhook_url = Column(String, nullable=True)
    webhook_headers = Column(JSON, nullable=True)
    parent_task_id = Column(Integer, nullable=True, index=True)
    parent_task_node_id = Column(Integer, nullable=True)
    translated_input_params = Column(JSON, default=None)
    execution_details = Column(JSON, default=None, nullable=True)
    extra_flags = Column(JSON, default=None, nullable=True)
    custom_worker = Column(String, default=None, index=True)
    hidden = Column(Boolean, nullable=True)

    __table_args__ = (Index("ix_parent_task", "parent_task_id", "parent_task_node_id"),)


class TaskLock(Base):
    __tablename__ = "task_locks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks_queue.id"), nullable=False, unique=True)
    locked_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    task_queue = relationship("TaskQueue", backref="lock")


class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False, index=True)
    worker_id = Column(String, comment="user_id:hostname:device_name:device_index", unique=True, nullable=False)
    worker_version = Column(String, default="")
    pytorch_version = Column(String, default="")
    last_seen = Column(DateTime, default=datetime.now(timezone.utc), index=True, nullable=False)
    tasks_to_give = Column(JSON, default=[])
    smart_memory = Column(Boolean, nullable=True)
    cache_type = Column(String, nullable=True)
    cache_size = Column(Integer, nullable=True)
    vae_cpu = Column(Boolean, nullable=True)
    reserve_vram = Column(Float, nullable=True)

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
    engine_details = Column(JSON, default=None, nullable=True)
    federated_instance_name = Column(String, nullable=False, default="", index=True)
    empty_task_requests_count = Column(BigInteger, nullable=False, default=0, index=True)
    last_asked_tasks = Column(JSON, default=[], nullable=False)


class UserInfo(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True, nullable=False)
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
    crc32 = Column(BigInteger, nullable=True)


class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    value = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint("user_id", "name", name="user_id_name_uc"),)


class FlowsInstallStatus(Base):
    __tablename__ = "flows_install_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    flow_comfy = Column(JSON, default={}, nullable=False)
    error = Column(String, default="")
    started_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    installed = Column(Boolean, default=False, nullable=False, index=True)
    models = Column(JSON, nullable=True)


class ModelsInstallStatus(Base):
    __tablename__ = "models_install_status"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    flow_name = Column(String, nullable=False)
    progress = Column(Float, default=0.0, nullable=False)
    error = Column(String, default="")
    started_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    file_mtime = Column(Float, nullable=True)
    filename = Column(String, default="")


class FederatedInstances(Base):
    __tablename__ = "federated_instances"
    id = Column(Integer, primary_key=True, autoincrement=True)
    instance_name = Column(String, unique=True, nullable=False, index=True)
    enabled = Column(Boolean, default=True, nullable=False, index=True)
    url_address = Column(String, nullable=False)
    username = Column(String, nullable=False)
    password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), nullable=False)
    installed_flows = Column(JSON, nullable=False, default={})


class FlowDelegationConfig(Base):
    __tablename__ = "flow_delegation_config"
    id = Column(Integer, primary_key=True, autoincrement=True)
    flow_name = Column(String, unique=True, nullable=False, index=True)
    delegation_threshold = Column(Integer, default=0, nullable=False)


class BackgroundJobLock(Base):
    __tablename__ = "background_job_locks"
    job_name = Column(String, primary_key=True)
    worker_id = Column(String, nullable=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    last_run_at = Column(DateTime, nullable=True, index=True)


class SystemSettings(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False, unique=True)
    value = Column(String, nullable=False)


async def init_database_engine() -> None:
    global SESSION
    if SESSION is not None:
        return
    connect_args = {}
    database_uri = options.DATABASE_URI
    if database_uri.startswith("sqlite"):
        connect_args = {
            "check_same_thread": False,
            "timeout": 12,
        }
        local_dir = "sqlite+aiosqlite:///."
        if database_uri.startswith(local_dir):
            database_uri = (
                f"sqlite+aiosqlite:///{os.path.abspath(os.path.join(os.getcwd(), database_uri[len(local_dir) - 1:]))}"
            )
        LOGGER.debug("SQLite file in use: %s", database_uri)

    engine = create_async_engine(database_uri, connect_args=connect_args)

    if database_uri.startswith("sqlite"):
        async with engine.connect() as connection:
            current_mode = (await connection.execute(text("PRAGMA journal_mode;"))).scalar()
            if current_mode.lower() != "wal":
                new_mode = (await connection.execute(text("PRAGMA journal_mode=WAL;"))).scalar()
                if new_mode.lower() != "wal":
                    raise RuntimeError("Failed to set SQLite journal mode to WAL.")
                LOGGER.info("SQLite journal mode set to WAL.")

    SESSION = async_sessionmaker(
        autocommit=False, autoflush=False, bind=engine, expire_on_commit=False, class_=AsyncSession
    )
    async with engine.connect() as connection:
        await connection.run_sync(run_db_migrations, database_uri)


async def create_user(username: str, full_name: str, email: str, password: str, is_admin: bool, disabled: bool) -> bool:
    async with SESSION() as session:
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
        await session.commit()
        return True


def run_db_migrations(connection, database_url: str):
    alembic_cfg = Config()
    alembic_cfg.set_main_option("script_location", str(importlib.resources.files("visionatrix").joinpath("alembic")))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    alembic_cfg.attributes["connection"] = connection
    command.upgrade(alembic_cfg, "head")
