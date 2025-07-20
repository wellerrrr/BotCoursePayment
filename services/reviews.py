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