import os

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is missing. Check your .env file.")

# A connection pool keeps a small set of open connections ready to reuse,
# instead of opening a brand new TCP connection to PostgreSQL on every
# single query. minconn=1 keeps one connection always ready; maxconn=10
# caps how many can be open at once under load.
_connection_pool = psycopg2.pool.SimpleConnectionPool(
    minconn=1,
    maxconn=10,
    dsn=DATABASE_URL,
    cursor_factory=RealDictCursor,
)


def get_connection():
    """Borrow a connection from the pool."""
    return _connection_pool.getconn()


def release_connection(conn):
    """Return a connection to the pool instead of closing it."""
    _connection_pool.putconn(conn)


def init_db():
    """Create all tables if they don't already exist yet."""
    conn = get_connection()
    try:
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
    finally:
        release_connection(conn)