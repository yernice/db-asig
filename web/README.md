# Part 3: Web application

Flask + SQLAlchemy Core (parameterized SQL via `text()`) on PostgreSQL.
Deployed on Render (app) with Neon (persistent PostgreSQL).

## What it does

| Entity | Operations |
| --- | --- |
| Users | Create, list, view, edit, delete. Author profile (ORCID, research areas) and reviewer profile (years of experience, expertise) are edited in the same form. |
| Papers | Create, list (filter by status), view, edit, delete. Authors with positions and the corresponding author, keywords, and versions (add / delete; next version number assigned automatically) are managed through the paper pages. |
| Reviews | Create, list, edit, delete. |
| Sessions | Create, list, view, edit, delete. |
| Conferences, tracks, reviewer pools, hosts | Read-only (loaded by the seed script), shown on the Conferences page and in selection lists. |
| `accepted_paper_schedule` view | Shown on the Schedule page. |

Every save runs in one transaction (`engine.begin()`): if any step fails, nothing is written and the
page shows a red error message.

## Required checks

| Check | Where it is enforced |
| --- | --- |
| No self-review when saving a review | `check_self_review()` in the app + trigger `review_no_self_review` |
| No self-review when changing a paper's authors | `check_new_authors_have_not_reviewed()` + trigger `author_not_reviewer` |
| Only accepted papers can be scheduled | `check_session_assignment()` + trigger `paper_session_valid` + CHECK `ck_paper_session_accepted` |
| Paper track and session in the same conference (on status / track / session change) | `check_session_assignment()` + trigger `paper_session_valid` |
| A session's conference cannot change while it holds papers of another conference | `check_session_conference_change()` + trigger `session_conference_change` |

All other database constraints (unique email, one review per reviewer and paper, score 1–5, unique
author positions, session times, etc.) are reported with readable messages (see `FRIENDLY` in `app.py`).

Optional Assignment 1 rules enforced by the application: every user has at least one role; every paper
has at least one author and exactly one corresponding author; a paper keeps at least one version;
a session chair belongs to the conference's reviewer pool (also a composite foreign key).

## Deletion behaviour

| Delete | Result |
| --- | --- |
| Paper | Cascades to its versions, authorship rows, keywords and reviews. |
| Session | Its papers stay and become unscheduled (`session_id` set to NULL). |
| Review | Removed. |
| User | Removes the author/reviewer profile and its areas. Rejected (RESTRICT) if the user authored a paper, wrote a review, is in a reviewer pool, coordinates a track or chairs a session; the page explains why. |

## Run locally

```bash
cd web
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export DATABASE_URL="postgresql://postgres:password@localhost:5432/conference"   # Windows: set DATABASE_URL=...
python init_db.py                    # runs db/schema.sql + db/sample_seed.sql (drops and recreates all tables)
python app.py                        # http://127.0.0.1:5000
```

To load the team's final seed instead of the sample: `python init_db.py db/schema.sql ../path/to/seed.sql`.
The seed must end with the `setval(...)` lines (see `db/sample_seed.sql`) so that new rows created in the
app get fresh IDs.

## Deploy (Neon + Render, both free)

1. **Neon**: create a project at neon.com and copy the connection string
   (`postgresql://user:password@ep-....neon.tech/neondb?sslmode=require`).
2. **Load the database** from your computer:
   `DATABASE_URL="<Neon string>" python init_db.py db/schema.sql <team seed file>`
3. **Push** this repository to GitHub (`render.yaml` at the repository root, the app in `web/`).
4. **Render**: New → Blueprint → choose the repository (it reads `render.yaml`).
   When asked, paste the Neon string as `DATABASE_URL`.
   Manual alternative: New → Web Service, Root Directory `web`, Build `pip install -r requirements.txt`,
   Start `gunicorn app:app`, environment variable `DATABASE_URL`.
5. Open the `https://<name>.onrender.com` URL. Put it in `links.txt`.

Free Render services sleep after a period without traffic; the first request afterwards can take
up to a minute.

## Demo script for the video (Part 3)

1. Users: create a user with both roles → edit the phone number → delete that user.
   Try to delete Arman Armanov → rejected (he authored papers).
2. Papers: create a paper with two authors, keywords and version 1 → add version 2 → edit the title → delete it
   (cascade message).
3. Reviews: create a valid review → edit its score → delete it.
   **Self-review:** paper 1 + reviewer Arman Armanov → rejected.
4. Sessions: create a session → edit the room → delete an empty session.
   **Invalid session assignment:** edit a *submitted* paper and choose a session → rejected;
   edit an accepted ADBC26 paper and choose a CAML26 session → rejected.
5. Schedule page: rows from the `accepted_paper_schedule` view.

## Files

```
render.yaml            Render Blueprint (repository root)
web/app.py             routes, transactions, application checks
web/templates/         HTML pages (Jinja)
web/static/style.css   minimal styling
web/init_db.py         loads schema + seed into any PostgreSQL (no psql needed)
web/db/schema.sql      team schema (tables, constraints, view, triggers)
web/db/sample_seed.sql small sample data for local testing
web/requirements.txt   Flask 3.1.3, SQLAlchemy 2.1.9, psycopg2-binary 2.9.13, gunicorn 27.0.1 (Python 3.13)
```
