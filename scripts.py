import argparse
from pathlib import Path

from sqlalchemy import MetaData, Table, func, inspect, select
from sqlalchemy.exc import SQLAlchemyError


SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SEED_PATH = SCHEMA_PATH.with_name("seed.sql")


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


def populate_database():
    """Run task 2, loading the shared seed and reporting every table's count."""
    from database import engine

    # The SQL file also works standalone. Let SQLAlchemy own its transaction here
    # so the inserts and row-count checks commit together.
    seed_lines = SEED_PATH.read_text(encoding="utf-8").strip().splitlines()
    if (
        not seed_lines
        or seed_lines[0].strip().upper() != "BEGIN;"
        or seed_lines[-1].strip().upper() != "COMMIT;"
    ):
        raise RuntimeError("Expected seed.sql to be wrapped in BEGIN; and COMMIT;.")
    seed_sql = "\n".join(seed_lines[1:-1])

    print("Task 2 - Insert sample data")
    print(f"SQL from {SEED_PATH.name}:\n{seed_sql}")
    counts = []
    with engine.begin() as connection:
        connection.execution_options(no_parameters=True).exec_driver_sql(seed_sql)
        metadata = MetaData()
        for name in inspect(connection).get_table_names(schema="public"):
            table = Table(name, metadata, schema="public")
            statement = select(func.count()).select_from(table)
            print(f"SQL: {statement.compile(dialect=connection.dialect)}")
            count = connection.execute(statement).scalar_one()
            counts.append((name, count))
            print(f"Result: {name} = {count} rows")

    print(f"Task 2 complete. Seed committed; counted {len(counts)} tables.")


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
    commands.add_parser(
        "seed",
        help="Run task 2: insert seed.sql and print every table's row count.",
        description=(
            "Load seed.sql into the empty assignment tables created by init-schema. "
            "To restore the seed dataset, run init-schema followed by seed."
        ),
    )
    args = parser.parse_args()

    try:
        if args.command == "init-schema":
            initialize_schema()
        elif args.command == "seed":
            populate_database()
    except SQLAlchemyError as exc:
        detail = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        parser.exit(1, f"Database operation failed: {detail}\n")
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"Setup error: {exc}\n")


if __name__ == "__main__":
    main()
