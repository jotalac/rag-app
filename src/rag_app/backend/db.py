from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import (
    TextLoader,
    PyPDFLoader,
    BSHTMLLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.indexes import _sql_record_manager
from langchain_core.indexing import index
from sqlalchemy import create_engine, text
import os
from typing import Final
from pathlib import Path
from langchain_chroma import Chroma

ROOT_PATH = Path(__file__).parent.parent.parent.parent

# dir for the database
DATA_DIR = ROOT_PATH / ".rag_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

# connect to the database
DB_CONNECTION_STRING: Final = f"sqlite:///{DATA_DIR / 'record_manager.sqlite'}"
COLLECTION_NAME: Final = "rag-files"

# folder documents (later it will be entered by the user and saved in the db)
DOCUMENT_BASE_DIR = ROOT_PATH / "documents"

# init local ollama model
embeddings_model: Final = OllamaEmbeddings(model="nomic-embed-text")

# connect to the chroma db
_vector_database: Final = Chroma(
    embedding_function=embeddings_model,
    collection_name=COLLECTION_NAME,
    persist_directory=str(DATA_DIR / "chroma_db"),
)

_text_splitter: Final = RecursiveCharacterTextSplitter(
    chunk_size=1500, chunk_overlap=100
)

retriever = _vector_database.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 5, "score_threshold": 0.5},
)

# record manager to not save same files multiple times
_record_manager = _sql_record_manager.SQLRecordManager(
    namespace=f"chroma/{COLLECTION_NAME}", db_url=DB_CONNECTION_STRING
)

_record_manager.create_schema()

# normal connection to db
_engine = create_engine(DB_CONNECTION_STRING)
_db_connection = _engine.connect()


def add_resource(filename: str) -> bool:
    file_path = DOCUMENT_BASE_DIR / filename

    print("File path is: " + str(file_path))

    # check if the file exists
    if not os.path.exists(file_path):
        print(f"File with name: {filename} is not in the documents folders")
        return False

    # choose correct loader based on the extention
    _, file_extension = os.path.splitext(file_path)
    file_extension = file_extension.lower()

    if file_extension == ".pdf":
        loader = PyPDFLoader(file_path)
    elif file_extension == ".txt":
        loader = TextLoader(file_path)  # type: ignore
    elif file_extension == ".html":
        loader = BSHTMLLoader(file_path)
    else:
        print(f"File with extention {file_extension} is not supported")
        return False

    raw_doc = loader.load()

    doc_chunks = _text_splitter.split_documents(raw_doc)

    print(f"Document splitted into {len(doc_chunks)} chunks")

    # vector_database.add_documents(documents=doc_chunks)
    # add documents to the database with indexing
    indexing_result = index(
        doc_chunks,
        _record_manager,  # type: ignore
        _vector_database,
        cleanup="incremental",
        source_id_key="source",
        key_encoder="sha256",
    )

    # print(f"Indexing complete for '{filename}': {indexing_result}")

    return True


def remove_resource(filename: str) -> bool:
    file_path = DOCUMENT_BASE_DIR / filename

    # if the file is not at the root docs directory search recursively
    if not file_path.exists():
        matches = list(DOCUMENT_BASE_DIR.rglob(filename))

        if len(matches) > 1:
            print(f"Multiple files with name: {filename}")
            return False

        if not matches:
            print(f"Not file named: {filename}")
            return False

        file_path = matches[0]

    keys_to_delete = _record_manager.list_keys(group_ids=[str(file_path)])

    if not keys_to_delete:
        print(f"Not records found to delete, for file {filename}")
        return False

    _vector_database.delete(keys_to_delete)
    _record_manager.delete_keys(keys_to_delete)

    return True


def remove_all_resources() -> None:
    all_keys = _record_manager.list_keys()

    _vector_database.delete(all_keys)
    _record_manager.delete_keys(all_keys)


def list_all_uploaded_files() -> list[str]:
    query = text("""
                 SELECT DISTINCT group_id
                 FROM upsertion_record
                 WHERE group_id IS NOT NULL
                 """)

    result = _db_connection.execute(query)

    unique_files = []
    for row in result:
        unique_files.append(str(Path(row[0]).relative_to(DOCUMENT_BASE_DIR)))

    return unique_files
