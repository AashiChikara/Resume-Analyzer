from database import get_connection, release_connection

# Cache the guest user's id after the first lookup/creation, so we don't
# run a SELECT (or INSERT) against the users table on every single save.
_guest_user_id_cache: int | None = None


def get_or_create_guest_user() -> int:
    global _guest_user_id_cache

    if _guest_user_id_cache is not None:
        return _guest_user_id_cache

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM users WHERE email = %s", ("guest@example.com",))
        row = cur.fetchone()

        if row:
            user_id = row["id"]
        else:
            cur.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id",
                ("Guest", "guest@example.com"),
            )
            user_id = cur.fetchone()["id"]
            conn.commit()

        cur.close()
    finally:
        release_connection(conn)

    _guest_user_id_cache = user_id
    return user_id


def save_resume(filename: str, extracted_text: str) -> int:
    user_id = get_or_create_guest_user()

    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO resumes (user_id, filename, extracted_text)
            VALUES (%s, %s, %s)
            RETURNING id
            """,
            (user_id, filename, extracted_text),
        )
        resume_id = cur.fetchone()["id"]
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)

    return resume_id


def save_analysis(resume_id: int, strengths: list, weaknesses: list,
                   suggestions: list, score: float = None):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO analyses (resume_id, score, strengths, weaknesses, suggestions)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (resume_id, score, strengths, weaknesses, suggestions),
        )
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)


def save_job_match(resume_id: int, job_description: str, match_score: float,
                    matching_skills: list, missing_skills: list):
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO job_descriptions
                (resume_id, job_description, match_score, matching_skills, missing_skills)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (resume_id, job_description, match_score, matching_skills, missing_skills),
        )
        conn.commit()
        cur.close()
    finally:
        release_connection(conn)


def get_history() -> list[dict]:
    conn = get_connection()
    try:
        cur = conn.cursor()

        cur.execute("SELECT id, filename, created_at FROM resumes ORDER BY created_at DESC")
        resumes = cur.fetchall()

        history = []
        for resume in resumes:
            cur.execute(
                """
                SELECT score, strengths, weaknesses, suggestions
                FROM analyses WHERE resume_id = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (resume["id"],),
            )
            analysis = cur.fetchone()

            cur.execute(
                """
                SELECT match_score, matching_skills, missing_skills
                FROM job_descriptions WHERE resume_id = %s
                ORDER BY created_at DESC LIMIT 1
                """,
                (resume["id"],),
            )
            match = cur.fetchone()

            history.append({
                "resume_id": resume["id"],
                "filename": resume["filename"],
                "created_at": resume["created_at"].isoformat() if resume["created_at"] else None,
                "strengths": analysis["strengths"] if analysis else [],
                "weaknesses": analysis["weaknesses"] if analysis else [],
                "suggestions": analysis["suggestions"] if analysis else [],
                "match_score": match["match_score"] if match else None,
                "matching_skills": match["matching_skills"] if match else [],
                "missing_skills": match["missing_skills"] if match else [],
            })

        cur.close()
    finally:
        release_connection(conn)

    return history