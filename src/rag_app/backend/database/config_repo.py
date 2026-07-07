from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from rag_app.backend.database.core import _engine, user_config_table


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
