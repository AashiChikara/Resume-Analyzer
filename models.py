from database import get_connection


def get_or_create_guest_user() -> int:
    """
    This project has no login system, so every resume is attached to one
    shared 'guest' user. A real multi-user app would replace this with
    an actual authenticated user id.
    """
    conn = get_connection()
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
    conn.close()
    return user_id


def save_resume(filename: str, extracted_text: str) -> int:
    """Save a resume and return its new id."""
    user_id = get_or_create_guest_user()

    conn = get_connection()
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
    conn.close()
    return resume_id


def save_analysis(resume_id: int, strengths: list, weaknesses: list,
                   suggestions: list, score: float = None):
    conn = get_connection()
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
    conn.close()


def save_job_match(resume_id: int, job_description: str, match_score: float,
                    matching_skills: list, missing_skills: list):
    conn = get_connection()
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
    conn.close()


def get_history() -> list[dict]:
    """
    Return every resume along with its most recent analysis and most
    recent job match, newest resumes first.
    We fetch resumes first, then loop and fetch related rows one by one —
    less efficient than a single complex join, but much easier to read
    and explain.
    """
    conn = get_connection()
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
    conn.close()
    return history