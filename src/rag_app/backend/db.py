from langchain_core.documents import Document
from langchain_postgres import PGVector
from langchain_ollama import OllamaEmbeddings
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.indexes import _sql_record_manager
from langchain_core.indexing import index
from sqlalchemy import create_engine, text
import os
from typing import Final
from pathlib import Path

DB_CONNECTION_STRING: Final = (
    "postgresql+psycopg://myuser:mypassword@localhost:5432/vectordb"
)
COLLECTION_NAME: Final = "test_collection"

DOCUMENT_BASE_DIR = Path(__file__).parent.parent.parent.parent / "documents"

# init local ollama model
embeddings_model: Final = OllamaEmbeddings(model="nomic-embed-text")

# connect to the pgvector db
vector_database: Final = PGVector(
    embeddings=embeddings_model,
    collection_name=COLLECTION_NAME,
    connection=DB_CONNECTION_STRING,
    use_jsonb=True,
)

text_splitter: Final = RecursiveCharacterTextSplitter(
    chunk_size=1500, chunk_overlap=100
)

retriever = vector_database.as_retriever(
    search_type="similarity_score_threshold",
    search_kwargs={"k": 5, "score_threshold": 0.5},
)

# record manager to not save same files multiple times
record_manager = _sql_record_manager.SQLRecordManager(
    namespace=f"pgvector/{COLLECTION_NAME}", db_url=DB_CONNECTION_STRING
)

record_manager.create_schema()

# normal connection to db
engine = create_engine(DB_CONNECTION_STRING)
db_connection = engine.connect()


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
    else:
        print(f"File with extention {file_extension} is not supported")
        return False

    raw_doc = loader.load()

    doc_chunks = text_splitter.split_documents(raw_doc)

    print(f"Document splitted into {len(doc_chunks)} chunks")

    # vector_database.add_documents(documents=doc_chunks)
    # add documents to the database with indexing
    indexing_result = index(
        doc_chunks,
        record_manager,  # type: ignore
        vector_database,
        cleanup="incremental",
        source_id_key="source",
        key_encoder="sha256",
    )

    # print(f"Indexing complete for '{filename}': {indexing_result}")

    return True


def remove_resource(filename: str) -> bool:
    file_path = DOCUMENT_BASE_DIR / filename

    keys_to_delete = record_manager.list_keys(group_ids=[str(file_path)])

    if not keys_to_delete:
        print(f"Not records found to delete, for file {filename}")
        return False

    vector_database.delete(keys_to_delete)
    record_manager.delete_keys(keys_to_delete)

    return True


def list_all_uploaded_files() -> list[str]:
    query = text("""
                 SELECT DISTINCT group_id
                 FROM upsertion_record
                 WHERE group_id IS NOT NULL
                 """)

    result = db_connection.execute(query)

    unique_files = [row[0].split("/")[-1] for row in result]

    return unique_files
