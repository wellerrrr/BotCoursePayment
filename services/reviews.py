import mysql.connector
import logging
from config import config

logger = logging.getLogger(__name__)

def get_mysql_conn():
    return mysql.connector.connect(**config.MYSQL_CONFIG)

class ReviewService:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Инициализация базы данных"""
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS reviews (
                    id INT PRIMARY KEY AUTO_INCREMENT,
                    photo_url VARCHAR(255) NOT NULL UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Database init error: {e}")

    async def add_review(self, photo_url: str) -> bool:
        """Добавление отзыва"""
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO reviews (photo_url) VALUES (%s)",
                (photo_url,)
            )
            conn.commit()
            conn.close()
            return True
        except mysql.connector.errors.IntegrityError:
            logger.warning(f"Duplicate photo: {photo_url}")
            return False
        except Exception as e:
            logger.error(f"Add review error: {e}")
            return False

    async def get_all_reviews(self) -> list[str]:
        """Получение всех отзывов"""
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT photo_url FROM reviews ORDER BY created_at DESC"
            )
            result = [row[0] for row in cursor.fetchall()]
            conn.close()
            return result
        except Exception as e:
            logger.error(f"Get reviews error: {e}")
            return []
    
    async def get_reviews_for_deletion(self) -> list[tuple[int, str]]:
        """Получение ID и URL отзывов для удаления"""
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, photo_url FROM reviews ORDER BY id DESC LIMIT 50"
            )
            result = cursor.fetchall()
            conn.close()
            return [(row[0], row[1]) for row in result]
        except Exception as e:
            logger.error(f"Error getting reviews for deletion: {e}")
            return []

    async def delete_review(self, review_id: int) -> bool:
        """Удаление отзыва по ID"""
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM reviews WHERE id = %s",
                (review_id,)
            )
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
            return deleted
        except Exception as e:
            logger.error(f"Error deleting review: {e}")
            return False
        
    async def get_photo_url(self, review_id: int) -> str | None:
        """Получить URL фото по ID отзыва"""
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT photo_url FROM reviews WHERE id = %s",
                (review_id,)
            )
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting photo URL: {e}")
            return None
        
    async def delete_review_and_reset_ids(self, review_id: int) -> bool:
        """Удаление отзыва с перенумерацией оставшихся (MySQL: просто удаляем)"""
        try:
            conn = get_mysql_conn()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM reviews WHERE id = %s", (review_id,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Error in delete_and_reset: {e}")
            return False