import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ReviewService:
    def __init__(self, db_path: str = "database/land_course.db"):
        self.db_path = Path(db_path)
        self._init_db()

    def _init_db(self):
        """Инициализация базы данных"""
        try:
            self.db_path.parent.mkdir(exist_ok=True)
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS reviews (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        photo_url TEXT NOT NULL UNIQUE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn.commit()
        except Exception as e:
            logger.error(f"Database init error: {e}")

    async def add_review(self, photo_url: str) -> bool:
        """Добавление отзыва"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "INSERT INTO reviews (photo_url) VALUES (?)",
                    (photo_url,)
                )
                conn.commit()
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"Duplicate photo: {photo_url}")
            return False
        except Exception as e:
            logger.error(f"Add review error: {e}")
            return False

    async def get_all_reviews(self) -> list[str]:
        """Получение всех отзывов"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT photo_url FROM reviews ORDER BY created_at DESC"
                )
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Get reviews error: {e}")
            return []
    
    async def get_reviews_for_deletion(self) -> list[tuple[int, str]]:
        """Получение ID и URL отзывов для удаления"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT id, photo_url FROM reviews ORDER BY id DESC LIMIT 50"
                )
                return [(row['id'], row['photo_url']) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting reviews for deletion: {e}")
            return []

    async def delete_review(self, review_id: int) -> bool:
        """Удаление отзыва по ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "DELETE FROM reviews WHERE id = ?",
                    (review_id,)
                )
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting review: {e}")
            return False
        
    async def get_photo_url(self, review_id: int) -> str | None:
        """Получить URL фото по ID отзыва"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT photo_url FROM reviews WHERE id = ?",
                    (review_id,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting photo URL: {e}")
            return None
        
    async def delete_review_and_reset_ids(self, review_id: int) -> bool:
        """Удаление отзыва с перенумерацией оставшихся"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("DELETE FROM reviews WHERE id = ?", (review_id,))
                
                conn.execute("""
                    UPDATE reviews 
                    SET id = id - 1 
                    WHERE id > ?
                """, (review_id,))
                
                conn.execute("""
                    UPDATE sqlite_sequence 
                    SET seq = (SELECT MAX(id) FROM reviews) 
                    WHERE name = 'reviews'
                """)
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error in delete_and_reset: {e}")
            return False
        

    async def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            question TEXT NOT NULL,
            admin_id INTEGER,
            answer TEXT,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        self.conn.commit()

    async def create_ticket(self, user_id: int, username: str, question: str):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO support_tickets (user_id, username, question)
        VALUES (?, ?, ?)
        ''', (user_id, username, question))
        self.conn.commit()
        return cursor.lastrowid

    async def get_open_tickets(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * FROM support_tickets WHERE status = "open"')
        return cursor.fetchall()

    async def add_answer(self, ticket_id: int, admin_id: int, answer: str):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE support_tickets 
        SET admin_id = ?, answer = ?, status = 'closed'
        WHERE id = ?
        ''', (admin_id, answer, ticket_id))
        self.conn.commit()



class Database:
    def __init__(self):
        self.conn = sqlite3.connect('database/land_course.db')
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            full_name TEXT,
            question TEXT NOT NULL,
            status TEXT DEFAULT 'open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        cursor.execute("PRAGMA table_info(support_tickets)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'full_name' not in columns:
            cursor.execute("ALTER TABLE support_tickets ADD COLUMN full_name TEXT")
        
        self.conn.commit()

    def create_ticket(self, user_id: int, username: str, full_name: str, question: str):
        cursor = self.conn.cursor()
        cursor.execute('''
        INSERT INTO support_tickets (user_id, username, full_name, question)
        VALUES (?, ?, ?, ?)
        ''', (user_id, username, full_name, question))
        self.conn.commit()
        return cursor.lastrowid

    def get_open_tickets(self) -> list[dict]:
        """Возвращает список открытых тикетов"""
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT id, user_id, username, full_name, question 
        FROM support_tickets 
        WHERE status = 'open'
        ORDER BY created_at DESC
        ''')
        return [
            {
                'id': row[0],
                'user_id': row[1],
                'username': row[2] or "NoUsername",
                'full_name': row[3] or "Без имени",
                'question': row[4]
            }
            for row in cursor.fetchall()
        ]
        
    def get_ticket(self, ticket_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
        SELECT id, user_id, username, full_name, question 
        FROM support_tickets 
        WHERE id = ? AND status = 'open'
        ''', (ticket_id,))
        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'user_id': row[1],
                'username': row[2],
                'full_name': row[3],
                'question': row[4]
            }
        return None
        
    def close_ticket(self, ticket_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
        UPDATE support_tickets SET status = 'closed' WHERE id = ?
        ''', (ticket_id,))
        self.conn.commit()    
    
    def delete_user_messages(self, user_id: int):
        cursor = self.conn.cursor()
        cursor.execute('''
        DELETE FROM support_tickets 
        WHERE user_id = ? AND status = 'open'
        ''', (user_id,))
        self.conn.commit()
        return cursor.rowcount
    

    def get_user_message_count(self, user_id: int) -> int:
        """Возвращает количество сообщений пользователя"""
        cursor = self.conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE user_id = ?', (user_id,))
        return cursor.fetchone()[0]

    def delete_old_messages(self, user_id: int, keep_count: int = 5):
        """Удаляет старые сообщения, оставляя только keep_count последних"""
        cursor = self.conn.cursor()
        cursor.execute('''
        DELETE FROM support_tickets 
        WHERE user_id = ? AND id NOT IN (
            SELECT id FROM support_tickets 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT ?
        )
        ''', (user_id, user_id, keep_count))
        self.conn.commit()




def test_db():
    db = Database()
    ticket_id = db.create_ticket(
        user_id=12345,
        username="test_user",
        full_name="Тестовый Пользователь",
        question="Тестовый вопрос"
    )
    print(f"Создан тикет #{ticket_id}")
    
    ticket = db.get_ticket(ticket_id)
    print(f"Получен тикет: {ticket}")
    
    db.get_ticket(ticket_id)
    print(f"Тикет #{ticket_id} закрыт")

if __name__ == "__main__":
    test_db()