import uuid
from sqlalchemy import select, delete, text
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from pathlib import Path
from langchain_chroma import Chroma

from rag_app.backend.config import config
from rag_app.backend.database.core import (
    _engine,
    workspaces_table,
    clear_record_manager_cache,
)


def get_workspace_info(workspace_name: str) -> tuple[str, uuid.UUID, str, str] | None:
    with _engine.connect() as conn:
        query = select(
            workspaces_table.c.resources_dir,
            workspaces_table.c.id,
            workspaces_table.c.gen_model,
            workspaces_table.c.embed_model,
        ).where(workspaces_table.c.name == workspace_name)

        row = conn.execute(query).fetchone()

        if row is not None:
            return (row[0], row[1], row[2], row[3])

        return None


def get_all_workspaces() -> dict[str, tuple[str, int]]:
    query = text("""
            SELECT 
                w.id, 
                w.name, 
                COUNT(DISTINCT u.group_id) as file_count
            FROM workspaces w
            LEFT JOIN upsertion_record u 
                ON u.namespace = 'chroma/' || w.id AND u.group_id IS NOT NULL
            GROUP BY w.id, w.name
        """)

    with _engine.connect() as conn:
        result = conn.execute(query)

        workspaces = {}
        for row in result:
            id_str = str(row[0])
            workspaces[id_str] = (str(row[1]), int(row[2]))

        return workspaces


def exists_workspace_by_name(workspace_name: str) -> bool:
    try:
        with _engine.connect() as conn:
            query = select(workspaces_table.c.id).where(
                workspaces_table.c.name == workspace_name
            )

            result = conn.execute(query).scalar()

            if result is not None:
                return True
            else:
                return False

    except Exception:
        print("Error checking name")
        return False


def exists_workspace_by_id(workspace_id: uuid.UUID) -> bool:
    try:
        with _engine.connect() as conn:
            query = select(workspaces_table.c.id).where(
                workspaces_table.c.id == str(workspace_id)
            )

            result = conn.execute(query).scalar()

            if result is not None:
                return True
            else:
                return False

    except Exception:
        print("Error checking name")
        return False


def add_workspace(workspace_name: str, id: uuid.UUID | None = None) -> uuid.UUID | None:
    try:
        if id is None:
            id = uuid.uuid4()

        value_to_insert = {
            "name": workspace_name,
            "id": str(id),
            "resources_dir": str(config.default_resources_dir),
            "gen_model": config.gen_model,
            "embed_model": config.embed_model,
        }

        with _engine.connect() as conn:
            query = sqlite_insert(workspaces_table).values(value_to_insert)

            conn.execute(query)
            conn.commit()

        return id
    except Exception as e:
        print(f"Failed to save configs: {e}")
        return None


def delete_workspace(workspace_id: str) -> bool:
    try:
        workspace_uuid = uuid.UUID(workspace_id)
        # check if the workspace exists
        if not exists_workspace_by_id(workspace_uuid):
            print("Workspace does not exist")
            return False

        try:
            # delete the embeddings
            tmp_vector_db = Chroma(
                collection_name=workspace_id,
                persist_directory=str(config.data_dir / "chroma_db"),
                embedding_function=config.embeddings,
            )

            tmp_vector_db.delete_collection()
        except Exception as e:
            print(f"Error deleting vector embeddings, might be empty {e}")

        with _engine.connect() as conn:
            with conn.begin():
                namespace = f"chroma/{workspace_id}"
                conn.execute(
                    text("DELETE FROM upsertion_record WHERE namespace = :ns"),
                    {"ns": namespace},
                )

                del_query = delete(workspaces_table).where(
                    workspaces_table.c.id == str(workspace_uuid)
                )
                conn.execute(del_query)

        return True

    except Exception as e:
        print(e)
        return False


def load_workspace_config(workspace_id: uuid.UUID) -> bool:
    try:
        with _engine.connect() as conn:
            query = select(
                workspaces_table.c.resources_dir,
                workspaces_table.c.gen_model,
                workspaces_table.c.embed_model,
            ).where(workspaces_table.c.id == str(workspace_id))

            row = conn.execute(query).fetchone()

            if row:
                config.workspace_id = workspace_id
                config.resources_dir = Path(row[0])
                config.gen_model = row[1]
                config.embed_model = row[2]

                clear_record_manager_cache()

                return True
            return False
    except Exception as e:
        print(f"Error loading workspace config: {e}")
        return False


def save_workspace_configs(
    resources_dir: str, gen_model: str, embed_model: str
) -> bool:
    try:
        with _engine.connect() as conn:
            with conn.begin():
                query = (
                    workspaces_table.update()
                    .where(workspaces_table.c.id == str(config.workspace_id))
                    .values(
                        resources_dir=resources_dir,
                        gen_model=gen_model,
                        embed_model=embed_model,
                    )
                )
                conn.execute(query)

        config.resources_dir = Path(resources_dir)
        config.gen_model = gen_model
        config.embed_model = embed_model

        return True
    except Exception as e:
        print(f"Error saving workspace configs: {e}")
        return False
