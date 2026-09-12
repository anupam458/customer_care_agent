import psycopg2
import psycopg2.extras
from pgvector.psycopg2 import register_vector
from dotenv import load_dotenv
import os
from pathlib import Path

# Load .env from the exact directory database.py lives in
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

DB_URL = os.getenv("DATABASE_URL") or os.getenv("COCKROACH_URI")

if not DB_URL:
    raise ValueError(f"❌ DATABASE_URL is missing! Checked file path: {env_path}")

def get_connection():
    conn = psycopg2.connect(DB_URL)
    try:
        register_vector(conn)
    except Exception:
        pass
    return conn

def init_db():
    raw_conn = psycopg2.connect(DB_URL)
    cur = raw_conn.cursor()
    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    raw_conn.commit()
    cur.close()
    raw_conn.close()

    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS support_memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            embedding VECTOR(3072),
            created_at TIMESTAMP DEFAULT now()
        );
    """)
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_memories_customer
        ON support_memories (customer_id);
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database initialized.")

def store_memory(customer_id, role, content, embedding):
    conn = get_connection()
    cur = conn.cursor()
    embedding_str = '[' + ','.join(map(str, embedding)) + ']'
    cur.execute("""
        INSERT INTO support_memories (customer_id, role, content, embedding)
        VALUES (%s, %s, %s, %s::VECTOR)
    """, (customer_id, role, content, embedding_str))
    conn.commit()
    cur.close()
    conn.close()

def search_memories(customer_id, query_embedding, limit=5):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
    cur.execute("""
        SELECT role, content, created_at
        FROM support_memories
        WHERE customer_id = %s AND embedding IS NOT NULL
        ORDER BY embedding <-> %s::VECTOR
        LIMIT %s
    """, (customer_id, embedding_str, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows

def get_history(customer_id, limit=20):
    conn = get_connection()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT role, content, created_at
        FROM support_memories
        WHERE customer_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """, (customer_id, limit))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return list(reversed(rows))