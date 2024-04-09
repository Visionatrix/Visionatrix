import os
from datetime import datetime

from passlib.context import CryptContext
from sqlalchemy import (
    JSON,
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
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

from . import options

SESSION: sessionmaker
PWD_CONTEXT = CryptContext(schemes=["bcrypt"], deprecated="auto")
Base = declarative_base()


class TaskQueue(Base):
    __tablename__ = "tasks_queue"
    id = Column(Integer, primary_key=True, autoincrement=True)


class TaskDetails(Base):
    __tablename__ = "tasks_details"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks_queue.id"), nullable=False, unique=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    progress = Column(Float, default=0.0)
    error = Column(String, default="")
    name = Column(String, default="")
    input_params = Column(JSON, default={})
    outputs = Column(JSON, default=[])
    input_files = Column(JSON, default=[])
    flow_comfy = Column(JSON, default={})
    task_queue = relationship("TaskQueue")
    user_info = relationship("UserInfo", backref="task_details")


class TaskLock(Base):
    __tablename__ = "task_locks"
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks_queue.id"), nullable=False, unique=True)
    locked_at = Column(DateTime, default=datetime.utcnow)
    task_queue = relationship("TaskQueue", backref="lock")


class UserInfo(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, unique=True)
    full_name = Column(String, default="")
    email = Column(String)
    hashed_password = Column(String)
    is_admin = Column(Boolean, default=False)
    disabled = Column(Boolean, default=False)


def get_user(username: str, password: str) -> UserInfo | None:
    session = SESSION()
    try:
        userinfo = session.query(UserInfo).filter_by(user_id=username).first()
        if userinfo and PWD_CONTEXT.verify(password, userinfo.hashed_password):
            return userinfo
        return None
    finally:
        session.close()


def create_user(username: str, full_name: str, email: str, password: str, is_admin: bool, disabled: bool) -> bool:
    session = SESSION()
    try:
        session.add(
            UserInfo(
                user_id=username,
                full_name=full_name,
                email=email,
                hashed_password=PWD_CONTEXT.hash(password),
                is_admin=is_admin,
                disabled=disabled,
            )
        )
        session.commit()
        return True
    finally:
        session.close()


def init_database_engine() -> None:
    global SESSION
    connect_args = {}
    database_uri = options.DATABASE_URI
    if database_uri.startswith("sqlite:"):
        connect_args = {"check_same_thread": False}
        if database_uri.startswith("sqlite:///."):
            database_uri = f"sqlite:///{os.path.abspath(os.path.join(options.TASKS_FILES_DIR, database_uri[10:]))}"
    engine = create_engine(database_uri, connect_args=connect_args)
    inspector = inspect(engine)
    is_new_database = not bool(inspector.get_table_names())
    Base.metadata.create_all(engine)
    SESSION = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    if is_new_database:
        create_user(
            "admin",
            "John Doe",
            "admin@example.com",
            "admin",
            is_admin=True,
            disabled=False,
        )
