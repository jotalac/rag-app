from typing import Final
from sqlalchemy import create_engine, MetaData, Table, Column, String
from langchain_community.indexes import _sql_record_manager
from langchain_chroma import Chroma
from rag_app.backend.config import config

DB_CONNECTION_STRING: Final = f"sqlite:///{config.data_dir / 'record_manager.sqlite'}"

_engine = create_engine(DB_CONNECTION_STRING)
metadata = MetaData()

user_config_table = Table(
    "user_config",
    metadata,
    Column("config_key", String, primary_key=True),
    Column("config_value", String, nullable=False),
)

workspaces_table = Table(
    "workspaces",
    metadata,
    Column("id", String, primary_key=True),
    Column("name", String, unique=True, nullable=False),
    Column("resources_dir", String, nullable=False),
    Column("gen_model", String, nullable=False),
    Column("embed_model", String, nullable=False),
)

metadata.create_all(_engine)

# create the record manager if not exists
_sql_record_manager.SQLRecordManager(namespace="init", engine=_engine).create_schema()


def get_vector_db() -> Chroma:
    """Always returns a fresh Chroma connection using the latest config."""
    return Chroma(
        embedding_function=config.embeddings,
        collection_name=str(config.workspace_id),
        persist_directory=str(config.data_dir / "chroma_db"),
    )


def get_retriever():
    """Builds a retriever dynamically from the fresh vector db."""
    return get_vector_db().as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 5, "score_threshold": 0.5},
    )


_cached_record_manager: _sql_record_manager.SQLRecordManager | None = None
_cached_workspace_id = None


def get_record_manager() -> _sql_record_manager.SQLRecordManager:
    global _cached_record_manager, _cached_workspace_id

    if (
        _cached_record_manager is not None
        and _cached_workspace_id == config.workspace_id
    ):
        return _cached_record_manager

    _cached_workspace_id = config.workspace_id

    _cached_record_manager = _sql_record_manager.SQLRecordManager(
        namespace=f"chroma/{config.workspace_id}", engine=_engine
    )

    _cached_record_manager.create_schema()

    return _cached_record_manager


def clear_record_manager_cache():
    global _cached_record_manager, _cached_workspace_id
    _cached_record_manager = None
    _cached_workspace_id = None
