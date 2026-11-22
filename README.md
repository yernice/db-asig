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
