BEGIN;
INSERT INTO app_user(user_id,given_name,surname,email, affiliation,country, phone_number) VALUES
(1,'Notadnan','Yazici','notadnan.yazici@example.com','Istanbul Database University','Turkey','+905320000005'),
(2,'Amina','Aminova','amina.aminova@example.com','Nazarbayev University','Kazakhstan','+77010000002'),
(3,'Samadbek','Kuralov','samadbek.kuralov@example.com','Old Uzbekistan University','Uzbekistan','+998901000003'),
(4,'Azamat','Abduraimov','azamat.bedwars@example.com','Old Uzbekistan University','Uzbekistan','+998901000004'),
(5,'Arman','Armanov','arman.armanov@example.com','New Astana University','Kazakhstan','+77010000001'),
(6,'Tigran','Tigranovich','tigran.tigranovich@example.com', 'Tiger University of Armenia','Armenia','+37491000009'),
(7,'Merab','Dvalishvili','merab.dvalishvili@example.com','UFC University of Tbilisi','Georgia','+995555000007'),
(8,'Garry','Kaspersky','garry.kaspersky@example.com','CS and CHESS University','Azerbaijan','+994500000008'),
(9,'Wei','Dongming','wei.dongming@example.com','Great Mathematics University','China','+8613800000006'),
(10,'Rector','Gabdullin','rector.gabdullin@example.com','CBTU','Kazakhstan','+77010000010');

INSERT INTO author(author_id, orcid) VALUES
(1,'0000-0001-1111-0001'),
(2,'0000-0002-2222-0002'),
(3,NULL),
(5,'0000-0003-3333-0003'),
(8,NULL),
(9,'0000-0004-4444-000X');

INSERT INTO author_research_area(author_id, area_label) VALUES
(1,'Machine Learning'),(1,'Databases'),
(2,'Machine Learning'),
(3,'Data Science'),
(5,'Virtual Reality'),(5,'Human-Computer Interaction'),
(8,'Virtual Reality'),
(9,'Mathematics'),(9,'Graph Theory');

INSERT INTO reviewer(reviewer_id, years_experience) VALUES
(1, 6), (4, 9), (5, 5), (6, 8), (7, 2), (8, 4), (10, 3);

INSERT INTO reviewer_expertise(reviewer_id, area_label) VALUES
(1,'Databases'), (1,'Machine Learning'),
(4,'Databases'), (4,'Discrete Mathematics'),
(5,'Virtual Reality'), (5,'Human-Computer Interaction'),
(6,'Machine Learning'), (6,'Mathematics'),
(7,'Databases'),
(8,'Virtual Reality'), (8,'Cryptography'),
(10,'Databases');

INSERT INTO conference(conference_id,name,acronym,description,city,country,start_date, end_date,submission_deadline,review_deadline) VALUES
(1,'Silk Road Conference on Machine Learning and Data Science', 'SRCML',
    'Models are trained, data is cleaned, and tea is drank.',
    'Astana','Kazakhstan','2027-04-14','2027-04-16','2026-10-01','2026-11-15'),
(2,'Supercell on Virtual Reality and Interaction', 'SVR',
    'Immersive technology research with cats.',
    'Istanbul','Turkey','2027-05-20','2027-05-22','2026-10-15','2026-12-01'),
(3,'Tashkent Workshop on Discrete Mathematics and Cryptography', 'TWDMC',
    'Graphs, proofs and secrets. Nobody has submitted anything yet.',
    'Tashkent','Uzbekistan','2027-09-08','2027-09-10','2027-03-01','2027-05-15');

INSERT INTO conference_host(conference_id, host_name) VALUES
(1,'New Astana University'), (1,'Nazarbayev University'),
(2,'Istanbul Database University'),
(3,'Old Uzbekistan University'), (3,'Tashkent University of Daribayev');

INSERT INTO conference_reviewer(conference_id, reviewer_id) VALUES
(1,1),(1,4),(1,6),(1,7),(1,10),
(2,4),(2,5),(2,6),(2,8),
(3,4),(3,8);

INSERT INTO track(track_id,conference_id,name,description,research_area, coordinator_id) VALUES
(1,1,'Machine Learning and Data Science','Learning algorithms, data cleaning and analytics.','Machine Learning', 1),
(2,1,'Mathematical Computing','Graphs, proofs and why 1+1=2.','Mathematics',4),
(3,1,'Quantum Computing','Empty and not empty until somebody submits a paper.','Quantum Computing',7),
(4,2,'Virtual and Augmented Reality','Headsets, avatars and avoiding motion sickness.','Virtual Reality',8),
(5,3,'Discrete Mathematics and Cryptography','BITCOINS, Combinatorics, codes and keeping secrets.','Cryptography',4);

INSERT INTO conference_session(session_id, conference_id, title, session_date, start_time, end_time, room_label, chair_id) VALUES
(1,1,'Machine Learning Morning (Caffeine Required)','2027-04-14', '09:00', '10:30', 'Hall A',6),
(2,1,'Poster Session and Free Tea','2027-04-15', '14:00', '15:30', 'Foyer',10),
(3,2,'VR Showcase (please dont steal)','2027-05-20', '10:00', '11:30', 'Bosphorus Room',5),
(4,2,'Closing Remarks and Coffee Debate','2027-05-22', '16:00', '17:00', 'Main Hall',8);

INSERT INTO paper(paper_id, track_id, title, abstract, submission_date, status, session_id) VALUES
(1, 1,'Gradient Descent Walks Into a Bar',
'We study something smart, very smart - look at the title. Some brain crushing words.',
'2026-08-12', 'accepted', 1),
(2, 1,'Automated Data Cleaning at Scale',
'Machine Alogs with super puper name Vacuum cleaner that does everyhting',
'2026-08-20', 'accepted', 1),
(3, 2,'Spectral Bounds for Sparse Graphs',
'We prove new eigenvalue(some stuff from linear algebra) bounds',
'2026-08-28', 'accepted', NULL),
(4, 1,'Neural Networks Predict Tomorrow''s Weather',
'Trained a network that forecasts tomorrow and report 67 percent accuracy.',
'2026-09-02', 'rejected', NULL),
(5, 2,'On the Convergence of Assignments and Deadlines',
'Model the probability that a assignment is finished before the submission deadline using Markov chains.',
'2026-09-15', 'under review', NULL),
(6, 1,'Fitting Language Models on a Smart Kettle',
'Compressed language models with MACHINE LEARNING techniques until they run on a kettle that also boils water at the same time.',
'2026-09-25', 'submitted', NULL),
(7, 1,'Reinforcement Learning for Parking Near the Bazaar',
'Agent learns to find a parking spot near a busy bazaar.',
'2026-08-15', 'withdrawn', NULL),
(8, 2,'Proof That Errors Are Inevitable',
'Showed every sufficiently long program contains an error, and so may this abstract.',
'2026-09-10', 'withdrawn', NULL),
(9, 4,'Avoiding Motion Sickness in Virtual Reality',
'Predicted and reduced cybersickness in headsets so that visitors can safely stroll through a virtual Grand Bazaar.',
'2026-09-20', 'accepted', 3),
(10,4,'Walking Through Walls in VR',
'Studied what happens when virtual walls are only suggestions.',
'2026-10-05', 'rejected', NULL);

INSERT INTO paper_author(paper_id, author_id, author_position, is_corresponding) VALUES
(1, 2, 1, TRUE), (1, 3, 2, FALSE),
(2, 3, 1, TRUE), (2, 9, 2, FALSE), (2, 5, 3, FALSE),
(3, 9, 1, TRUE),
(4, 5, 1, TRUE), (4, 8, 2, FALSE),
(5, 8, 1, TRUE), (5, 1, 2, FALSE),
(6, 3, 1, TRUE),
(7, 2, 1, TRUE), (7, 9, 2, FALSE),
(8, 2, 1, TRUE), (8, 1, 2, FALSE),
(9, 5, 1, TRUE), (9, 1, 2, FALSE),
(10,9, 1, TRUE), (10,2, 2, FALSE);

INSERT INTO paper_keyword(paper_id, keyword) VALUES
(1,'optimization'), (1,'deep learning'),
(2,'data cleaning'), (2,'data quality'),
(3,'spectral graph theory'),
(4,'forecasting'),
(5,'markov chains'), (5,'deadlines'),
(6,'language models'), (6,'compression'),
(7,'reinforcement learning'), (7,'parking'),
(8,'program correctness'),
(9,'virtual reality'), (9,'cybersickness'),
(10,'virtual reality'), (10,'collision detection');

INSERT INTO paper_version(paper_id, version_no, file_location, uploaded_at, change_note) VALUES
(1, 1, 'papers/p001/v1.pdf', '2026-08-12 10:00', 'first submission'),
(1, 3, 'papers/p001/v3.pdf', '2026-11-01 14:20', 'camera-ready (v2 was lost in mouth of a dog)'),
(2, 1, 'papers/p002/v1.pdf', '2026-08-20 11:00', NULL),
(3, 1, 'papers/p003/v1.pdf', '2026-08-28 12:30', NULL),
(4, 1, 'papers/p004/v1.pdf', '2026-09-02 08:50', NULL),
(5, 1, 'papers/p005/v1.pdf', '2026-09-15 13:10', NULL),
(6, 1, 'papers/p006/v1.pdf', '2026-09-25 21:40', 'submitted five minutes before deadline'),
(7, 1, 'papers/p007/v1.pdf', '2026-08-15 09:00', NULL),
(8, 1, 'papers/p008/v1.pdf', '2026-09-10 15:30', NULL),
(9, 1, 'papers/p009/v1.pdf', '2026-09-20 10:20', NULL),
(10,1, 'papers/p010/v1.pdf', '2026-10-05 16:10', NULL);

INSERT INTO review(review_id, paper_id, reviewer_id, overall_score, recommendation,comments_for_authors, confidential_comments, review_submission_date) VALUES
(1,  1, 4,  5, 'accept', 'Nice','Hello','2026-10-20'),
(2,  1, 6,  4, 'accept', 'Super nice',NULL,'2026-10-22'),
(3,  2, 4,  4, 'accept', 'Super Mega Nice.',NULL,'2026-10-25'),
(4,  2, 10, 5, 'accept', 'Hyper Super Nega Nice',NULL,'2026-10-27'),
(5,  3, 6,  3, 'accept', 'Ultra Mega Super Nice','Thumbs up','2026-10-30'),
(6,  4, 6,  2, 'reject', 'Better luck next time', NULL,'2026-11-02'),
(7,  7, 1,  3, 'reject', 'Mehhhh', 'Whats up','2026-11-05'),
(8,  9, 4,  5, 'accept', 'Nicee', NULL,'2026-11-10'),
(9,  9, 8,  4, 'accept', '2x Nice', NULL, '2026-11-12'),
(10, 10,5,  2, 'reject', 'boooooohhhh', ';)', '2026-11-15');

SELECT setval(pg_get_serial_sequence('app_user','user_id'),(SELECT MAX(user_id) FROM app_user));
SELECT setval(pg_get_serial_sequence('conference','conference_id'),(SELECT MAX(conference_id) FROM conference));
SELECT setval(pg_get_serial_sequence('track','track_id'),(SELECT MAX(track_id) FROM track));
SELECT setval(pg_get_serial_sequence('conference_session','session_id'),(SELECT MAX(session_id) FROM conference_session));
SELECT setval(pg_get_serial_sequence('paper','paper_id'),(SELECT MAX(paper_id) FROM paper));
SELECT setval(pg_get_serial_sequence('review','review_id'),(SELECT MAX(review_id) FROM review));
COMMIT;