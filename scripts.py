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


def track_statistics(connection):
    # Task 6.1: authorship joins multiply papers, so count distinct IDs.
    return show_query(connection, "6.1 - Track statistics", """
        SELECT t.track_id, t.name AS track_name, t.conference_id,
               COUNT(DISTINCT p.paper_id) AS paper_count,
               COUNT(DISTINCT pa.author_id) AS author_count
        FROM track AS t
        LEFT JOIN paper AS p ON p.track_id = t.track_id
        LEFT JOIN paper_author AS pa ON pa.paper_id = p.paper_id
        GROUP BY t.track_id, t.name, t.conference_id
        ORDER BY t.track_id
    """, {})


def reviewer_statistics(connection):
    # Task 6.2: count review IDs rather than the outer join's empty row.
    return show_query(connection, "6.2 - Reviewer statistics", """
        SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
               COUNT(rv.review_id) AS review_count,
               AVG(rv.overall_score) AS average_overall_score
        FROM reviewer AS r
        JOIN app_user AS u ON u.user_id = r.reviewer_id
        LEFT JOIN review AS rv ON rv.reviewer_id = r.reviewer_id
        GROUP BY r.reviewer_id, u.given_name, u.surname
        ORDER BY r.reviewer_id
    """, {})


def conference_statistics(connection):
    # Task 6.3: count papers once while allowing every review into the average.
    return show_query(connection, "6.3 - Conference statistics", """
        SELECT c.conference_id, c.acronym,
               COUNT(DISTINCT p.paper_id) AS paper_count,
               COUNT(DISTINCT CASE WHEN p.status = :accepted THEN p.paper_id END)
                   AS accepted_count,
               AVG(rv.overall_score) AS average_overall_score
        FROM conference AS c
        LEFT JOIN track AS t ON t.conference_id = c.conference_id
        LEFT JOIN paper AS p ON p.track_id = t.track_id
        LEFT JOIN review AS rv ON rv.paper_id = p.paper_id
        GROUP BY c.conference_id, c.acronym
        ORDER BY c.conference_id
    """, {"accepted": "accepted"})


def above_average_reviewers(connection):
    # Task 6.4: build counts for ALL reviewers, including zero-review users.
    return show_query(connection, "6.4 - Above-average reviewers", """
        WITH review_counts AS (
            SELECT r.reviewer_id, COUNT(rv.review_id) AS review_count
            FROM reviewer AS r
            LEFT JOIN review AS rv ON rv.reviewer_id = r.reviewer_id
            GROUP BY r.reviewer_id
        ), overall AS (
            SELECT AVG(review_count) AS average_review_count FROM review_counts
        )
        SELECT rc.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
               rc.review_count, o.average_review_count
        FROM review_counts AS rc
        JOIN app_user AS u ON u.user_id = rc.reviewer_id
        CROSS JOIN overall AS o
        WHERE rc.review_count > o.average_review_count
        ORDER BY rc.reviewer_id
    """, {})


def run_complex_queries():
    from database import engine

    with engine.connect() as connection:
        track_statistics(connection)
        reviewer_statistics(connection)
        conference_statistics(connection)
        above_average_reviewers(connection)


def acceptance_rates(connection):
    # Task 7: only decisions enter the denominator; zero decisions yield NULL.
    return show_query(connection, "7 - Conference acceptance rates", """
        WITH decisions AS (
            SELECT c.conference_id, c.acronym,
                   COUNT(CASE WHEN p.status = :accepted THEN 1 END) AS accepted_count,
                   COUNT(CASE WHEN p.status = :rejected THEN 1 END) AS rejected_count
            FROM conference AS c
            LEFT JOIN track AS t ON t.conference_id = c.conference_id
            LEFT JOIN paper AS p ON p.track_id = t.track_id
            GROUP BY c.conference_id, c.acronym
        )
        SELECT conference_id, acronym, accepted_count, rejected_count,
               ROUND(100.0 * accepted_count /
                     NULLIF(accepted_count + rejected_count, 0), 2) AS acceptance_rate
        FROM decisions
        ORDER BY conference_id
    """, {"accepted": "accepted", "rejected": "rejected"})


def run_acceptance_rates():
    from database import engine

    with engine.connect() as connection:
        acceptance_rates(connection)


def scheduled_papers(connection):
    return show_query(connection, "8 - Query accepted_paper_schedule", """
        SELECT paper_id, paper_title, conference_id, acronym, track_name,
               session_id, session_title, session_date, start_time, end_time,
               room_label, chair_name, corresponding_author_name,
               corresponding_author_email
        FROM accepted_paper_schedule
        ORDER BY conference_id, session_date, start_time, session_id, paper_id
    """, {})


def run_schedule_view():
    from database import engine

    # Reuse the view definition in schema.sql; unlike its functions, this SELECT
    # definition has no internal semicolons. Do not run the schema's DROP commands.
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    start = schema_sql.index("CREATE VIEW accepted_paper_schedule AS")
    end = schema_sql.index(";", start) + 1
    view_sql = schema_sql[start:end].replace("CREATE VIEW", "CREATE OR REPLACE VIEW", 1)
    print("Task 8 - Create accepted_paper_schedule view")
    print(f"SQL:\n{view_sql}")
    with engine.begin() as connection:
        connection.exec_driver_sql(view_sql)
        print("Result: view created or replaced.")
        scheduled_papers(connection)
    print("Task 8 complete. View committed; paper data unchanged.")


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
    commands.add_parser("complex-queries", help="Run aggregate tasks 6.1-6.4.")
    commands.add_parser("acceptance-rates", help="Run task 7: conference acceptance rates.")
    commands.add_parser("schedule-view", help="Run task 8: create and query the schedule view.")
    args = parser.parse_args()

    try:
        if args.command == "init-schema":
            initialize_schema()
        elif args.command == "seed":
            populate_database()
        elif args.command == "simple-queries":
            run_simple_queries(args.paper_id, args.conference_id)
        elif args.command == "complex-queries":
            run_complex_queries()
        elif args.command == "acceptance-rates":
            run_acceptance_rates()
        elif args.command == "schedule-view":
            run_schedule_view()
    except SQLAlchemyError as exc:
        detail = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        parser.exit(1, f"Database operation failed: {detail}\n")
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"Setup error: {exc}\n")


if __name__ == "__main__":
    main()
