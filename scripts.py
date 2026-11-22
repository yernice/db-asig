import argparse
from pathlib import Path

from sqlalchemy import MetaData, Table, func, inspect, select, text
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


def show_query(connection, task, sql, parameters):
    """Print a numbered query, its bound inputs, and its result rows."""
    statement = text(sql.strip())
    print(f"\nTask {task}")
    print(f"SQL:\n{statement}")
    print(f"Parameters: {parameters}")
    result = connection.execute(statement, parameters)
    print(" | ".join(result.keys()))
    rows = result.mappings().all()
    for row in rows:
        print(" | ".join("NULL" if value is None else str(value) for value in row.values()))
    print(f"Result: {len(rows)} row(s)")
    return rows


def accepted_papers(connection):
    # Task 5.1: join only the corresponding author to keep one row per paper.
    return show_query(connection, "5.1 - Accepted papers", """
        SELECT p.paper_id, p.title,
               u.given_name || ' ' || u.surname AS corresponding_author_name,
               u.email AS corresponding_author_email,
               t.name AS track_name, c.conference_id, c.acronym
        FROM paper AS p
        JOIN paper_author AS pa ON pa.paper_id = p.paper_id AND pa.is_corresponding
        JOIN app_user AS u ON u.user_id = pa.author_id
        JOIN track AS t ON t.track_id = p.track_id
        JOIN conference AS c ON c.conference_id = t.conference_id
        WHERE p.status = :status
        ORDER BY p.paper_id
    """, {"status": "accepted"})


def machine_learning_papers(connection):
    # Task 5.2: PostgreSQL ILIKE performs the case-insensitive search in SQL.
    return show_query(connection, "5.2 - Abstract search", """
        SELECT paper_id, title
        FROM paper
        WHERE abstract ILIKE :pattern
        ORDER BY paper_id
    """, {"pattern": "%machine learning%"})


def paper_versions(connection, paper_id):
    # Task 5.3: version numbers can have gaps; highest number comes first.
    return show_query(connection, "5.3 - Paper versions", """
        SELECT version_no, file_location, uploaded_at
        FROM paper_version
        WHERE paper_id = :paper_id
        ORDER BY version_no DESC
    """, {"paper_id": paper_id})


def conference_reviewers(connection, conference_id):
    # Task 5.4: EXISTS filters membership and expertise without multiplying rows.
    return show_query(connection, "5.4 - Conference reviewers", """
        SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name, u.email
        FROM reviewer AS r
        JOIN app_user AS u ON u.user_id = r.reviewer_id
        WHERE r.years_experience >= :minimum_experience
          AND EXISTS (
              SELECT 1 FROM conference_reviewer AS cr
              WHERE cr.reviewer_id = r.reviewer_id AND cr.conference_id = :conference_id
          )
          AND EXISTS (
              SELECT 1 FROM reviewer_expertise AS re
              WHERE re.reviewer_id = r.reviewer_id AND re.area_label = :expertise
          )
        ORDER BY r.reviewer_id
    """, {"conference_id": conference_id, "expertise": "Databases", "minimum_experience": 3})


def run_simple_queries(paper_id, conference_id):
    """Run tasks 5.1-5.4 without creating, seeding, or changing database records."""
    from database import engine

    with engine.connect() as connection:
        accepted_papers(connection)
        machine_learning_papers(connection)
        paper_versions(connection, paper_id)
        conference_reviewers(connection, conference_id)


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
    simple_queries = commands.add_parser(
        "simple-queries",
        help="Run retrieval tasks 5.1-5.4 against the existing data.",
        description="Run tasks 5.1-5.4. Restore the original seed before demonstrating queries.",
    )
    simple_queries.add_argument(
        "--paper-id", type=int, default=1,
        help="Paper for task 5.3 (default: 1, with seed versions 3 and 1).",
    )
    simple_queries.add_argument(
        "--conference-id", type=int, default=1,
        help="Conference pool for task 5.4 (default: 1).",
    )
    args = parser.parse_args()

    try:
        if args.command == "init-schema":
            initialize_schema()
        elif args.command == "seed":
            populate_database()
        elif args.command == "simple-queries":
            run_simple_queries(args.paper_id, args.conference_id)
    except SQLAlchemyError as exc:
        detail = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        parser.exit(1, f"Database operation failed: {detail}\n")
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"Setup error: {exc}\n")


if __name__ == "__main__":
    main()
