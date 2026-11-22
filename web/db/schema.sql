DROP VIEW  IF EXISTS accepted_paper_schedule;
DROP FUNCTION IF EXISTS trg_review_no_self_review() CASCADE;
DROP FUNCTION IF EXISTS trg_author_not_reviewer() CASCADE;
DROP FUNCTION IF EXISTS trg_paper_session_valid() CASCADE;
DROP FUNCTION IF EXISTS trg_session_conference_change() CASCADE;
DROP FUNCTION IF EXISTS trg_track_conference_change() CASCADE;
DROP TABLE IF EXISTS review CASCADE;
DROP TABLE IF EXISTS paper_version CASCADE;
DROP TABLE IF EXISTS paper_author CASCADE;
DROP TABLE IF EXISTS paper_keyword CASCADE;
DROP TABLE IF EXISTS paper CASCADE;
DROP TABLE IF EXISTS conference_session CASCADE;
DROP TABLE IF EXISTS track CASCADE;
DROP TABLE IF EXISTS conference_reviewer CASCADE;
DROP TABLE IF EXISTS conference_host CASCADE;
DROP TABLE IF EXISTS conference CASCADE;
DROP TABLE IF EXISTS reviewer_expertise CASCADE;
DROP TABLE IF EXISTS reviewer CASCADE;
DROP TABLE IF EXISTS author_research_area CASCADE;
DROP TABLE IF EXISTS author CASCADE;
DROP TABLE IF EXISTS app_user CASCADE;

CREATE TABLE app_user(
    user_id SERIAL PRIMARY KEY,
    given_name VARCHAR(100) NOT NULL,
    surname VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    affiliation VARCHAR(200) NOT NULL,
    country VARCHAR(100) NOT NULL,
    phone_number VARCHAR(30)  NOT NULL,
    CONSTRAINT ck_user_email CHECK(position('@' IN email) >1)
);

CREATE TABLE author(
    author_id INT PRIMARY KEY REFERENCES app_user(user_id) ON DELETE CASCADE,
    orcid VARCHAR(19),
    CONSTRAINT ck_author_orcid CHECK(orcid IS NULL OR orcid ~'^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$')
);

CREATE TABLE author_research_area(
    author_id  INT NOT NULL REFERENCES author(author_id) ON DELETE CASCADE,
    area_label VARCHAR(100) NOT NULL,
    PRIMARY KEY(author_id, area_label)
);

CREATE TABLE reviewer(
    reviewer_id INT PRIMARY KEY REFERENCES app_user(user_id) ON DELETE CASCADE,
    years_experience INT NOT NULL,
    CONSTRAINT ck_reviewer_years CHECK(years_experience >=0)
);

CREATE TABLE reviewer_expertise(
    reviewer_id INT NOT NULL REFERENCES reviewer(reviewer_id) ON DELETE CASCADE,
    area_label  VARCHAR(100) NOT NULL,
    PRIMARY KEY(reviewer_id, area_label)
);

CREATE TABLE conference(
    conference_id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    acronym VARCHAR(20) NOT NULL UNIQUE,
    description TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    country VARCHAR(100) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    submission_deadline DATE NOT NULL,
    review_deadline DATE NOT NULL,
    CONSTRAINT ck_conf_dates CHECK(end_date >=start_date)
);

CREATE TABLE conference_host(
    conference_id INT NOT NULL REFERENCES conference(conference_id) ON DELETE CASCADE,
    host_name VARCHAR(200) NOT NULL,
    PRIMARY KEY(conference_id, host_name)
);

CREATE TABLE conference_reviewer(
    conference_id INT NOT NULL REFERENCES conference(conference_id) ON DELETE CASCADE,
    reviewer_id INT NOT NULL REFERENCES reviewer(reviewer_id) ON DELETE RESTRICT,
    PRIMARY KEY(conference_id, reviewer_id)
);

CREATE TABLE track(
    track_id SERIAL PRIMARY KEY,
    conference_id INT NOT NULL REFERENCES conference(conference_id) ON DELETE CASCADE,
    name VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    research_area VARCHAR(100) NOT NULL,
    coordinator_id INT NOT NULL REFERENCES reviewer(reviewer_id) ON DELETE RESTRICT,
    UNIQUE(conference_id, name),
    FOREIGN KEY(conference_id, coordinator_id) REFERENCES conference_reviewer(conference_id, reviewer_id)
);

CREATE TABLE conference_session(
    session_id SERIAL PRIMARY KEY,
    conference_id INT NOT NULL REFERENCES conference(conference_id) ON DELETE CASCADE,
    title VARCHAR(200) NOT NULL,
    session_date DATE NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,
    room_label VARCHAR(50) NOT NULL,
    chair_id INT NOT NULL REFERENCES reviewer(reviewer_id) ON DELETE RESTRICT,
    CONSTRAINT ck_session_times CHECK(end_time >start_time),
    FOREIGN KEY(conference_id, chair_id) REFERENCES conference_reviewer(conference_id, reviewer_id)
);

CREATE TABLE paper(
    paper_id SERIAL PRIMARY KEY,
    track_id INT NOT NULL REFERENCES track(track_id) ON DELETE RESTRICT,
    title VARCHAR(300) NOT NULL,
    abstract TEXT NOT NULL,
    submission_date DATE NOT NULL,
    status VARCHAR(20) NOT NULL,
    session_id INT REFERENCES conference_session(session_id) ON DELETE SET NULL,
    CONSTRAINT ck_paper_status CHECK(status IN ('submitted','under review','accepted','rejected','withdrawn')),
    CONSTRAINT ck_paper_session_accepted CHECK(session_id IS NULL OR status = 'accepted')
);

CREATE TABLE paper_keyword(
    paper_id INT NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
    keyword  VARCHAR(100) NOT NULL,
    PRIMARY KEY(paper_id, keyword)
);

CREATE TABLE paper_author(
    paper_id INT NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
    author_id INT NOT NULL REFERENCES author(author_id) ON DELETE RESTRICT,
    author_position INT NOT NULL,
    is_corresponding BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (paper_id, author_id),
    CONSTRAINT uq_paper_author_position UNIQUE(paper_id, author_position),
    CONSTRAINT ck_author_position CHECK(author_position >0)
);

CREATE UNIQUE INDEX uq_one_corresponding_per_paper ON paper_author(paper_id) WHERE is_corresponding;

CREATE TABLE paper_version(
    paper_id INT NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
    version_no INT NOT NULL,
    file_location VARCHAR(500) NOT NULL,
    uploaded_at TIMESTAMP NOT NULL,
    change_note TEXT,
    PRIMARY KEY(paper_id, version_no),
    CONSTRAINT ck_version_no CHECK(version_no> 0)
);

CREATE TABLE review(
    review_id SERIAL PRIMARY KEY,
    paper_id INT NOT NULL REFERENCES paper(paper_id) ON DELETE CASCADE,
    reviewer_id INT NOT NULL REFERENCES reviewer(reviewer_id) ON DELETE RESTRICT,
    overall_score INT NOT NULL,
    recommendation VARCHAR(10) NOT NULL,
    comments_for_authors TEXT NOT NULL,
    confidential_comments TEXT,
    review_submission_date DATE NOT NULL,
    CONSTRAINT uq_review_paper_reviewer UNIQUE(paper_id, reviewer_id),
    CONSTRAINT ck_review_score CHECK(overall_score BETWEEN 1 AND 5),
    CONSTRAINT ck_review_recommendation CHECK(recommendation IN('accept','reject'))
);

CREATE INDEX idx_paper_track ON paper(track_id);
CREATE INDEX idx_paper_session ON paper(session_id);
CREATE INDEX idx_review_reviewer ON review(reviewer_id);
CREATE VIEW accepted_paper_schedule AS
SELECT p.paper_id, p.title AS paper_title, c.conference_id,
       c.acronym, t.name AS track_name, s.session_id,
       s.title AS session_title, s.session_date, s.start_time,
       s.end_time, s.room_label,
       ch.given_name ||' '|| ch.surname AS chair_name,
       ca.given_name ||' '|| ca.surname AS corresponding_author_name,
       ca.email AS corresponding_author_email
FROM paper p
JOIN conference_session s ON s.session_id= p.session_id
JOIN conference c ON c.conference_id =s.conference_id
JOIN track t ON t.track_id=p.track_id
JOIN app_user ch ON ch.user_id= s.chair_id
JOIN paper_author pa ON pa.paper_id= p.paper_id AND pa.is_corresponding
JOIN app_user ca ON ca.user_id= pa.author_id;

CREATE FUNCTION trg_review_no_self_review() RETURNS trigger AS $$
BEGIN
    IF EXISTS(SELECT 1 FROM paper_author WHERE paper_id = NEW.paper_id AND author_id = NEW.reviewer_id)
        THEN RAISE EXCEPTION 'Self-review rejected: user % is an author of paper %',
            NEW.reviewer_id, NEW.paper_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER review_no_self_review
BEFORE INSERT OR UPDATE OF paper_id, reviewer_id ON review
FOR EACH ROW EXECUTE FUNCTION trg_review_no_self_review();

CREATE FUNCTION trg_author_not_reviewer() RETURNS trigger AS $$
BEGIN
    IF EXISTS(SELECT 1 FROM review WHERE paper_id = NEW.paper_id AND reviewer_id = NEW.author_id)
        THEN RAISE EXCEPTION 'Author change rejected: user % has reviewed paper % and cannot be its author',
            NEW.author_id, NEW.paper_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER author_not_reviewer
BEFORE INSERT OR UPDATE OF paper_id, author_id ON paper_author
FOR EACH ROW EXECUTE FUNCTION trg_author_not_reviewer();

CREATE FUNCTION trg_paper_session_valid() RETURNS trigger AS $$
BEGIN
    IF NEW.session_id IS NOT NULL THEN
        IF NEW.status <> 'accepted'
            THEN RAISE EXCEPTION 'Session assignment rejected: paper % has status "%" but only accepted papers can be scheduled',
                NEW.paper_id, NEW.status USING ERRCODE = 'check_violation';
        END IF;
        IF(SELECT conference_id FROM track WHERE track_id = NEW.track_id)<>(SELECT conference_id FROM conference_session WHERE session_id = NEW.session_id)
            THEN RAISE EXCEPTION 'Session assignment rejected: the track of paper % and session % belong to different conferences',
                NEW.paper_id, NEW.session_id USING ERRCODE = 'check_violation';
        END IF;
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER paper_session_valid
BEFORE INSERT OR UPDATE OF track_id, session_id, status ON paper
FOR EACH ROW EXECUTE FUNCTION trg_paper_session_valid();

CREATE FUNCTION trg_session_conference_change() RETURNS trigger AS $$
BEGIN
    IF NEW.conference_id <> OLD.conference_id AND EXISTS(SELECT 1 FROM paper p JOIN track t ON t.track_id = p.track_id WHERE p.session_id = NEW.session_id AND t.conference_id <> NEW.conference_id)
        THEN RAISE EXCEPTION 'Session change rejected: session % holds papers from another conference',
            NEW.session_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER session_conference_change
BEFORE UPDATE OF conference_id ON conference_session
FOR EACH ROW EXECUTE FUNCTION trg_session_conference_change();

CREATE FUNCTION trg_track_conference_change() RETURNS trigger AS $$
BEGIN
    IF NEW.conference_id <> OLD.conference_id AND EXISTS(SELECT 1 FROM paper p JOIN conference_session s ON s.session_id = p.session_id WHERE p.track_id = NEW.track_id AND s.conference_id <> NEW.conference_id)
        THEN RAISE EXCEPTION 'Track change rejected: papers of track % are scheduled in sessions of another conference',
            NEW.track_id USING ERRCODE = 'check_violation';
    END IF;
    RETURN NEW;
END $$ LANGUAGE plpgsql;

CREATE TRIGGER track_conference_change
BEFORE UPDATE OF conference_id ON track
FOR EACH ROW EXECUTE FUNCTION trg_track_conference_change();
