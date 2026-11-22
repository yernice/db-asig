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
