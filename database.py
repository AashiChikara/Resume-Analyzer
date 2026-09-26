import os

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Check your .env file.")


def get_connection():
    """
    Open a new database connection.
    We open one connection per request instead of using a connection pool,
    which is simpler to understand even though a pool is more efficient
    at larger scale.
    RealDictCursor makes rows come back as dictionaries (e.g. row["id"])
    instead of plain tuples.
    """
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)


def init_db():
    """
    Create all tables if they don't already exist yet.
    Safe to call every time the app starts.
    """
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS resumes (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            filename TEXT,
            extracted_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS analyses (
            id SERIAL PRIMARY KEY,
            resume_id INTEGER REFERENCES resumes(id),
            score FLOAT,
            strengths TEXT[],
            weaknesses TEXT[],
            suggestions TEXT[],
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS job_descriptions (
            id SERIAL PRIMARY KEY,
            resume_id INTEGER REFERENCES resumes(id),
            job_description TEXT NOT NULL,
            match_score FLOAT,
            matching_skills TEXT[],
            missing_skills TEXT[],
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()