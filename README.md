# DB Assignment 3

Authors: Olzhas, Nurislam, Yernar

## Local setup

Use Python 3.10 or newer and a running PostgreSQL server.

Create a virtual environment and install the shared dependencies (PowerShell):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

SQLAlchemy provides database access; psycopg is the PostgreSQL driver. The
binary extra includes its client libraries, so no compiler is required.
PostgreSQL itself must be installed or hosted separately.

Set the connection URL in each terminal before running project code:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://postgres:password@localhost:5432/db_assignment"
```

Replace the example credentials and database name with your own. Create that
database in PostgreSQL first. The URL is read from the environment, not a .env file.

Check that the shared setup imports successfully:

```powershell
.\.venv\Scripts\python.exe -c "from database import engine, SessionLocal; print('Database setup loaded')"
```

This checks dependency loading and URL parsing; it does not connect to PostgreSQL
or create tables. Scripts and the web app should import `engine` or `SessionLocal`
from `database.py`. Add the web framework dependency when the team selects one.

## Task 1: Create the database schema

In Git Bash, set your own PostgreSQL connection details, then run:

```bash
export DATABASE_URL='postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/db-assignment'
./.venv/Scripts/python.exe scripts.py init-schema
```

The database named in the URL must already exist. Use your actual database name.
This command runs `schema.sql`, which drops existing assignment tables and their
data, then recreates the tables, constraints, indexes, view, functions, and triggers.
Use a dedicated assignment database. It does not insert seed data.

The script prints the task number, SQL, and resulting table names. Changes commit
only if the whole operation succeeds; a failure rolls back the transaction.
The SQL file is located relative to `scripts.py`, independent of the current directory.
Importing `scripts.py` or requesting `--help` does not run the schema or require
`DATABASE_URL`.

## Task 2: Insert the sample data

After creating the schema, run in Git Bash:

```bash
./.venv/Scripts/python.exe scripts.py seed
```

This loads the team's root `seed.sql` through Python and SQLAlchemy. It prints the
task number, seed SQL, and each table's count query and result (all 15 tables).
Inserts and count checks run in one transaction; a failure rolls back the inserted
rows. PostgreSQL sequence counters may still advance after a failed transaction.
The script leaves `seed.sql` unchanged and omits its outer `BEGIN`/`COMMIT` when
executing it, so SQLAlchemy controls the transaction.

Run `seed` once on empty tables. Running it again on populated tables fails on
existing keys; it does not silently overwrite data. Use this sequence to restore
the original dataset before independent assignment demonstrations:

```bash
./.venv/Scripts/python.exe scripts.py init-schema &&
./.venv/Scripts/python.exe scripts.py seed
```

Restoring deletes existing assignment data. These commands use the database in
`DATABASE_URL` and do not create a PostgreSQL database. Use the root `seed.sql`
for the final assignment dataset; `web/db/sample_seed.sql` is a separate sample.
