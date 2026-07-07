import os
from pathlib import Path
from typing import Final
from sqlalchemy import text
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    BSHTMLLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.indexing import index

from rag_app.backend.config import config
from rag_app.backend.utils import is_text_file
from rag_app.backend.database.core import get_vector_db, get_record_manager, _engine

_text_splitter: Final = RecursiveCharacterTextSplitter(
    chunk_size=1500, chunk_overlap=100
)


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
        get_record_manager(),  # type: ignore
        get_vector_db(),
        cleanup="incremental",
        source_id_key="source",
        key_encoder="sha256",
    )

    # print(f"Indexing complete for '{filename}': {indexing_result}")

    return (True, f"{len(doc_chunks)} chunks")


def remove_resource(filename: str) -> bool:
    file_path = config.resources_dir / filename
    rm = get_record_manager()

    keys_to_delete = rm.list_keys(group_ids=[str(file_path)])

    if not keys_to_delete:
        print(f"Not records found to delete, for file {filename}")
        return False

    get_vector_db().delete(keys_to_delete)
    rm.delete_keys(keys_to_delete)

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
            AND namespace = :namespace
                     
        """)

        target_namespace = f"chroma/{config.workspace_id}"

        result = conn.execute(
            query, {"target_dir": f"{target_dir}%", "namespace": target_namespace}
        )

        keys_to_delete = [row[0] for row in result]

    if not keys_to_delete:
        print("No record to delete")
        return False

    get_vector_db().delete(keys_to_delete)
    get_record_manager().delete_keys(keys_to_delete)

    return True


def remove_all_resources() -> None:
    rm = get_record_manager()
    all_keys = rm.list_keys()

    if not all_keys:
        print("Database already empty")
        return

    get_vector_db().delete(all_keys)
    rm.delete_keys(all_keys)


def list_all_uploaded_files() -> list[str]:
    query = text("""
                 SELECT DISTINCT group_id
                 FROM upsertion_record
                 WHERE namespace = :namespace AND group_id IS NOT NULL
                 """)

    with _engine.connect() as conn:
        target_namespace = f"chroma/{config.workspace_id}"
        result = conn.execute(query, {"namespace": target_namespace})

        unique_files = []
        for row in result:
            unique_files.append(str(Path(row[0]).relative_to(config.resources_dir)))

        return unique_files
