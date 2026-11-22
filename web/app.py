"""
CSCI 341 Assignment 3, Part 3: web application for the
Research Conference and Paper Review Management System.

Flask + SQLAlchemy Core (parameterized SQL through text()) on PostgreSQL.

CRUD:       users (with author / reviewer profiles), papers (with authors,
            keywords and versions), reviews, conference sessions.
Read-only:  conferences, tracks, reviewer pools, hosts, accepted_paper_schedule.

Every save runs in one transaction (engine.begin()). The two required checks
(no self-review, valid session assignment) are validated here in the
application AND by triggers in the database; whichever fires, the user sees
a clear error message and nothing is written.
"""
import os
from datetime import date, datetime

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-only-secret-change-me")

STATUSES = ["submitted", "under review", "accepted", "rejected", "withdrawn"]
RECOMMENDATIONS = ["accept", "reject"]
AUTHOR_ROWS = 6  # author slots shown on the paper form


# --------------------------------------------------------------------------
# Database connection and helpers
# --------------------------------------------------------------------------
def database_url():
    url = os.environ.get("DATABASE_URL", "postgresql://postgres@localhost:5432/conference")
    # Hosts give "postgres://..." or "postgresql://..."; SQLAlchemy 2.1 would pick the psycopg 3
    # driver for a bare "postgresql://", so name the installed psycopg2 driver explicitly.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            url = "postgresql+psycopg2://" + url[len(prefix):]
    return url


engine = create_engine(database_url(), pool_pre_ping=True, pool_recycle=300)


class AppError(Exception):
    """A rule violated in application validation; shown to the user as is."""


def rows(sql, **params):
    with engine.connect() as conn:
        return conn.execute(text(sql), params).mappings().all()


def one(sql, **params):
    result = rows(sql, **params)
    return result[0] if result else None


def scalar(conn, sql, **params):
    return conn.execute(text(sql), params).scalar()


# Friendly explanations for database constraint violations, keyed by constraint name.
FRIENDLY = {
    "app_user_email_key": "Another user already has this email address.",
    "ck_user_email": "The email address is not valid.",
    "ck_author_orcid": "ORCID must look like 0000-0002-1825-0097.",
    "ck_reviewer_years": "Years of reviewing experience cannot be negative.",
    "ck_author_position": "Author positions must be positive integers.",
    "uq_paper_author_position": "Two authors of a paper cannot share the same position.",
    "paper_author_pkey": "The same author is listed twice for this paper.",
    "uq_one_corresponding_per_paper": "A paper can have only one corresponding author.",
    "ck_paper_status": "Unknown paper status.",
    "ck_paper_session_accepted": "Only accepted papers can be assigned to a session.",
    "ck_version_no": "Version numbers must be positive integers.",
    "paper_version_pkey": "This version number already exists for the paper.",
    "uq_review_paper_reviewer": "This reviewer has already reviewed this paper (one review per reviewer and paper).",
    "ck_review_score": "The overall score must be an integer from 1 to 5.",
    "ck_review_recommendation": "The recommendation must be accept or reject.",
    "ck_session_times": "The session end time must be later than its start time.",
    "conference_session_conference_id_chair_id_fkey": "The session chair must belong to the conference's reviewer pool.",
    # deletions blocked by ON DELETE RESTRICT
    "paper_author_author_id_fkey": "This user is listed as an author of one or more papers. Remove them from those papers first.",
    "review_reviewer_id_fkey": "This user has written reviews. Delete those reviews first.",
    "conference_reviewer_reviewer_id_fkey": "This user is in a conference reviewer pool.",
    "track_coordinator_id_fkey": "This user coordinates a track.",
    "conference_session_chair_id_fkey": "This user chairs a conference session. Choose another chair first.",
}


def db_message(err):
    """Turn a database error into a readable message (trigger text or constraint explanation)."""
    diag = getattr(getattr(err, "orig", None), "diag", None)
    if diag is None:
        return str(err)
    name = diag.constraint_name
    if name in FRIENDLY:
        return f"{FRIENDLY[name]} [database constraint: {name}]"
    return diag.message_primary or str(err)


def run_transaction(action):
    """Run action(conn) in one transaction. Returns (result, error_message)."""
    try:
        with engine.begin() as conn:
            return action(conn), None
    except AppError as err:
        return None, str(err)
    except DBAPIError as err:
        return None, db_message(err)


# --------------------------------------------------------------------------
# Form parsing helpers
# --------------------------------------------------------------------------
def required(form, field, label):
    value = (form.get(field) or "").strip()
    if not value:
        raise AppError(f"{label} is required.")
    return value


def optional(form, field):
    value = (form.get(field) or "").strip()
    return value or None


def to_int(value, label):
    try:
        return int(value)
    except (TypeError, ValueError):
        raise AppError(f"{label} must be a whole number.")


def lines(value):
    """Textarea with one item per line -> unique, non-empty items (stored as separate rows)."""
    seen, result = set(), []
    for item in (value or "").splitlines():
        item = item.strip()
        if item and item.lower() not in seen:
            seen.add(item.lower())
            result.append(item)
    return result


# --------------------------------------------------------------------------
# Required application checks (Part 1)
# --------------------------------------------------------------------------
def check_self_review(conn, paper_id, reviewer_id):
    """Check 1a: a reviewer may not review a paper they authored."""
    if scalar(conn, "SELECT 1 FROM paper_author WHERE paper_id = :p AND author_id = :r",
              p=paper_id, r=reviewer_id):
        name = scalar(conn, "SELECT given_name || ' ' || surname FROM app_user WHERE user_id = :r", r=reviewer_id)
        raise AppError(f"Self-review rejected: {name} is an author of paper {paper_id} and cannot review it.")


def check_new_authors_have_not_reviewed(conn, paper_id, author_ids):
    """Check 1b: when a paper's authors change, none of them may already be a reviewer of it."""
    names = conn.execute(text("""
        SELECT u.given_name || ' ' || u.surname
        FROM review r JOIN app_user u ON u.user_id = r.reviewer_id
        WHERE r.paper_id = :p AND r.reviewer_id = ANY(:ids)"""),
        {"p": paper_id, "ids": list(author_ids)}).scalars().all()
    if names:
        raise AppError("Author change rejected (self-review): " + ", ".join(names) +
                       f" already reviewed paper {paper_id} and cannot become its author.")


def check_session_assignment(conn, status, track_id, session_id):
    """Check 2: a scheduled paper must be accepted, and its track and session must share a conference."""
    if session_id is None:
        return
    if status != "accepted":
        raise AppError(f"Session assignment rejected: only accepted papers can be scheduled, "
                       f"but the status is '{status}'. Change the status or remove the session.")
    track_conf = conn.execute(text(
        "SELECT c.conference_id, c.acronym FROM track t JOIN conference c USING (conference_id) WHERE t.track_id = :t"),
        {"t": track_id}).first()
    session_conf = conn.execute(text(
        "SELECT c.conference_id, c.acronym FROM conference_session s JOIN conference c USING (conference_id) WHERE s.session_id = :s"),
        {"s": session_id}).first()
    if track_conf is None or session_conf is None:
        raise AppError("Unknown track or session.")
    if track_conf.conference_id != session_conf.conference_id:
        raise AppError(f"Session assignment rejected: the paper's track belongs to {track_conf.acronym}, "
                       f"but the session belongs to {session_conf.acronym}.")


def check_session_conference_change(conn, session_id, conference_id):
    """Check 2 when a session's conference changes: its scheduled papers must stay in the same conference."""
    bad = conn.execute(text("""
        SELECT p.paper_id FROM paper p JOIN track t ON t.track_id = p.track_id
        WHERE p.session_id = :s AND t.conference_id <> :c"""), {"s": session_id, "c": conference_id}).scalars().all()
    if bad:
        raise AppError("Session change rejected: papers " + ", ".join(map(str, bad)) +
                       " are scheduled in this session and belong to another conference. Unschedule them first.")


def check_chair_in_pool(conn, conference_id, chair_id):
    """Optional Assignment 1 rule (also enforced by a composite foreign key)."""
    if not scalar(conn, "SELECT 1 FROM conference_reviewer WHERE conference_id = :c AND reviewer_id = :r",
                  c=conference_id, r=chair_id):
        raise AppError("The session chair must be a reviewer in this conference's reviewer pool.")


# --------------------------------------------------------------------------
# Lookup lists for select boxes
# --------------------------------------------------------------------------
def all_authors():
    return rows("""SELECT a.author_id AS id, u.given_name || ' ' || u.surname AS name, u.email
                   FROM author a JOIN app_user u ON u.user_id = a.author_id ORDER BY u.surname, u.given_name""")


def all_reviewers():
    return rows("""SELECT r.reviewer_id AS id, u.given_name || ' ' || u.surname AS name,
                          COALESCE(string_agg(c.acronym, ', ' ORDER BY c.acronym), 'no pool') AS pools
                   FROM reviewer r JOIN app_user u ON u.user_id = r.reviewer_id
                   LEFT JOIN conference_reviewer cr ON cr.reviewer_id = r.reviewer_id
                   LEFT JOIN conference c ON c.conference_id = cr.conference_id
                   GROUP BY r.reviewer_id, u.given_name, u.surname ORDER BY u.surname, u.given_name""")


def all_tracks():
    return rows("""SELECT t.track_id AS id, c.acronym || ' / ' || t.name AS label
                   FROM track t JOIN conference c USING (conference_id) ORDER BY c.acronym, t.name""")


def all_sessions():
    return rows("""SELECT s.session_id AS id,
                          c.acronym || ' / ' || s.title || ' (' || s.session_date || ' ' ||
                          to_char(s.start_time, 'HH24:MI') || ')' AS label
                   FROM conference_session s JOIN conference c USING (conference_id)
                   ORDER BY c.acronym, s.session_date, s.start_time""")


def all_conferences():
    return rows("SELECT conference_id AS id, acronym || ' - ' || name AS label FROM conference ORDER BY acronym")


def all_papers():
    return rows("SELECT paper_id AS id, paper_id || ': ' || title AS label FROM paper ORDER BY paper_id")


# --------------------------------------------------------------------------
# Home, conferences (read-only), schedule view
# --------------------------------------------------------------------------
@app.route("/")
def index():
    counts = one("""SELECT (SELECT count(*) FROM app_user) AS users,
                           (SELECT count(*) FROM paper) AS papers,
                           (SELECT count(*) FROM review) AS reviews,
                           (SELECT count(*) FROM conference_session) AS sessions,
                           (SELECT count(*) FROM conference) AS conferences,
                           (SELECT count(*) FROM track) AS tracks""")
    return render_template("index.html", counts=counts)


@app.route("/conferences")
def conferences():
    confs = rows("SELECT * FROM conference ORDER BY conference_id")
    hosts = rows("SELECT * FROM conference_host ORDER BY host_name")
    tracks = rows("""SELECT t.*, u.given_name || ' ' || u.surname AS coordinator,
                            (SELECT count(*) FROM paper p WHERE p.track_id = t.track_id) AS papers
                     FROM track t JOIN app_user u ON u.user_id = t.coordinator_id ORDER BY t.track_id""")
    sessions = rows("""SELECT s.*, u.given_name || ' ' || u.surname AS chair,
                              (SELECT count(*) FROM paper p WHERE p.session_id = s.session_id) AS papers
                       FROM conference_session s JOIN app_user u ON u.user_id = s.chair_id
                       ORDER BY s.session_date, s.start_time""")
    pool = rows("""SELECT cr.conference_id, u.user_id, u.given_name || ' ' || u.surname AS name
                   FROM conference_reviewer cr JOIN app_user u ON u.user_id = cr.reviewer_id ORDER BY u.surname""")
    return render_template("conferences.html", confs=confs, hosts=hosts, tracks=tracks,
                           sessions=sessions, pool=pool)


@app.route("/schedule")
def schedule():
    items = rows("""SELECT * FROM accepted_paper_schedule
                    ORDER BY conference_id, session_date, start_time, session_id, paper_id""")
    return render_template("schedule.html", items=items)


# --------------------------------------------------------------------------
# Users (with author and reviewer profiles)
# --------------------------------------------------------------------------
@app.route("/users")
def users_list():
    users = rows("""SELECT u.*, a.author_id IS NOT NULL AS is_author, r.reviewer_id IS NOT NULL AS is_reviewer,
                           r.years_experience
                    FROM app_user u
                    LEFT JOIN author a ON a.author_id = u.user_id
                    LEFT JOIN reviewer r ON r.reviewer_id = u.user_id
                    ORDER BY u.user_id""")
    return render_template("users_list.html", users=users)


@app.route("/users/<int:user_id>")
def user_detail(user_id):
    user = one("""SELECT u.*, a.author_id IS NOT NULL AS is_author, a.orcid,
                         r.reviewer_id IS NOT NULL AS is_reviewer, r.years_experience
                  FROM app_user u LEFT JOIN author a ON a.author_id = u.user_id
                  LEFT JOIN reviewer r ON r.reviewer_id = u.user_id WHERE u.user_id = :id""", id=user_id)
    if user is None:
        abort(404)
    areas = rows("SELECT area_label FROM author_research_area WHERE author_id = :id ORDER BY 1", id=user_id)
    expertise = rows("SELECT area_label FROM reviewer_expertise WHERE reviewer_id = :id ORDER BY 1", id=user_id)
    papers = rows("""SELECT p.paper_id, p.title, p.status, pa.author_position, pa.is_corresponding
                     FROM paper_author pa JOIN paper p USING (paper_id) WHERE pa.author_id = :id ORDER BY p.paper_id""",
                  id=user_id)
    reviews = rows("""SELECT r.review_id, r.paper_id, p.title, r.overall_score, r.recommendation
                      FROM review r JOIN paper p USING (paper_id) WHERE r.reviewer_id = :id ORDER BY r.review_id""",
                   id=user_id)
    pools = rows("""SELECT c.acronym FROM conference_reviewer cr JOIN conference c USING (conference_id)
                    WHERE cr.reviewer_id = :id ORDER BY 1""", id=user_id)
    return render_template("user_detail.html", user=user, areas=areas, expertise=expertise,
                           papers=papers, reviews=reviews, pools=pools)


def user_form_from_db(user_id):
    user = one("""SELECT u.*, a.author_id IS NOT NULL AS is_author, a.orcid,
                         r.reviewer_id IS NOT NULL AS is_reviewer, r.years_experience
                  FROM app_user u LEFT JOIN author a ON a.author_id = u.user_id
                  LEFT JOIN reviewer r ON r.reviewer_id = u.user_id WHERE u.user_id = :id""", id=user_id)
    if user is None:
        abort(404)
    form = {k: ("" if v is None else str(v)) for k, v in user.items()}
    form["is_author"] = "on" if user["is_author"] else ""
    form["is_reviewer"] = "on" if user["is_reviewer"] else ""
    form["research_areas"] = "\n".join(r["area_label"] for r in rows(
        "SELECT area_label FROM author_research_area WHERE author_id = :id ORDER BY 1", id=user_id))
    form["expertise"] = "\n".join(r["area_label"] for r in rows(
        "SELECT area_label FROM reviewer_expertise WHERE reviewer_id = :id ORDER BY 1", id=user_id))
    return form


def save_user(conn, form, user_id=None):
    data = {
        "given_name": required(form, "given_name", "Given name"),
        "surname": required(form, "surname", "Surname"),
        "email": required(form, "email", "Email").lower(),
        "affiliation": required(form, "affiliation", "Affiliation"),
        "country": required(form, "country", "Country"),
        "phone_number": required(form, "phone_number", "Phone number"),
    }
    is_author, is_reviewer = bool(form.get("is_author")), bool(form.get("is_reviewer"))
    if not (is_author or is_reviewer):  # optional Assignment 1 rule, enforced here
        raise AppError("Every user must have an author role, a reviewer role, or both.")
    years = to_int(required(form, "years_experience", "Years of reviewing experience"),
                   "Years of reviewing experience") if is_reviewer else None

    if user_id is None:
        user_id = scalar(conn, """INSERT INTO app_user (given_name, surname, email, affiliation, country, phone_number)
                                  VALUES (:given_name, :surname, :email, :affiliation, :country, :phone_number)
                                  RETURNING user_id""", **data)
    else:
        conn.execute(text("""UPDATE app_user SET given_name = :given_name, surname = :surname, email = :email,
                                    affiliation = :affiliation, country = :country, phone_number = :phone_number
                             WHERE user_id = :id"""), {**data, "id": user_id})

    # Author profile: research areas are stored as separate rows (multivalued attribute).
    if is_author:
        conn.execute(text("""INSERT INTO author (author_id, orcid) VALUES (:id, :orcid)
                             ON CONFLICT (author_id) DO UPDATE SET orcid = EXCLUDED.orcid"""),
                     {"id": user_id, "orcid": optional(form, "orcid")})
        conn.execute(text("DELETE FROM author_research_area WHERE author_id = :id"), {"id": user_id})
        for area in lines(form.get("research_areas")):
            conn.execute(text("INSERT INTO author_research_area VALUES (:id, :a)"), {"id": user_id, "a": area})
    else:  # removing the role; blocked by the database if the user authored papers
        conn.execute(text("DELETE FROM author WHERE author_id = :id"), {"id": user_id})

    # Reviewer profile
    if is_reviewer:
        conn.execute(text("""INSERT INTO reviewer (reviewer_id, years_experience) VALUES (:id, :y)
                             ON CONFLICT (reviewer_id) DO UPDATE SET years_experience = EXCLUDED.years_experience"""),
                     {"id": user_id, "y": years})
        conn.execute(text("DELETE FROM reviewer_expertise WHERE reviewer_id = :id"), {"id": user_id})
        for area in lines(form.get("expertise")):
            conn.execute(text("INSERT INTO reviewer_expertise VALUES (:id, :a)"), {"id": user_id, "a": area})
    else:  # blocked by the database if the user has reviews, a pool membership, a track or a session
        conn.execute(text("DELETE FROM reviewer WHERE reviewer_id = :id"), {"id": user_id})
    return user_id


@app.route("/users/new", methods=["GET", "POST"])
def user_new():
    if request.method == "POST":
        user_id, error = run_transaction(lambda conn: save_user(conn, request.form))
        if error is None:
            flash(f"User {user_id} created.", "ok")
            return redirect(url_for("user_detail", user_id=user_id))
        flash(error, "error")
        return render_template("user_form.html", form=request.form, user_id=None), 400
    return render_template("user_form.html", form={}, user_id=None)


@app.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
def user_edit(user_id):
    if request.method == "POST":
        _, error = run_transaction(lambda conn: save_user(conn, request.form, user_id))
        if error is None:
            flash(f"User {user_id} updated.", "ok")
            return redirect(url_for("user_detail", user_id=user_id))
        flash(error, "error")
        return render_template("user_form.html", form=request.form, user_id=user_id), 400
    return render_template("user_form.html", form=user_form_from_db(user_id), user_id=user_id)


@app.route("/users/<int:user_id>/delete", methods=["POST"])
def user_delete(user_id):
    deleted, error = run_transaction(lambda conn: conn.execute(
        text("DELETE FROM app_user WHERE user_id = :id"), {"id": user_id}).rowcount)
    if error:
        flash(f"Delete rejected: {error}", "error")
        return redirect(url_for("user_detail", user_id=user_id))
    flash(f"User {user_id} deleted (with their author/reviewer profile)." if deleted else "User not found.", "ok")
    return redirect(url_for("users_list"))


# --------------------------------------------------------------------------
# Papers (with authorship, keywords and versions)
# --------------------------------------------------------------------------
@app.route("/papers")
def papers_list():
    status = request.args.get("status") or None
    papers = rows("""
        SELECT p.paper_id, p.title, p.status, c.acronym, t.name AS track, s.title AS session_title,
               (SELECT u.given_name || ' ' || u.surname FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
                 WHERE pa.paper_id = p.paper_id AND pa.is_corresponding) AS corresponding,
               (SELECT count(*) FROM review r WHERE r.paper_id = p.paper_id) AS reviews,
               (SELECT max(version_no) FROM paper_version v WHERE v.paper_id = p.paper_id) AS current_version
        FROM paper p JOIN track t ON t.track_id = p.track_id JOIN conference c ON c.conference_id = t.conference_id
        LEFT JOIN conference_session s ON s.session_id = p.session_id
        WHERE CAST(:status AS VARCHAR) IS NULL OR p.status = :status
        ORDER BY p.paper_id""", status=status)
    return render_template("papers_list.html", papers=papers, statuses=STATUSES, status=status)


@app.route("/papers/<int:paper_id>")
def paper_detail(paper_id):
    paper = one("""SELECT p.*, t.name AS track, c.acronym, c.conference_id, s.title AS session_title,
                          s.session_date, s.start_time
                   FROM paper p JOIN track t ON t.track_id = p.track_id
                   JOIN conference c ON c.conference_id = t.conference_id
                   LEFT JOIN conference_session s ON s.session_id = p.session_id
                   WHERE p.paper_id = :id""", id=paper_id)
    if paper is None:
        abort(404)
    authors = rows("""SELECT pa.*, u.given_name || ' ' || u.surname AS name, u.email
                      FROM paper_author pa JOIN app_user u ON u.user_id = pa.author_id
                      WHERE pa.paper_id = :id ORDER BY pa.author_position""", id=paper_id)
    keywords = rows("SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY keyword", id=paper_id)
    versions = rows("SELECT * FROM paper_version WHERE paper_id = :id ORDER BY version_no DESC", id=paper_id)
    reviews = rows("""SELECT r.*, u.given_name || ' ' || u.surname AS reviewer
                      FROM review r JOIN app_user u ON u.user_id = r.reviewer_id
                      WHERE r.paper_id = :id ORDER BY r.review_id""", id=paper_id)
    return render_template("paper_detail.html", paper=paper, authors=authors, keywords=keywords,
                           versions=versions, reviews=reviews,
                           now=datetime.now().strftime("%Y-%m-%dT%H:%M"))


def paper_form_from_db(paper_id):
    paper = one("SELECT * FROM paper WHERE paper_id = :id", id=paper_id)
    if paper is None:
        abort(404)
    form = {k: ("" if v is None else str(v)) for k, v in paper.items()}
    form["keywords"] = "\n".join(r["keyword"] for r in rows(
        "SELECT keyword FROM paper_keyword WHERE paper_id = :id ORDER BY keyword", id=paper_id))
    for i, a in enumerate(rows("SELECT * FROM paper_author WHERE paper_id = :id ORDER BY author_position", id=paper_id)):
        form[f"author_{i}"] = str(a["author_id"])
        form[f"position_{i}"] = str(a["author_position"])
        if a["is_corresponding"]:
            form["corresponding"] = str(i)
    return form


def parse_authors(form):
    """Author slots -> list of (author_id, position, is_corresponding)."""
    authors, used_ids, used_positions = [], set(), set()
    corresponding = form.get("corresponding")
    for i in range(AUTHOR_ROWS):
        author_id = (form.get(f"author_{i}") or "").strip()
        if not author_id:
            continue
        author_id = to_int(author_id, "Author")
        position = to_int(form.get(f"position_{i}") or (len(authors) + 1), "Author position")
        if author_id in used_ids:
            raise AppError("The same author is listed twice.")
        if position in used_positions:
            raise AppError(f"Author position {position} is used twice.")
        if position < 1:
            raise AppError("Author positions must be positive.")
        used_ids.add(author_id)
        used_positions.add(position)
        authors.append((author_id, position, corresponding == str(i)))
    if not authors:
        raise AppError("A paper needs at least one author.")
    if sum(1 for a in authors if a[2]) != 1:  # optional Assignment 1 rule, enforced here
        raise AppError("Choose exactly one corresponding author (among the selected authors).")
    return authors


def save_paper(conn, form, paper_id=None):
    data = {
        "track_id": to_int(required(form, "track_id", "Track"), "Track"),
        "title": required(form, "title", "Title"),
        "abstract": required(form, "abstract", "Abstract"),
        "submission_date": required(form, "submission_date", "Submission date"),
        "status": required(form, "status", "Status"),
        "session_id": to_int(form["session_id"], "Session") if form.get("session_id") else None,
    }
    if data["status"] not in STATUSES:
        raise AppError("Unknown status.")
    authors = parse_authors(form)

    # Required check 2: validate the session assignment against the new status and track.
    check_session_assignment(conn, data["status"], data["track_id"], data["session_id"])

    if paper_id is None:
        paper_id = scalar(conn, """INSERT INTO paper (track_id, title, abstract, submission_date, status, session_id)
                                   VALUES (:track_id, :title, :abstract, :submission_date, :status, :session_id)
                                   RETURNING paper_id""", **data)
        conn.execute(text("""INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
                             VALUES (:p, 1, :loc, now(), :note)"""),
                     {"p": paper_id, "loc": required(form, "file_location", "File location of version 1"),
                      "note": optional(form, "change_note")})
    else:
        conn.execute(text("""UPDATE paper SET track_id = :track_id, title = :title, abstract = :abstract,
                                    submission_date = :submission_date, status = :status, session_id = :session_id
                             WHERE paper_id = :id"""), {**data, "id": paper_id})
        # Required check 1 (second half): new authors may not be reviewers of this paper.
        check_new_authors_have_not_reviewed(conn, paper_id, [a[0] for a in authors])
        conn.execute(text("DELETE FROM paper_author WHERE paper_id = :p"), {"p": paper_id})

    for author_id, position, is_corr in authors:
        conn.execute(text("""INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding)
                             VALUES (:p, :a, :pos, :c)"""), {"p": paper_id, "a": author_id, "pos": position, "c": is_corr})

    conn.execute(text("DELETE FROM paper_keyword WHERE paper_id = :p"), {"p": paper_id})
    for keyword in lines(form.get("keywords")):
        conn.execute(text("INSERT INTO paper_keyword VALUES (:p, :k)"), {"p": paper_id, "k": keyword})
    return paper_id


def paper_form_context(form, paper_id):
    return dict(form=form, paper_id=paper_id, tracks=all_tracks(), sessions=all_sessions(),
                authors=all_authors(), statuses=STATUSES, author_rows=range(AUTHOR_ROWS))


@app.route("/papers/new", methods=["GET", "POST"])
def paper_new():
    if request.method == "POST":
        paper_id, error = run_transaction(lambda conn: save_paper(conn, request.form))
        if error is None:
            flash(f"Paper {paper_id} created with version 1.", "ok")
            return redirect(url_for("paper_detail", paper_id=paper_id))
        flash(error, "error")
        return render_template("paper_form.html", **paper_form_context(request.form, None)), 400
    form = {"submission_date": date.today().isoformat(), "status": "submitted", "position_0": "1", "corresponding": "0"}
    return render_template("paper_form.html", **paper_form_context(form, None))


@app.route("/papers/<int:paper_id>/edit", methods=["GET", "POST"])
def paper_edit(paper_id):
    if request.method == "POST":
        _, error = run_transaction(lambda conn: save_paper(conn, request.form, paper_id))
        if error is None:
            flash(f"Paper {paper_id} updated.", "ok")
            return redirect(url_for("paper_detail", paper_id=paper_id))
        flash(error, "error")
        return render_template("paper_form.html", **paper_form_context(request.form, paper_id)), 400
    return render_template("paper_form.html", **paper_form_context(paper_form_from_db(paper_id), paper_id))


@app.route("/papers/<int:paper_id>/delete", methods=["POST"])
def paper_delete(paper_id):
    def action(conn):
        counts = conn.execute(text("""SELECT (SELECT count(*) FROM paper_version WHERE paper_id = :p) AS v,
                                             (SELECT count(*) FROM review WHERE paper_id = :p) AS r"""),
                              {"p": paper_id}).first()
        deleted = conn.execute(text("DELETE FROM paper WHERE paper_id = :p"), {"p": paper_id}).rowcount
        return deleted, counts

    result, error = run_transaction(action)
    if error:
        flash(f"Delete rejected: {error}", "error")
        return redirect(url_for("paper_detail", paper_id=paper_id))
    deleted, counts = result
    if deleted:
        flash(f"Paper {paper_id} deleted. Cascaded: {counts.v} version(s), {counts.r} review(s), "
              "its authorship and keyword rows.", "ok")
    return redirect(url_for("papers_list"))


@app.route("/papers/<int:paper_id>/versions", methods=["POST"])
def version_add(paper_id):
    def action(conn):
        next_no = scalar(conn, "SELECT COALESCE(MAX(version_no), 0) + 1 FROM paper_version WHERE paper_id = :p",
                         p=paper_id)
        conn.execute(text("""INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note)
                             VALUES (:p, :v, :loc, :at, :note)"""),
                     {"p": paper_id, "v": next_no, "loc": required(request.form, "file_location", "File location"),
                      "at": optional(request.form, "uploaded_at") or datetime.now(),
                      "note": optional(request.form, "change_note")})
        return next_no

    version_no, error = run_transaction(action)
    if error:
        flash(error, "error")
    else:
        flash(f"Version {version_no} added; it is now the current version.", "ok")
    return redirect(url_for("paper_detail", paper_id=paper_id))


@app.route("/papers/<int:paper_id>/versions/<int:version_no>/delete", methods=["POST"])
def version_delete(paper_id, version_no):
    def action(conn):
        if scalar(conn, "SELECT count(*) FROM paper_version WHERE paper_id = :p", p=paper_id) <= 1:
            raise AppError("A paper must keep at least one version.")  # optional rule, enforced here
        return conn.execute(text("DELETE FROM paper_version WHERE paper_id = :p AND version_no = :v"),
                            {"p": paper_id, "v": version_no}).rowcount

    _, error = run_transaction(action)
    flash(error or f"Version {version_no} deleted.", "error" if error else "ok")
    return redirect(url_for("paper_detail", paper_id=paper_id))


# --------------------------------------------------------------------------
# Reviews
# --------------------------------------------------------------------------
@app.route("/reviews")
def reviews_list():
    reviews = rows("""SELECT r.*, p.title, u.given_name || ' ' || u.surname AS reviewer
                      FROM review r JOIN paper p USING (paper_id) JOIN app_user u ON u.user_id = r.reviewer_id
                      ORDER BY r.review_id""")
    return render_template("reviews_list.html", reviews=reviews)


def save_review(conn, form, review_id=None):
    data = {
        "paper_id": to_int(required(form, "paper_id", "Paper"), "Paper"),
        "reviewer_id": to_int(required(form, "reviewer_id", "Reviewer"), "Reviewer"),
        "overall_score": to_int(required(form, "overall_score", "Overall score"), "Overall score"),
        "recommendation": required(form, "recommendation", "Recommendation"),
        "comments_for_authors": required(form, "comments_for_authors", "Comments for authors"),
        "confidential_comments": optional(form, "confidential_comments"),
        "review_submission_date": required(form, "review_submission_date", "Submission date"),
    }
    # Required check 1: no self-reviews.
    check_self_review(conn, data["paper_id"], data["reviewer_id"])
    if review_id is None:
        return scalar(conn, """INSERT INTO review (paper_id, reviewer_id, overall_score, recommendation,
                                   comments_for_authors, confidential_comments, review_submission_date)
                               VALUES (:paper_id, :reviewer_id, :overall_score, :recommendation,
                                   :comments_for_authors, :confidential_comments, :review_submission_date)
                               RETURNING review_id""", **data)
    conn.execute(text("""UPDATE review SET paper_id = :paper_id, reviewer_id = :reviewer_id,
                                overall_score = :overall_score, recommendation = :recommendation,
                                comments_for_authors = :comments_for_authors,
                                confidential_comments = :confidential_comments,
                                review_submission_date = :review_submission_date
                         WHERE review_id = :id"""), {**data, "id": review_id})
    return review_id


def review_form_context(form, review_id):
    return dict(form=form, review_id=review_id, papers=all_papers(), reviewers=all_reviewers(),
                recommendations=RECOMMENDATIONS)


@app.route("/reviews/new", methods=["GET", "POST"])
def review_new():
    if request.method == "POST":
        review_id, error = run_transaction(lambda conn: save_review(conn, request.form))
        if error is None:
            flash(f"Review {review_id} saved.", "ok")
            return redirect(url_for("reviews_list"))
        flash(error, "error")
        return render_template("review_form.html", **review_form_context(request.form, None)), 400
    form = {"review_submission_date": date.today().isoformat(), "paper_id": request.args.get("paper_id", "")}
    return render_template("review_form.html", **review_form_context(form, None))


@app.route("/reviews/<int:review_id>/edit", methods=["GET", "POST"])
def review_edit(review_id):
    if request.method == "POST":
        _, error = run_transaction(lambda conn: save_review(conn, request.form, review_id))
        if error is None:
            flash(f"Review {review_id} updated.", "ok")
            return redirect(url_for("reviews_list"))
        flash(error, "error")
        return render_template("review_form.html", **review_form_context(request.form, review_id)), 400
    review = one("SELECT * FROM review WHERE review_id = :id", id=review_id)
    if review is None:
        abort(404)
    form = {k: ("" if v is None else str(v)) for k, v in review.items()}
    return render_template("review_form.html", **review_form_context(form, review_id))


@app.route("/reviews/<int:review_id>/delete", methods=["POST"])
def review_delete(review_id):
    deleted, error = run_transaction(lambda conn: conn.execute(
        text("DELETE FROM review WHERE review_id = :id"), {"id": review_id}).rowcount)
    flash(error or (f"Review {review_id} deleted." if deleted else "Review not found."), "error" if error else "ok")
    return redirect(url_for("reviews_list"))


# --------------------------------------------------------------------------
# Conference sessions
# --------------------------------------------------------------------------
@app.route("/sessions")
def sessions_list():
    sessions = rows("""SELECT s.*, c.acronym, c.city, u.given_name || ' ' || u.surname AS chair,
                              (SELECT count(*) FROM paper p WHERE p.session_id = s.session_id) AS papers
                       FROM conference_session s JOIN conference c USING (conference_id)
                       JOIN app_user u ON u.user_id = s.chair_id
                       ORDER BY c.acronym, s.session_date, s.start_time""")
    return render_template("sessions_list.html", sessions=sessions)


@app.route("/sessions/<int:session_id>")
def session_detail(session_id):
    session = one("""SELECT s.*, c.acronym, c.name AS conference, u.given_name || ' ' || u.surname AS chair
                     FROM conference_session s JOIN conference c USING (conference_id)
                     JOIN app_user u ON u.user_id = s.chair_id WHERE s.session_id = :id""", id=session_id)
    if session is None:
        abort(404)
    papers = rows("SELECT paper_id, title, status FROM paper WHERE session_id = :id ORDER BY paper_id", id=session_id)
    return render_template("session_detail.html", session=session, papers=papers)


def save_session(conn, form, session_id=None):
    data = {
        "conference_id": to_int(required(form, "conference_id", "Conference"), "Conference"),
        "title": required(form, "title", "Title"),
        "session_date": required(form, "session_date", "Date"),
        "start_time": required(form, "start_time", "Start time"),
        "end_time": required(form, "end_time", "End time"),
        "room_label": required(form, "room_label", "Room"),
        "chair_id": to_int(required(form, "chair_id", "Chair"), "Chair"),
    }
    if data["end_time"] <= data["start_time"]:  # "HH:MM" strings compare correctly
        raise AppError("The session end time must be later than its start time.")
    check_chair_in_pool(conn, data["conference_id"], data["chair_id"])
    if session_id is None:
        return scalar(conn, """INSERT INTO conference_session (conference_id, title, session_date, start_time,
                                   end_time, room_label, chair_id)
                               VALUES (:conference_id, :title, :session_date, :start_time, :end_time,
                                   :room_label, :chair_id)
                               RETURNING session_id""", **data)
    # Required check 2 when the session's conference changes.
    check_session_conference_change(conn, session_id, data["conference_id"])
    conn.execute(text("""UPDATE conference_session SET conference_id = :conference_id, title = :title,
                                session_date = :session_date, start_time = :start_time, end_time = :end_time,
                                room_label = :room_label, chair_id = :chair_id
                         WHERE session_id = :id"""), {**data, "id": session_id})
    return session_id


def session_form_context(form, session_id):
    return dict(form=form, session_id=session_id, conferences=all_conferences(), reviewers=all_reviewers())


@app.route("/sessions/new", methods=["GET", "POST"])
def session_new():
    if request.method == "POST":
        session_id, error = run_transaction(lambda conn: save_session(conn, request.form))
        if error is None:
            flash(f"Session {session_id} created.", "ok")
            return redirect(url_for("session_detail", session_id=session_id))
        flash(error, "error")
        return render_template("session_form.html", **session_form_context(request.form, None)), 400
    return render_template("session_form.html", **session_form_context({}, None))


@app.route("/sessions/<int:session_id>/edit", methods=["GET", "POST"])
def session_edit(session_id):
    if request.method == "POST":
        _, error = run_transaction(lambda conn: save_session(conn, request.form, session_id))
        if error is None:
            flash(f"Session {session_id} updated.", "ok")
            return redirect(url_for("session_detail", session_id=session_id))
        flash(error, "error")
        return render_template("session_form.html", **session_form_context(request.form, session_id)), 400
    session = one("SELECT * FROM conference_session WHERE session_id = :id", id=session_id)
    if session is None:
        abort(404)
    form = {k: ("" if v is None else str(v)) for k, v in session.items()}
    for key in ("start_time", "end_time"):
        form[key] = form[key][:5]  # HH:MM for <input type="time">
    return render_template("session_form.html", **session_form_context(form, session_id))


@app.route("/sessions/<int:session_id>/delete", methods=["POST"])
def session_delete(session_id):
    def action(conn):
        papers = scalar(conn, "SELECT count(*) FROM paper WHERE session_id = :s", s=session_id)
        deleted = conn.execute(text("DELETE FROM conference_session WHERE session_id = :s"),
                               {"s": session_id}).rowcount
        return deleted, papers

    result, error = run_transaction(action)
    if error:
        flash(f"Delete rejected: {error}", "error")
        return redirect(url_for("session_detail", session_id=session_id))
    deleted, papers = result
    if deleted:
        flash(f"Session {session_id} deleted. {papers} paper(s) were unscheduled (session_id set to NULL).", "ok")
    return redirect(url_for("sessions_list"))


@app.errorhandler(404)
def not_found(_):
    return render_template("message.html", title="Not found", message="This record does not exist."), 404


if __name__ == "__main__":
    app.run(debug=True, port=int(os.environ.get("PORT", 5000)))
