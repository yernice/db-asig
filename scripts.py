import argparse
from pathlib import Path
from sqlalchemy import MetaData, Table, func, inspect, select, text
from sqlalchemy.exc import SQLAlchemyError
from database import engine

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"
SEED_PATH = SCHEMA_PATH.with_name("seed.sql")


def show_query(connection, task, sql, parameters):
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


def task_1():
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    print("Task 1 - Create tables and constraints")
    print(f"SQL from {SCHEMA_PATH.name}:\n{schema_sql}")

    with engine.begin() as connection:
        connection.execution_options(no_parameters=True).exec_driver_sql(schema_sql)
        table_names = inspect(connection).get_table_names(schema="public")

    print(f"Task 1 complete. Schema committed; {len(table_names)} tables in public:")
    for table_name in table_names:
        print(f"  {table_name}")


def task_2():
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


def task_3():
    # 3.1.
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            parameters = {"email": "arman.armanov@example.com"}
            snapshot_sql = """
                SELECT user_id, given_name, surname, email, phone_number
                FROM app_user WHERE email = :email
            """
            show_query(connection, "3.1 - Before phone update", snapshot_sql, parameters)
            show_query(connection, "3.1 - Update phone", """
                UPDATE app_user SET phone_number = :phone WHERE email = :email
                RETURNING user_id, email, phone_number
            """, {**parameters, "phone": "+77773414141"})
            show_query(connection, "3.1 - After phone update", snapshot_sql, parameters)
        finally:
            transaction.rollback()
            print("Task 3.1: ROLLBACK complete; demonstration changes were not saved.")

    # 3.2
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            snapshot_sql = """
                SELECT conference_id, acronym, city, review_deadline
                FROM conference ORDER BY conference_id
            """
            show_query(connection, "3.2 - Before deadline update", snapshot_sql, {})
            show_query(connection, "3.2 - Conditional deadline update", """
                UPDATE conference
                SET review_deadline = review_deadline +
                    CASE WHEN city = :city THEN :astana_days ELSE :other_days END
                RETURNING conference_id, acronym, city, review_deadline
            """, {"city": "Astana", "astana_days": 7, "other_days": 3})
            show_query(connection, "3.2 - After deadline update", snapshot_sql, {})
        finally:
            transaction.rollback()
            print("Task 3.2: ROLLBACK complete; demonstration changes were not saved.")


def task_4():
    # 4.1
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            parameters = {"email": "amina.aminova@example.com", "status": "withdrawn"}
            target_condition = """
                p.status = :status AND EXISTS (
                    SELECT 1 FROM paper_author AS pa
                    JOIN app_user AS u ON u.user_id = pa.author_id
                    WHERE pa.paper_id = p.paper_id AND pa.is_corresponding AND u.email = :email
                )
            """
            targets = show_query(connection, "4.1 - Before: matching withdrawn papers",
                                 f"SELECT p.paper_id, p.title FROM paper AS p WHERE {target_condition} ORDER BY p.paper_id",
                                 parameters)
            paper_ids = [row["paper_id"] for row in targets]
            counts_sql = """
                SELECT 'paper' AS table_name, COUNT(*) AS row_count
                FROM paper WHERE paper_id = ANY(:paper_ids)
                UNION ALL
                SELECT 'paper_author', COUNT(*) FROM paper_author WHERE paper_id = ANY(:paper_ids)
                UNION ALL
                SELECT 'paper_keyword', COUNT(*) FROM paper_keyword WHERE paper_id = ANY(:paper_ids)
                UNION ALL
                SELECT 'paper_version', COUNT(*) FROM paper_version WHERE paper_id = ANY(:paper_ids)
                UNION ALL
                SELECT 'review', COUNT(*) FROM review WHERE paper_id = ANY(:paper_ids)
            """
            papers_sql = "SELECT paper_id, title, status FROM paper ORDER BY paper_id"
            protected_sql = """
                SELECT (SELECT COUNT(*) FROM app_user) AS user_count,
                       (SELECT COUNT(*) FROM track) AS track_count,
                       (SELECT COUNT(*) FROM conference) AS conference_count
            """
            show_query(connection, "4.1 - Before: targeted rows and dependents", counts_sql, {"paper_ids": paper_ids})
            show_query(connection, "4.1 - Before: papers", papers_sql, {})
            show_query(connection, "4.1 - Before: protected records", protected_sql, {})
            
            show_query(connection, "4.1 - Delete withdrawn papers",
                       f"DELETE FROM paper AS p WHERE {target_condition} RETURNING p.paper_id, p.title",
                       parameters)
            show_query(connection, "4.1 - After: targeted rows and dependents", counts_sql, {"paper_ids": paper_ids})
            show_query(connection, "4.1 - After: papers", papers_sql, {})
            show_query(connection, "4.1 - After: protected records", protected_sql, {})
        finally:
            transaction.rollback()
            print("Task 4.1: ROLLBACK complete; demonstration changes were not saved.")

    # 4.2
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            snapshot_sql = """
                SELECT s.session_id, s.title, c.conference_id, c.city,
                       COUNT(p.paper_id) AS assigned_paper_count
                FROM conference_session AS s
                JOIN conference AS c ON c.conference_id = s.conference_id
                LEFT JOIN paper AS p ON p.session_id = s.session_id
                GROUP BY s.session_id, s.title, c.conference_id, c.city
                ORDER BY s.session_id
            """
            conferences_sql = "SELECT conference_id, acronym FROM conference ORDER BY conference_id"
            show_query(connection, "4.2 - Before: sessions", snapshot_sql, {})
            show_query(connection, "4.2 - Before: conferences", conferences_sql, {})
            show_query(connection, "4.2 - Delete empty Astana sessions", """
                DELETE FROM conference_session AS s
                USING conference AS c
                WHERE c.conference_id = s.conference_id AND c.city = :city
                  AND NOT EXISTS (SELECT 1 FROM paper AS p WHERE p.session_id = s.session_id)
                RETURNING s.session_id, s.title, s.conference_id
            """, {"city": "Astana"})
            show_query(connection, "4.2 - After: sessions", snapshot_sql, {})
            show_query(connection, "4.2 - After: conferences", conferences_sql, {})
        finally:
            transaction.rollback()
            print("Task 4.2: ROLLBACK complete; demonstration changes were not saved.")


def task_5(paper_id=1, conference_id=1):
    with engine.connect() as connection:
        # 5.1
        show_query(connection, "5.1 - Accepted papers", """
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

        # 5.2
        show_query(connection, "5.2 - Abstract search", """
            SELECT paper_id, title
            FROM paper
            WHERE abstract ILIKE :pattern
            ORDER BY paper_id
        """, {"pattern": "%machine learning%"})

        # 5.3
        show_query(connection, "5.3 - Paper versions", """
            SELECT version_no, file_location, uploaded_at
            FROM paper_version
            WHERE paper_id = :paper_id
            ORDER BY version_no DESC
        """, {"paper_id": paper_id})

        # 5.4
        show_query(connection, "5.4 - Conference reviewers", """
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


def task_6():
    with engine.connect() as connection:
        # 6.1
        show_query(connection, "6.1 - Track statistics", """
            SELECT t.track_id, t.name AS track_name, t.conference_id,
                   COUNT(DISTINCT p.paper_id) AS paper_count,
                   COUNT(DISTINCT pa.author_id) AS author_count
            FROM track AS t
            LEFT JOIN paper AS p ON p.track_id = t.track_id
            LEFT JOIN paper_author AS pa ON pa.paper_id = p.paper_id
            GROUP BY t.track_id, t.name, t.conference_id
            ORDER BY t.track_id
        """, {})

        # 6.2
        show_query(connection, "6.2 - Reviewer statistics", """
            SELECT r.reviewer_id, u.given_name || ' ' || u.surname AS full_name,
                   COUNT(rv.review_id) AS review_count,
                   AVG(rv.overall_score) AS average_overall_score
            FROM reviewer AS r
            JOIN app_user AS u ON u.user_id = r.reviewer_id
            LEFT JOIN review AS rv ON rv.reviewer_id = r.reviewer_id
            GROUP BY r.reviewer_id, u.given_name, u.surname
            ORDER BY r.reviewer_id
        """, {})

        # 6.3
        show_query(connection, "6.3 - Conference statistics", """
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

        # 6.4
        show_query(connection, "6.4 - Above-average reviewers", """
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


def task_7():
    with engine.connect() as connection:
        show_query(connection, "7 - Conference acceptance rates", """
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


def task_8():
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    start = schema_sql.index("CREATE VIEW accepted_paper_schedule AS")
    end = schema_sql.index(";", start) + 1
    view_sql = schema_sql[start:end].replace("CREATE VIEW", "CREATE OR REPLACE VIEW", 1)
    print("Task 8 - Create accepted_paper_schedule view")
    print(f"SQL:\n{view_sql}")
    with engine.begin() as connection:
        connection.exec_driver_sql(view_sql)
        print("Result: view created or replaced.")
        show_query(connection, "8 - Query accepted_paper_schedule", """
            SELECT paper_id, paper_title, conference_id, acronym, track_name,
                   session_id, session_title, session_date, start_time, end_time,
                   room_label, chair_name, corresponding_author_name,
                   corresponding_author_email
            FROM accepted_paper_schedule
            ORDER BY conference_id, session_date, start_time, session_id, paper_id
        """, {})
    print("Task 8 complete. View committed; paper data unchanged.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("task-1", help="Create schema; drops existing assignment tables and data.")
    commands.add_parser("task-2", help="Load seed.sql into empty tables and show counts.")
    commands.add_parser("task-3", help="Show updates 3.1-3.2; roll back each change.")
    commands.add_parser("task-4", help="Show deletions 4.1-4.2; roll back each change.")
    task_5_parser = commands.add_parser("task-5", help="Run simple queries 5.1-5.4.")
    task_5_parser.add_argument("--paper-id", type=int, default=1, help="Paper for 5.3 (default: 1).")
    task_5_parser.add_argument("--conference-id", type=int, default=1, help="Conference for 5.4 (default: 1).")
    commands.add_parser("task-6", help="Run aggregate queries 6.1-6.4.")
    commands.add_parser("task-7", help="Calculate conference acceptance rates.")
    commands.add_parser("task-8", help="Create and query the schedule view.")
    args = parser.parse_args()

    try:
        if args.command == "task-1":
            task_1()
        elif args.command == "task-2":
            task_2()
        elif args.command == "task-3":
            task_3()
        elif args.command == "task-4":
            task_4()
        elif args.command == "task-5":
            task_5(args.paper_id, args.conference_id)
        elif args.command == "task-6":
            task_6()
        elif args.command == "task-7":
            task_7()
        elif args.command == "task-8":
            task_8()
    except SQLAlchemyError as exc:
        detail = str(exc.orig) if getattr(exc, "orig", None) else str(exc)
        parser.exit(1, f"Database operation failed: {detail}\n")
    except (OSError, RuntimeError) as exc:
        parser.exit(1, f"Setup error: {exc}\n")


if __name__ == "__main__":
    main()
