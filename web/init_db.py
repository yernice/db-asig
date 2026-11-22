"""
Create and populate the database (schema + seed) without needing psql.

Usage:
    DATABASE_URL="postgresql://user:pass@host/db?sslmode=require" python init_db.py
    DATABASE_URL=... python init_db.py db/schema.sql path/to/team_seed.sql

With no file arguments it runs db/schema.sql and then db/sample_seed.sql.
WARNING: schema.sql drops and recreates every table, so all data is reset.
"""
import os
import sys

import psycopg2

files = sys.argv[1:] or ["db/schema.sql", "db/sample_seed.sql"]
url = os.environ.get("DATABASE_URL")
if not url:
    sys.exit("Set DATABASE_URL first.")

with psycopg2.connect(url) as conn, conn.cursor() as cur:
    for path in files:
        with open(path, encoding="utf-8") as f:
            cur.execute(f.read())
        print(f"ran {path}")
    for table in ["app_user", "author", "reviewer", "conference", "track", "conference_session",
                  "paper", "paper_author", "paper_version", "review"]:
        cur.execute(f"SELECT count(*) FROM {table}")
        print(f"  {table:20} {cur.fetchone()[0]} rows")
print("done")
