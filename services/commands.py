import sqlite3
import logging
from config import config

def init_db():
    try:
        conn = sqlite3.connect('database/land_course.db')
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            text TEXT NOT NULL
        )''')
        conn.commit()
        conn.close()
        logging.debug("База данных инициализирована")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при инициализации базы данных: {e}")

# Вызов инициализации базы данных
init_db()

# Получение всех сообщений из базы данных с сортировкой по title
def get_all_messages():
    try:
        conn = sqlite3.connect('database/land_course.db')
        c = conn.cursor()
        c.execute("SELECT id, title, text FROM messages ORDER BY title ASC")
        messages = c.fetchall()
        conn.close()
        logging.debug(f"Получено сообщений из базы: {len(messages)}")
        return messages
    except sqlite3.Error as e:
        logging.error(f"Ошибка при получении сообщений из базы: {e}")
        return []

# Поиск сообщения по title
def get_message_by_title(title: str):
    try:
        conn = sqlite3.connect('database/land_course.db')
        c = conn.cursor()
        c.execute("SELECT id, title, text FROM messages WHERE title = ? LIMIT 1", (title,))
        message = c.fetchone()
        conn.close()
        if message:
            logging.debug(f"Найдено сообщение с title='{title}'")
            return message
        else:
            logging.debug(f"Сообщение с title='{title}' не найдено")
            return None
    except sqlite3.Error as e:
        logging.error(f"Ошибка при поиске сообщения с title='{title}': {e}")
        return None

# Обновление текста сообщения в базе данных
def update_message_text(message_id: int, new_text: str):
    try:
        conn = sqlite3.connect('database/land_course.db')
        c = conn.cursor()
        c.execute("UPDATE messages SET text = ? WHERE id = ?", (new_text, message_id))
        conn.commit()
        conn.close()
        logging.debug(f"Сообщение с ID {message_id} обновлено")
    except sqlite3.Error as e:
        logging.error(f"Ошибка при обновлении сообщения: {e}")
        raise

def is_admin(user_id: int) -> bool:
    is_admin_user = user_id in config.ADMIN_IDS
    logging.debug(f"Проверка админа: user_id={user_id}, is_admin={is_admin_user}")
    return is_admin_user