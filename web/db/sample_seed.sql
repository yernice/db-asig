-- Small sample data for developing and testing the web application locally.
-- Replace with the team's full seed script (Part 1) before deploying.
-- Explicit IDs are used, so the sequences are moved forward at the end (setval).

INSERT INTO app_user (user_id, given_name, surname, email, affiliation, country, phone_number) VALUES
 (1, 'Arman',  'Armanov',   'arman.armanov@example.com',   'Nazarbayev University', 'Kazakhstan', '+77010000001'),
 (2, 'Amina',  'Aminova',   'amina.aminova@example.com',   'Nazarbayev University', 'Kazakhstan', '+77010000002'),
 (3, 'Dana',   'Bekova',    'dana.bekova@example.com',     'KBTU',                  'Kazakhstan', '+77010000003'),
 (4, 'Timur',  'Sadykov',   'timur.sadykov@example.com',   'Astana IT University',  'Kazakhstan', '+77010000004'),
 (5, 'Aliya',  'Nurlanova', 'aliya.nurlanova@example.com', 'Satbayev University',   'Kazakhstan', '+77010000005'),
 (6, 'Ruslan', 'Omarov',    'ruslan.omarov@example.com',   'ETH Zurich',            'Switzerland','+41000000006'),
 (7, 'Saule',  'Kassymova', 'saule.kassymova@example.com', 'KIMEP',                 'Kazakhstan', '+77010000007'),
 (8, 'Erlan',  'Zhakupov',  'erlan.zhakupov@example.com',  'TU Munich',             'Germany',    '+49000000008');

-- authors: 1, 2, 5, 6, 8   reviewers: 1, 3, 4, 5, 7   both roles: 1, 5
INSERT INTO author (author_id, orcid) VALUES
 (1, '0000-0001-0000-0001'), (2, NULL), (5, '0000-0001-0000-0005'), (6, NULL), (8, '0000-0001-0000-0008');
INSERT INTO author_research_area VALUES
 (1, 'Databases'), (1, 'Query Processing'), (2, 'Information Retrieval'), (5, 'Machine Learning'),
 (6, 'Distributed Systems'), (8, 'Machine Learning'), (8, 'Computer Vision');

INSERT INTO reviewer (reviewer_id, years_experience) VALUES (1, 4), (3, 10), (4, 5), (5, 2), (7, 1);
INSERT INTO reviewer_expertise VALUES
 (1, 'Databases'), (3, 'Databases'), (3, 'Machine Learning'), (4, 'Databases'), (5, 'Machine Learning'), (7, 'Databases');

INSERT INTO conference (conference_id, name, acronym, description, city, country, start_date, end_date, submission_deadline, review_deadline) VALUES
 (1, 'Astana Database Conference 2026', 'ADBC26', 'Data management research.', 'Astana', 'Kazakhstan', '2026-06-01', '2026-06-03', '2026-03-01', '2026-04-15'),
 (2, 'Central Asia Machine Learning 2026', 'CAML26', 'Machine learning research.', 'Almaty', 'Kazakhstan', '2026-07-10', '2026-07-12', '2026-04-01', '2026-05-15');
INSERT INTO conference_host VALUES (1, 'Nazarbayev University'), (2, 'KBTU'), (2, 'Satbayev University');
INSERT INTO conference_reviewer VALUES (1, 1), (1, 3), (1, 4), (1, 5), (1, 7), (2, 1), (2, 3), (2, 4);

INSERT INTO track (track_id, conference_id, name, description, research_area, coordinator_id) VALUES
 (1, 1, 'Data Management', 'Storage, indexing and query processing.', 'Databases', 3),
 (2, 1, 'Data Visualization', 'Visual analytics (no papers yet).', 'Visualization', 4),
 (3, 2, 'Machine Learning', 'Learning methods and applications.', 'Machine Learning', 3);

INSERT INTO conference_session (session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
 (1, 1, 'Query Processing I',   '2026-06-02', '09:00', '10:30', 'Hall A', 4),
 (2, 1, 'Open Session (empty)', '2026-06-02', '11:00', '12:30', 'Hall B', 5),
 (3, 2, 'Learning Systems',     '2026-07-11', '14:00', '15:30', 'Room 3', 3);

INSERT INTO paper (paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
 (1, 1, 'Adaptive Join Ordering for Analytical Queries', 'We study cost-based join ordering for analytical workloads.', '2026-02-10', 'accepted', 1),
 (2, 1, 'Learned Index Structures in Practice', 'An evaluation of learned indexes against B+-trees.', '2026-02-12', 'accepted', NULL),
 (3, 3, 'Machine Learning for Crop Yield Prediction', 'We apply Machine Learning models to satellite data.', '2026-03-20', 'under review', NULL),
 (4, 1, 'A Survey of Spatial Databases', 'A survey of spatial indexing methods.', '2026-02-20', 'withdrawn', NULL),
 (5, 3, 'Federated Learning on Edge Devices', 'Privacy-preserving training across devices.', '2026-03-25', 'withdrawn', NULL),
 (6, 3, 'Graph Neural Networks for Traffic', 'Traffic forecasting with GNNs.', '2026-03-15', 'rejected', NULL),
 (7, 1, 'Transaction Processing on SSDs', 'Concurrency control tuned for flash storage.', '2026-02-27', 'submitted', NULL),
 (8, 3, 'Explainable Models for Credit Scoring', 'Interpretable machine learning for finance.', '2026-03-28', 'accepted', 3);

INSERT INTO paper_author (paper_id, author_id, author_position, is_corresponding) VALUES
 (1, 1, 1, TRUE), (1, 6, 2, FALSE),
 (2, 5, 1, TRUE),
 (3, 8, 1, TRUE), (3, 1, 2, FALSE),
 (4, 2, 1, TRUE),
 (5, 2, 1, TRUE), (5, 6, 2, FALSE),
 (6, 6, 1, TRUE),
 (7, 8, 1, TRUE),
 (8, 2, 1, TRUE), (8, 5, 2, FALSE);

INSERT INTO paper_keyword VALUES
 (1, 'query optimization'), (1, 'joins'), (2, 'learned indexes'), (3, 'machine learning'), (3, 'agriculture'),
 (4, 'spatial data'), (5, 'federated learning'), (6, 'graph neural networks'), (7, 'transactions'), (8, 'explainability');

INSERT INTO paper_version (paper_id, version_no, file_location, uploaded_at, change_note) VALUES
 (1, 1, 'papers/1/v1.pdf', '2026-02-10 10:00', NULL),
 (1, 2, 'papers/1/v2.pdf', '2026-04-20 18:30', 'Camera-ready'),
 (2, 1, 'papers/2/v1.pdf', '2026-02-12 09:15', NULL),
 (3, 1, 'papers/3/v1.pdf', '2026-03-20 12:00', NULL),
 (3, 3, 'papers/3/v3.pdf', '2026-04-02 16:45', 'Revised experiments'),
 (4, 1, 'papers/4/v1.pdf', '2026-02-20 11:00', NULL),
 (5, 1, 'papers/5/v1.pdf', '2026-03-25 08:00', NULL),
 (6, 1, 'papers/6/v1.pdf', '2026-03-15 14:20', NULL),
 (7, 1, 'papers/7/v1.pdf', '2026-02-27 17:05', NULL),
 (8, 1, 'papers/8/v1.pdf', '2026-03-28 13:10', NULL);

-- Reviewer 7 (Saule) has no reviews. Nobody reviews a paper they authored.
INSERT INTO review (review_id, paper_id, reviewer_id, overall_score, recommendation, comments_for_authors, confidential_comments, review_submission_date) VALUES
 (1, 1, 3, 5, 'accept', 'Clear contribution.', NULL, '2026-04-01'),
 (2, 1, 4, 4, 'accept', 'Good experiments.', NULL, '2026-04-03'),
 (3, 1, 5, 4, 'accept', 'Minor typos.', NULL, '2026-04-05'),
 (4, 2, 3, 4, 'accept', 'Useful comparison.', NULL, '2026-04-02'),
 (5, 2, 4, 3, 'accept', 'Needs more datasets.', 'Borderline.', '2026-04-06'),
 (6, 3, 4, 3, 'reject', 'Baselines are weak.', NULL, '2026-05-01'),
 (7, 4, 4, 2, 'reject', 'Survey is incomplete.', NULL, '2026-03-30'),
 (8, 6, 3, 2, 'reject', 'Limited novelty.', NULL, '2026-04-20'),
 (9, 6, 1, 1, 'reject', 'Results not reproducible.', NULL, '2026-04-22'),
 (10, 8, 3, 5, 'accept', 'Excellent.', NULL, '2026-04-28'),
 (11, 8, 4, 4, 'accept', 'Solid work.', NULL, '2026-04-29');

-- Move SERIAL counters past the explicit IDs, so new rows created by the app get fresh IDs.
SELECT setval(pg_get_serial_sequence('app_user', 'user_id'),              (SELECT MAX(user_id) FROM app_user));
SELECT setval(pg_get_serial_sequence('conference', 'conference_id'),      (SELECT MAX(conference_id) FROM conference));
SELECT setval(pg_get_serial_sequence('track', 'track_id'),                (SELECT MAX(track_id) FROM track));
SELECT setval(pg_get_serial_sequence('conference_session', 'session_id'), (SELECT MAX(session_id) FROM conference_session));
SELECT setval(pg_get_serial_sequence('paper', 'paper_id'),                (SELECT MAX(paper_id) FROM paper));
SELECT setval(pg_get_serial_sequence('review', 'review_id'),              (SELECT MAX(review_id) FROM review));
