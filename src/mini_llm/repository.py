from src.mini_llm.database import DatabaseManager


class ChatRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self.db = db

    def create_session(self, title: str) -> dict:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO chat_sessions (title) VALUES (%s)",
                    (title,),
                )
                session_id = cursor.lastrowid
                cursor.execute(
                    """
                    SELECT id, title, created_at, updated_at
                    FROM chat_sessions
                    WHERE id = %s
                    """,
                    (session_id,),
                )
                return cursor.fetchone()

    def list_sessions(self) -> list[dict]:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        s.id,
                        s.title,
                        s.created_at,
                        s.updated_at,
                        (
                            SELECT COUNT(*)
                            FROM chat_messages m
                            WHERE m.session_id = s.id
                        ) AS message_count,
                        (
                            SELECT m2.content
                            FROM chat_messages m2
                            WHERE m2.session_id = s.id
                            ORDER BY m2.id DESC
                            LIMIT 1
                        ) AS last_message
                    FROM chat_sessions s
                    ORDER BY s.updated_at DESC, s.id DESC
                    """
                )
                return cursor.fetchall()

    def get_session(self, session_id: int) -> dict | None:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, title, created_at, updated_at
                    FROM chat_sessions
                    WHERE id = %s
                    """,
                    (session_id,),
                )
                return cursor.fetchone()

    def update_session_title(self, session_id: int, title: str) -> None:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET title = %s
                    WHERE id = %s
                    """,
                    (title, session_id),
                )

    def delete_session(self, session_id: int) -> int:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM chat_sessions
                    WHERE id = %s
                    """,
                    (session_id,),
                )
                return int(cursor.rowcount)

    def touch_session(self, session_id: int) -> None:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE chat_sessions
                    SET updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                    """,
                    (session_id,),
                )

    def add_message(self, session_id: int, role: str, content: str) -> dict:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO chat_messages (session_id, role, content)
                    VALUES (%s, %s, %s)
                    """,
                    (session_id, role, content),
                )
                message_id = cursor.lastrowid
                cursor.execute(
                    """
                    SELECT id, session_id, role, content, created_at
                    FROM chat_messages
                    WHERE id = %s
                    """,
                    (message_id,),
                )
                return cursor.fetchone()

    def list_messages(self, session_id: int) -> list[dict]:
        with self.db.connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, session_id, role, content, created_at
                    FROM chat_messages
                    WHERE session_id = %s
                    ORDER BY id ASC
                    """,
                    (session_id,),
                )
                return cursor.fetchall()
