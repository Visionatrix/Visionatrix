import os
from datetime import datetime, timezone

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
    create_engine,
    inspect,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from . import options, pydantic_models

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
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
    worker_id = Column(String, ForeignKey("workers.worker_id"), nullable=True, default=None, index=True)
    progress = Column(Float, default=0.0, index=True)
    error = Column(String, default="")
    name = Column(String, default="")
    input_params = Column(JSON, default={})
    outputs = Column(JSON, default=[])
    input_files = Column(JSON, default=[])
    flow_comfy = Column(JSON, default={})
    task_queue = relationship("TaskQueue")
    user_info = relationship("UserInfo", backref="task_details")
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
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False, index=True)
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


def init_database_engine() -> None:
    global SESSION, SESSION_ASYNC
    connect_args = {}
    database_uri = options.DATABASE_URI
    if database_uri.startswith("sqlite:"):
        connect_args = {"check_same_thread": False}
        if database_uri.startswith("sqlite:///."):
            database_uri = f"sqlite:///{os.path.abspath(os.path.join(os.getcwd(), database_uri[10:]))}"
    engine = create_engine(database_uri, connect_args=connect_args)
    inspector = inspect(engine)
    is_new_database = not bool(inspector.get_table_names())
    Base.metadata.create_all(engine)
    SESSION = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)
    if is_new_database:
        create_user(
            DEFAULT_USER.user_id,
            DEFAULT_USER.full_name,
            DEFAULT_USER.email,
            "admin",
            DEFAULT_USER.is_admin,
            False,
        )
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
