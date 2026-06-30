from sqlalchemy import inspect, text

from app.database.database import engine


def ensure_phase_16_2_schema() -> None:
    """Safe SQLite-friendly migration for nullable ClassSession bridge columns."""
    inspector = inspect(engine)
    if "class_sessions" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("class_sessions")}
    columns_to_add = {
        "class_group_id": "INTEGER",
        "course_id": "INTEGER",
        "weekly_schedule_id": "INTEGER",
    }

    with engine.begin() as connection:
        for column_name, column_type in columns_to_add.items():
            if column_name not in existing_columns:
                connection.execute(text(f"ALTER TABLE class_sessions ADD COLUMN {column_name} {column_type}"))


# Phase 16.2.2 safe migration: archived sessions
def ensure_session_archived_column(engine):
    with engine.connect() as connection:
        columns = connection.exec_driver_sql("PRAGMA table_info(class_sessions)").fetchall()
        column_names = {column[1] for column in columns}

        if "archived" not in column_names:
            connection.exec_driver_sql(
                "ALTER TABLE class_sessions ADD COLUMN archived BOOLEAN NOT NULL DEFAULT 0"
            )
            connection.commit()
