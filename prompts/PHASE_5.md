# PHASE 5 — Backend APIs and Family Room logic

GOAL: Complete, secured backend for auth, rooms, voting, comparison and roadmap.

TASKS:
1. Auth: register/login with JWT (access+refresh), roles student|parent|counsellor|admin, password hashing (argon2/bcrypt), rate limiting (slowapi), consent timestamp stored at registration, DELETE /students/me removes all personal data.
2. Rooms: POST /rooms (student creates; 6-char code), POST /rooms/{code}/join (parent/counsellor), membership checks on every room endpoint.
3. Criteria weights: PUT /rooms/{code}/weights per member for {cost, duration, salary, local_jobs, distance} (sum normalised). Store per user.
4. Compare: POST /compare takes occupation_ids + weights, returns normalised criterion scores, weighted total per member and a combined family score, and "where you disagree" highlights (largest weight/score divergence).
5. Votes + consensus: POST /rooms/{code}/vote (score 1-5 per option), GET /rooms/{code}/consensus returns ranking, agreement index (e.g. 1 - normalised variance) and suggested next step (e.g. "discuss cost vs salary").
6. Roadmap: GET /roadmap/{occupation_id}?district= returns ordered steps (eligibility check -> course -> nearest centres -> certification body/NSQF level -> apprenticeship/placement notes -> expected timeline and fees) with source + is_demo flags.
7. Counsellor endpoints: cohort list (only assigned students), override recommendation with note (audit-logged).
8. OpenAPI polish: tags, examples; standard error schema; request-id in logs.
9. Tests: integration tests for every route including authorisation failures (a parent must not read another room), weights normalisation, consensus math, deletion.

ACCEPTANCE: `pytest backend/tests/integration` passes; OpenAPI docs render; a scripted scenario (scripts/demo_flow.py) registers student+parent, creates room, votes, prints consensus.
DO NOT: expose other users' data; store raw passwords or unnecessary personal fields.
