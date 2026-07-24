import os
import psycopg
import uuid

DB_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres_user:postgres_password@postgres:5432/postgres"
)

def create_conversation(conversation_id: str | None = None) -> str:
    conversation_id = conversation_id or str(uuid.uuid4())

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(""" 
                INSERT INTO chat_conversations (conversation_id)
                VALUES (%s)
                ON CONFLICT (conversation_id) DO NOTHING
            """,
            (conversation_id,),
            )

    return conversation_id

def save_message(conversation_id: str, role: str, content: str, agent: str | None = None) -> None:
    conversation_id = conversation_id or str(uuid.uuid4())

    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO chat_messages (conversation_id, role, content, agent)
                VALUES (%s, %s, %s, %s)
            """,
            (conversation_id, role, content, agent)
            )

        with conn.cursor() as cur:
            cur.execute("""
                UPDATE chat_conversations
                SET updated_at = CURRENT_TIMESTAMP
                WHERE conversation_id = %s
            """,
            (conversation_id,)
            )

def load_messages(conversation_id: str) -> list[dict]:
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT role, content, agent, created_at
                FROM chat_messages
                WHERE conversation_id = %s
                ORDER BY created_at ASC, message_id ASC
            """,
            (conversation_id,),
            )

            rows = cur.fetchall()
        
    return [
        {
            "role" : row[0],
            "content" : row[1],
            "agent" : row[2],
            "created_at" : row[3].isoformat(),
        } 
        for row in rows
    ]

def get_sidebar_conversations() -> list[dict]:
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    conversation_id,
                    title,
                    updated_at
                FROM chat_conversations
                ORDER BY updated_at DESC
                """
            )

            rows = cur.fetchall()

    return [
        {
            "conversation_id": str(row[0]),
            "title": row[1],
            "updated_at": row[2].isoformat() if row[2] else None,
        }
        for row in rows
    ]

def clear_chat_history():
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                    TRUNCATE TABLE chat_messages, chat_conversations
                    RESTART IDENTITY CASCADE
                """
            )

def delete_conversation(conversation_id: str):
    with psycopg.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                    DELETE FROM chat_conversations 
                    WHERE conversation_id = %s
                """,
                (conversation_id,),
            )

hardcoded_title_query = """ 
                SELECT
                    c.conversation_id,
                    COALESCE(
                        SUBSTRING(first_msg.content FROM 1 FOR 40),
                        'New conversation'
                    ) AS title,
                    c.updated_at
                FROM chat_conversations c
                LEFT JOIN LATERAL (
                    SELECT m.content
                    FROM chat_messages m
                    WHERE m.conversation_id = c.conversation_id
                      AND m.role = 'user'
                    ORDER BY m.created_at ASC, m.message_id ASC
                    LIMIT 1
                ) first_msg ON TRUE
                ORDER BY c.updated_at DESC
                """