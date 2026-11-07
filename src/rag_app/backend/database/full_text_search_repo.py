from rag_app.backend.database.core import _engine, chunk_map_table
from sqlalchemy import text, insert
import re


# regex to extract words from string
_WORD_RE = re.compile(r"\w+", re.UNICODE)

def _to_fts_query(user_query: str) -> str | None:
    """Turns user query into a fts5 query of works"""
    words = _WORD_RE.findall(user_query)
    if not words:
        return None

    return " OR ".join(f'"{w}"' for w in words)

def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so '_' or '%' in a path match literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")

# deleting
def _delete_where(conn, where_sql: str, params: dict) -> None:
    conn.execute(
        text(f"DELETE FROM chunks_fts WHERE rowid IN (SELECT rowid FROM chunk_map WHERE {where_sql})"),
        params
    )
    conn.execute(text(f"DELETE FROM chunk_map WHERE {where_sql}"), params)

def delete_by_source(namespace: str, source: str) -> None:
    """Remove all chunks of one file."""
    with _engine.begin() as conn:
        _delete_where(conn, "namespace = :ns AND source = :src", {"ns": namespace, "src": source})


def delete_by_source_prefix(namespace: str, source_prefix: str) -> None:
    """Remove all chunks of every file inside a directory (prefix should end with a separator)."""
    with _engine.begin() as conn:
        _delete_where(
            conn,
            "namespace = :ns AND source LIKE :prefix ESCAPE '\\'",
            {"ns": namespace, "prefix": _escape_like(source_prefix) + "%"},
        )


def delete_namespace(namespace: str) -> None:
    """Remove all chunks of a workspace."""
    with _engine.begin() as conn:
        _delete_where(conn, "namespace = :ns", {"ns": namespace})



# insert
def index_chunks(namespace: str, source: str, chunks: list[tuple[str, str]]) -> None:
    """index one file, chunks = [(chunk_id, text)]"""
    with _engine.begin() as conn:
        # delete the old chunks for the old files
        _delete_where(conn, "namespace = :ns AND source = :src", {"ns": namespace, "src": source})

        # add the new chunks
        for chunk_id, chunk_text in chunks:
            result = conn.execute(
                insert(chunk_map_table).values(chunk_id=chunk_id, namespace=namespace, source=source)
            )

            rowid = result.inserted_primary_key[0]
            conn.execute(
                text("INSERT INTO chunks_fts(rowid, text) VALUES (:rowid, :text)"),
                {"rowid": rowid, "text": chunk_text}
            )



# search
def search(namespace: str, user_query: str, limit: int = 10) -> list[str]:
    fts_query = _to_fts_query(user_query)

    if fts_query is None:
        return []

    with _engine.connect() as conn:
        result_rows = conn.execute(
            text("""
                SELECT m.chunk_id
                FROM chunk_fts
                JOIN chunk_map AS m ON m.rowid = chunk_fts.rowid
                WHERE chunks_fts MATCH :q AND m.namespace = :namespace
                ORDER BY bm25(chunks_fts) ASC
                LIMIT :limit    
            """),
            {"q": fts_query, "namespace": namespace, "limit": limit}
        )

        return [row[0] for row in result_rows]
