# CSCI 341 - Assignment 3

Research Conference and Paper Review Management System, Fall 2026.

## Team and contributions

| Given name | Surname | Student ID | Contribution |
| --- | --- | --- | --- |
| Olzhas | Sabyrzhan | 202432854 | Part 1 |
| Yernar | Duzelbay | 202217878 | Part 2 |
| Nurislam | Zhanibek | 202361729 | Part 3 |

## Software and versions

Use PostgreSQL, not SQLite or MySQL, because the supplied SQL uses PostgreSQL-specific features.

| Component | Version or configuration |
| --- | --- |
| Part 2 Python | Python 3.14.3; Python 3.10 or newer is required by the selected driver series. |
| Part 2 SQLAlchemy | `>=2.0,<2.1` |
| Part 2 PostgreSQL driver | `psycopg[binary]>=3.3,<4` |
| PostgreSQL | 18 |
| Web dependencies | Flask 3.1.3, SQLAlchemy 2.1.9, psycopg2-binary 2.9.13, gunicorn 27.0.1, as pinned in `web/requirements.txt`. |
| Hosted Python | 3.13.1 in `render.yaml`. Gunicorn is used on the Linux host; use `python web/app.py` locally. |

The root and web requirements select different SQLAlchemy/driver versions. Install them in separate virtual environments.

## Local setup for Part 2

The following commands use Git Bash on Windows from the repository root. On Linux/macOS, use `.venv/bin/python` instead of `./.venv/Scripts/python.exe`.

```bash
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.txt
```

Create an empty database named `db-assignment` in pgAdmin/DBeaver, or use PostgreSQL command-line tools:

Set connection details in the current terminal; substitute your own password and database name:

```bash
export DATABASE_URL='postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/db-assignment'
```

## Create, seed, and restore the original dataset

```bash
./.venv/Scripts/python.exe scripts.py task-1 &&
./.venv/Scripts/python.exe scripts.py task-2
```

Task 1 runs `schema.sql` and task 2 runs `seed.sql`. 

## Run Part 2

Commands for other tasks are ran in the same manner: 

```bash
./.venv/Scripts/python.exe scripts.py task-i
```

`i` - number of the task (3 to 8).

Task 5 also have additional variables `--paper-id` and `--conference-id`. They are set to 1 by default. You can change them as following:

```bash
./.venv/Scripts/python.exe scripts.py task-5 --paper-id 3 --conference-id 5
```

Tasks 3 and 4 make real changes inside separate transactions, print the temporary after-state, and always roll back, including on failure.

## Run the web application locally

First create/load the database with root tasks 1 and 2 above. Then install the web dependencies in a separate environment:

```bash
python -m venv web/.venv
./web/.venv/Scripts/python.exe -m pip install -r web/requirements.txt
export DATABASE_URL='postgresql+psycopg2://postgres:YOUR_PASSWORD@localhost:5432/db-assignment'
export SECRET_KEY='replace-with-a-local-random-secret'
./web/.venv/Scripts/python.exe web/app.py
```

Open `http://127.0.0.1:5000`. On Linux/macOS, use `web/.venv/bin/python`. The `psycopg2` URL matches the web driver's dependencies. Before returning to Part 2 commands, set the URL back to `postgresql+psycopg://...` for the root environment.

The web app has its own engine configuration rather than importing root `database.py`. When no URL is supplied, it defaults to a local database named `conference`; explicitly setting the URL avoids connecting to a different database accidentally.

Users, papers, reviews, and sessions have CRUD workflows. User forms manage author/reviewer profiles; paper workflows manage authorship, keywords, and versions. Conferences, tracks, pools, hosts, and labels are supporting selection/read-only data. The schedule page queries the database view.

The hosted application uses Render and persistent PostgreSQL on Neon, as described in `web/README.md` and `render.yaml`. Its database can be separate from the local demonstration database. Changes are shared only when both clients target the same database; there is no automatic local/hosted synchronization. Keep hosting available during grading. Put the actual application/video URLs in `links.txt`; those URLs are not supplied in the repository at the time of this documentation update.

### Web demonstration checks with the final seed

1. Create, read, edit, and delete temporary users, papers, reviews, and sessions. Include role profiles, paper authorship/keywords, and an additional paper version. Refresh the lists to confirm persistence.
2. Try to create a review of paper 9 by reviewer 5 (Arman): he authored that paper, so the operation must be rejected with no review saved.
3. Try to assign submitted paper 6 to session 1: the operation must be rejected because the paper is not accepted.
4. Try to assign accepted paper 1 to session 3: the operation must be rejected because the track and session belong to different conferences.
5. Show the schedule page and confirm paper 3 is absent while it has no session. Keep the original seed or restore it before returning to Part 2 demonstrations.

These IDs refer to root `seed.sql`, not the separate sample used by default in `web/init_db.py`.

## Relational schema: keys and references

Names below match `schema.sql`. Composite keys are shown in parentheses. Nonoptional attributes are `NOT NULL`; optional attributes are `author.orcid`, `paper.session_id`, `paper_version.change_note`, and `review.confidential_comments`.

| Relation | Primary key | Foreign keys and notable uniqueness |
| --- | --- | --- |
| `app_user` | `user_id` | Unique `email`. |
| `author` | `author_id` | Also references `app_user.user_id`. |
| `author_research_area` | `(author_id, area_label)` | `author_id` -> `author.author_id`. |
| `reviewer` | `reviewer_id` | Also references `app_user.user_id`. |
| `reviewer_expertise` | `(reviewer_id, area_label)` | `reviewer_id` -> `reviewer.reviewer_id`. |
| `conference` | `conference_id` | Unique `acronym`. |
| `conference_host` | `(conference_id, host_name)` | `conference_id` -> `conference.conference_id`. |
| `conference_reviewer` | `(conference_id, reviewer_id)` | References `conference` and `reviewer`. |
| `track` | `track_id` | References `conference`; coordinator -> `reviewer`; `(conference_id, coordinator_id)` -> `conference_reviewer`; unique `(conference_id, name)`. |
| `conference_session` | `session_id` | References `conference`; chair -> `reviewer`; `(conference_id, chair_id)` -> `conference_reviewer`. |
| `paper` | `paper_id` | `track_id` -> `track.track_id`; nullable `session_id` -> `conference_session.session_id`. |
| `paper_keyword` | `(paper_id, keyword)` | References `paper`. |
| `paper_author` | `(paper_id, author_id)` | References `paper` and `author`; unique `(paper_id, author_position)`; partial unique index permits at most one corresponding author per paper. |
| `paper_version` | `(paper_id, version_no)` | References `paper`. |
| `review` | `review_id` | References `paper` and `reviewer`; unique `(paper_id, reviewer_id)`. |

Surrogate IDs use PostgreSQL `SERIAL`. Author/reviewer IDs reuse their user's ID; a user can have both roles. Research/expertise labels, keywords, and host names are stored in separate relations rather than comma-separated fields.

### Required database constraints and application checks

- Primary/foreign keys, required fields, unique user emails, unique author positions, and one review per reviewer/paper are enforced in PostgreSQL.
- CHECK constraints enforce the five statuses (`submitted`, `under review`, `accepted`, `rejected`, `withdrawn`), integer scores 1-5, `accept`/`reject` recommendations, positive positions/version numbers, nonnegative experience, conference end >= start, and session end > start. Email has a basic `@` check; optional ORCID has a format check.
- A paper has at most one session through its single nullable `session_id`. A CHECK also requires a scheduled paper to be accepted.
- Self-reviews are rejected on review inserts/changes and paper-author changes: application checks plus `review_no_self_review` and `author_not_reviewer` triggers.
- Session assignments require an accepted paper and matching track/session conferences. Application checks and `paper_session_valid` enforce paper status/track/session changes. `session_conference_change` and `track_conference_change` protect later conference reassignment.
- Related web changes run in one transaction. Validation and database failures are reported to the user; partial writes are rolled back.

### Optional business-rule enforcement

| Rule | Enforcement |
| --- | --- |
| Every user has at least one author/reviewer role | Web user workflow; seed satisfies it. Direct SQL does not enforce minimum role membership. |
| Every paper has authors and exactly one corresponding author | Web paper workflow; seed satisfies it. Database enforces at most one corresponding author, not a minimum. |
| Every paper has at least one version | Web creation inserts version 1; deletion of its last version is rejected. Direct SQL does not enforce minimum version count. |
| Track coordinator and session chair belong to the conference reviewer pool | Composite database foreign keys; the web session workflow also checks the chair. |
| Required nonempty child relations such as hosts and area/expertise labels | Supplied in seed where applicable; their minimum cardinalities are not generally enforced automatically. |
| Additional temporal or review-assignment policies | No general enforcement of deadline chronology, session date within conference dates, or reviewer's pool membership when saving a review. These are not among Assignment 3's two required application checks; compare any additional Assignment 1 rules with the team's chosen conceptual design. |