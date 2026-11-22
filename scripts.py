import argparse
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def initialize_schema():
    from database import engine

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    print("Task 1 - Create tables and constraints")
    print(f"SQL from {SCHEMA_PATH.name}:\n{schema_sql}")

    with engine.begin() as connection:
        connection.execution_options(no_parameters=True).exec_driver_sql(schema_sql)
        table_names = inspect(connection).get_table_names(schema="public")

    print(f"Task 1 complete. Schema committed; {len(table_names)} tables in public:")
    for table_name in table_names:
        print(f"  {table_name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser(
        "init-schema",
        help="Run task 1: drop existing assignment tables and recreate the schema.",
        description=(
            "Run schema.sql. Existing assignment tables and their data are deleted. "
            "Use a dedicated assignment database."
        ),
    )
    args = parser.parse_args()

    try:
        if args.command == "init-schema":
            initialize_schema()
    except SQLAlchemyError as exc:
        detail = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        parser.exit(1, f"Database operation failed: {detail}\n")
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"Setup error: {exc}\n")


if __name__ == "__main__":
    main()
