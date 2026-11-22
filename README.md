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

## Tasks 3 and 4: Update and delete demonstrations

Run these against the original root seed dataset. If records have changed, restore
the seed using Task 2's instructions first. These commands do not reset the database.

```bash
./.venv/Scripts/python.exe scripts.py updates
./.venv/Scripts/python.exe scripts.py deletions
```

Each operation prints its task number, SQL, bound inputs, before/after results,
and the affected rows using PostgreSQL `RETURNING`. Each runs in a separate
transaction that always rolls back, including if an operation fails. The displayed
after-state is temporary; the next task and later queries see the original data.
There is no commit option for these demonstration commands.

Expected checks using the root seed:

| Task | Before | Temporary after-state |
| --- | --- | --- |
| 3.1 | Arman, identified by `arman.armanov@example.com`, has phone `+77010000001`. | Phone becomes `+77773414141`; one user is affected. |
| 3.2 | Conference IDs 1, 2, 3 have review deadlines `2026-11-15`, `2026-12-01`, `2027-05-15`. | One conditional UPDATE changes them to `2026-11-22` (Astana, +7 days), `2026-12-04`, `2027-05-18` (elsewhere, +3 days). |
| 4.1 | Amina (`amina.aminova@example.com`) is corresponding author of withdrawn papers 7 and 8. Their dependent counts are 4 authorship rows, 3 keywords, 2 versions, and 1 review. | Both papers and all those dependent rows disappear through foreign-key cascades. Papers 1-6, 9, 10 remain, along with all 10 users, 5 tracks, and 3 conferences. |
| 4.2 | Session 2 is empty and in Astana. Sessions 1 and 3 have papers; session 4 is empty but outside Astana. | Only session 2 disappears. Sessions 1, 3, 4 and all conferences remain. |

After each operation, look for `ROLLBACK complete`. Running the same commands again
should show the same before-state and affected rows. Task 4.1 prints dependent-row
counts using the original target paper IDs, so the after-counts must all be zero.
An empty match prints zero affected rows; use the original seed for grading so
each required operation affects the intended records.

## Tasks 5.1-5.4: Simple retrieval queries

After loading the original seed, run in Git Bash:

```bash
./.venv/Scripts/python.exe scripts.py simple-queries
```

This runs all four queries, printing each task number, SQL, bound parameter values,
column names, results, and returned row count. It only reads existing data; it does
not recreate tables or load the seed. If you have edited data through the web app,
restore the seed using the Task 2 instructions before the assignment demonstration.

Expected results for the root seed dataset:

| Task | Inputs | Expected result |
| --- | --- | --- |
| 5.1 | Status `accepted` | Papers 1, 2, 3, 9, each with its corresponding author, track, and conference. Includes unscheduled paper 3. |
| 5.2 | Case-insensitive phrase `machine learning` | Paper 6, whose abstract contains `MACHINE LEARNING`. |
| 5.3 | Paper ID `1` | Versions 3 then 1, including file locations and upload timestamps. |
| 5.4 | Conference ID `1`, expertise `Databases`, minimum experience `3` | Reviewers 1, 4, 10, each once. |

Choose different paper/conference IDs with arguments:

```bash
./.venv/Scripts/python.exe scripts.py simple-queries --paper-id 2 --conference-id 2
```

For those IDs, task 5.3 returns version 1 of paper 2, and task 5.4 returns reviewer 4.
Tasks 5.1 and 5.2 keep their assignment-defined filters. A selection with no matches
prints the column names and a zero row count.

## Tasks 6, 7, and 8: Aggregates, acceptance rates, and schedule view

Use the original root seed dataset for these checks. If you have edited records,
restore it using Task 2's instructions first (restoration deletes existing data).
Each command prints its numbered SQL, bound parameters, columns, and results.

### Task 6: Aggregate queries

```bash
./.venv/Scripts/python.exe scripts.py complex-queries
```

Check each numbered section:

| Task | Expected result |
| --- | --- |
| 6.1 | Track IDs 1-5 have `(paper_count, author_count)` of `(5, 5)`, `(3, 4)`, `(0, 0)`, `(2, 4)`, `(0, 0)`. Authors appearing on multiple papers in a track count once. |
| 6.2 | Reviewer IDs `1, 4, 5, 6, 7, 8, 10` have review counts `1, 3, 1, 3, 0, 1, 1`; their average scores are `3`, approximately `4.6667`, `2`, `3`, `NULL`, `4`, `5`. |
| 6.3 | Conference 1: 8 papers, 3 accepted, mean score `26/7` (approximately `3.7143`). Conference 2: 2 papers, 1 accepted, mean score `11/3` (approximately `3.6667`). Conference 3: 0 papers, 0 accepted, `NULL` mean. |
| 6.4 | Only reviewers 4 and 6, each with 3 reviews. The overall mean count is `10/7` (approximately `1.4286`), including zero-review reviewer 7. |

Tasks 6.2-6.4 print PostgreSQL's numeric averages without rounding them.

### Task 7: Derived acceptance rate

```bash
./.venv/Scripts/python.exe scripts.py acceptance-rates
```

| Conference ID | Acronym | Accepted | Rejected | Acceptance rate (%) |
| --- | --- | --- | --- | --- |
| 1 | SRCML | 3 | 1 | 75.00 |
| 2 | SVR | 1 | 1 | 50.00 |
| 3 | TWDMC | 0 | 0 | NULL |

The denominator includes only accepted and rejected papers. These commands read
existing data and do not seed, reset, or update it.

### Task 8: Create and query the view

```bash
./.venv/Scripts/python.exe scripts.py schedule-view
```

This creates or replaces the real database view `accepted_paper_schedule`, using
its definition from `schema.sql`, and queries it. It does not run the rest of the
schema file or change paper data. It can recreate the view if it is missing.

Expect paper IDs `1, 2, 9`, in that order, assigned to session IDs `1, 1, 3`.
Accepted paper 3 must be absent because it has no session. Each row includes the
paper and conference details, track, session title/date/times/room, chair name,
and corresponding author's name/email. Ordering is by conference ID, session
date, start time, session ID, then paper ID. In pgAdmin, refresh
**Schemas > public > Views** to see the view; no schedule result table is created.
