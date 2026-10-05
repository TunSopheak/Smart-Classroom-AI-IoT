from sqlalchemy import inspect, text

from app.database.database import engine


# Columns added to class_sessions after the first release. create_all() does
# not alter existing tables, so older SQLite databases get them here.
CLASS_SESSION_COLUMNS = {
    "class_group_id": "INTEGER",
    "course_id": "INTEGER",
    "weekly_schedule_id": "INTEGER",
    "archived": "BOOLEAN NOT NULL DEFAULT 0",
}


def apply_schema_migrations() -> None:
    """Add missing columns to existing tables. Safe to run on every startup."""
    inspector = inspect(engine)
    if "class_sessions" not in inspector.get_table_names():
        return

    existing_columns = {column["name"] for column in inspector.get_columns("class_sessions")}

    with engine.begin() as connection:
        for column_name, column_type in CLASS_SESSION_COLUMNS.items():
            if column_name not in existing_columns:
                connection.execute(
                    text(f"ALTER TABLE class_sessions ADD COLUMN {column_name} {column_type}")
                )
