from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    BSHTMLLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.indexes import _sql_record_manager
from langchain_core.indexing import index
from sqlalchemy import MetaData, Table, Column, String, select, create_engine, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
import os
from typing import Final
from pathlib import Path
from langchain_chroma import Chroma
from rag_app.backend.config import ConfigKeys
from rag_app.backend.config import config
import string

# connect to the database
DB_CONNECTION_STRING: Final = f"sqlite:///{config.data_dir / 'record_manager.sqlite'}"
COLLECTION_NAME: Final = "rag-files"


def get_vector_db() -> Chroma:
    """Always returns a fresh Chroma connection using the latest config."""
    return Chroma(
        embedding_function=config.embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(config.data_dir / "chroma_db"),
    )


def get_retriever():
    """Builds a retriever dynamically from the fresh vector db."""
    return get_vector_db().as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 5, "score_threshold": 0.5},
    )


_text_splitter: Final = RecursiveCharacterTextSplitter(
    chunk_size=1500, chunk_overlap=100
)

# record manager to not save same files multiple times
_record_manager = _sql_record_manager.SQLRecordManager(
    namespace=f"chroma/{COLLECTION_NAME}", db_url=DB_CONNECTION_STRING
)

_record_manager.create_schema()

# normal connection to db
_engine = create_engine(DB_CONNECTION_STRING)

# add the user config table
metadata = MetaData()
user_config_table = Table(
    "user_config",
    metadata,
    Column("config_key", String, primary_key=True),
    Column("config_value", String, nullable=False),
)

metadata.create_all(_engine)


def is_text_file(file_path: Path | str) -> bool:
    """Function to check if file is a text or binary file - not 100% reliable"""

    try:
        with open(file_path, "rb") as f:
            chunk = f.read(1024)

        if not chunk:
            return True

        # if the file contains null byte - it is binary
        if b"\x00" in chunk:
            return False

        text = chunk.decode("utf-8", errors="ignore")

        text_chars = sum(1 for char in text if char.isprintable() or char in "\n\r\t")

        text_binary_ratio = text_chars / len(chunk)

        # check if at least 85% of the file is text
        return text_binary_ratio > 0.85

    except FileNotFoundError:
        return False


def add_resource(filename: str) -> tuple[bool, str]:
    file_path = config.resources_dir / filename

    print("File path is: " + str(file_path))

    # check if the file exists
    if not os.path.exists(file_path):
        print(f"File with name: {filename} is not in the documents folders")
        return (False, f"File at path: {file_path} doesn't exist")

    # check if it isnt a folder
    if Path(file_path).is_dir():
        return (False, "For adding directories use `/add-resources-dir`")

    # choose correct loader based on the extension
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    if file_extension == ".pdf":
        loader = PyPDFLoader(file_path)
    elif file_extension == ".html":
        loader = BSHTMLLoader(file_path)  # type: ignore
    elif is_text_file(file_path):
        try:
            loader = TextLoader(file_path)  # type: ignore
        except Exception as e:
            print(f"Failed to add text file {e}")
            return (False, "Failed to load text file.")

    else:
        print(f"File with extension {file_extension} is not supported")
        return (False, f"Unsupported file type: {file_extension}")

    raw_doc = loader.load()

    doc_chunks = _text_splitter.split_documents(raw_doc)

    # check if the file wasnt empty
    if len(doc_chunks) == 0:
        return (False, "Empty file")

    print(f"Document splitted into {len(doc_chunks)} chunks")

    # add documents to the database with indexing
    index(
        doc_chunks,
        _record_manager,  # type: ignore
        get_vector_db(),
        cleanup="incremental",
        source_id_key="source",
        key_encoder="sha256",
    )

    # print(f"Indexing complete for '{filename}': {indexing_result}")

    return (True, f"{len(doc_chunks)} chunks")


def remove_resource(filename: str) -> bool:
    file_path = config.resources_dir / filename

    keys_to_delete = _record_manager.list_keys(group_ids=[str(file_path)])

    if not keys_to_delete:
        print(f"Not records found to delete, for file {filename}")
        return False

    get_vector_db().delete(keys_to_delete)
    _record_manager.delete_keys(keys_to_delete)

    return True


def remove_resources_dir(subdir_name: str) -> bool:
    target_dir = str(config.resources_dir / subdir_name)

    if not target_dir.endswith(os.sep):
        target_dir += os.sep

    with _engine.connect() as conn:
        query = text("""
            SELECT key
            FROM upsertion_record
            WHERE group_id LIKE :target_dir
        """)

        result = conn.execute(query, {"target_dir": f"{target_dir}%"})

        keys_to_delete = [row[0] for row in result]

    if not keys_to_delete:
        print("No record to delete")
        return False

    get_vector_db().delete(keys_to_delete)
    _record_manager.delete_keys(keys_to_delete)

    return True


def remove_all_resources() -> None:
    all_keys = _record_manager.list_keys()

    if not all_keys:
        print("Database already empty")
        return

    get_vector_db().delete(all_keys)
    _record_manager.delete_keys(all_keys)


def list_all_uploaded_files() -> list[str]:
    query = text("""
                 SELECT DISTINCT group_id
                 FROM upsertion_record
                 WHERE group_id IS NOT NULL
                 """)

    with _engine.connect() as conn:
        result = conn.execute(query)

        unique_files = []
        for row in result:
            unique_files.append(str(Path(row[0]).relative_to(config.resources_dir)))

        return unique_files


def set_config(key: str, value: str) -> None:
    with _engine.connect() as conn:
        # upsert the value to the config table
        query = sqlite_insert(user_config_table).values(
            config_key=key, config_value=value.strip()
        )

        query = query.on_conflict_do_update(
            index_elements=["config_key"],
            set_=dict(config_value=query.excluded.config_value),
        )

        conn.execute(query)
        conn.commit()


def get_config(key: str, default: str | None = None) -> str | None:
    with _engine.connect() as conn:
        query = select(user_config_table.c.config_value).where(
            user_config_table.c.config_key == key
        )

        result = conn.execute(query).scalar_one_or_none()

        return result if result is not None else default


def get_configs(keys: list[str]) -> dict[str, str]:
    with _engine.connect() as conn:
        query = select(
            user_config_table.c.config_key, user_config_table.c.config_value
        ).where(user_config_table.c.config_key.in_(keys))

        result = conn.execute(query)
        return {row[0]: row[1] for row in result}


def save_configs(config_dict: dict[str, str]) -> bool:
    try:
        values_to_insert = [
            {"config_key": key, "config_value": value.strip()}
            for key, value in config_dict.items()
        ]

        with _engine.connect() as conn:
            query = sqlite_insert(user_config_table).values(values_to_insert)

            query = query.on_conflict_do_update(
                index_elements=["config_key"],
                set_=dict(config_value=query.excluded.config_value),
            )

            conn.execute(query)
            conn.commit()

        return True
    except Exception as e:
        print(f"Failed to save configs: {e}")
        return False


def load_all_config_values() -> None:
    global gen_model, embed_model, resources_dir

    keys_to_fetch = [
        ConfigKeys.RESOURCES_DIR.value,
        ConfigKeys.GEN_MODEL.value,
        ConfigKeys.EMBED_MODEL.value,
    ]

    db_configs = get_configs(keys_to_fetch)

    if ConfigKeys.RESOURCES_DIR.value in db_configs:
        config.resources_dir = Path(db_configs[ConfigKeys.RESOURCES_DIR.value])

    if ConfigKeys.GEN_MODEL.value in db_configs:
        config.gen_model = db_configs[ConfigKeys.GEN_MODEL.value]

    if ConfigKeys.EMBED_MODEL.value in db_configs:
        config.embed_model = db_configs[ConfigKeys.EMBED_MODEL.value]
