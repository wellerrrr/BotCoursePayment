from datetime import datetime
import sqlite3
import time
from aiogram import types


def init_db():
    conn = sqlite3.connect('database/land_course.db')
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        email TEXT UNIQUE,
        registration_date TEXT,
        registration_timestamp INTEGER
    )
    """)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_consents (
            user_id INTEGER PRIMARY KEY,
            data_consent BOOLEAN NOT NULL,
            offer_consent BOOLEAN NOT NULL,
            timestamp TEXT NOT NULL
        )
    ''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS user_links (
        user_id INTEGER PRIMARY KEY,
        invite_link TEXT,
        created_at INTEGER,
        created_date TEXT
    )''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS payments (
        user_id INTEGER,
        payment_id TEXT,
        amount REAL,
        currency TEXT,
        payment_timestamp INTEGER,
        payment_date TEXT,
        payment_method TEXT,
        payment_status TEXT NOT NULL,
        PRIMARY KEY (user_id, payment_id)
    )''')

        
    # Добавляем колонку created_date если её нет
    cursor.execute("PRAGMA table_info(user_links)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'created_date' not in columns:
        cursor.execute("ALTER TABLE user_links ADD COLUMN created_date TEXT")
    
    conn.commit()
    conn.close()

init_db()

def save_or_update_user(user_id: int, username: str = None, first_name: str = None, 
                       last_name: str = None, email: str = None):
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    
    current_time = int(time.time())
    current_date = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
    
    # Проверяем, существует ли пользователь
    cursor.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
    user_exists = cursor.fetchone() is not None
    
    if user_exists:
        # Обновляем данные
        cursor.execute("""
        UPDATE users SET
            username = COALESCE(?, username),
            first_name = COALESCE(?, first_name),
            last_name = COALESCE(?, last_name),
            email = COALESCE(?, email)
        WHERE user_id = ?
        """, (username, first_name, last_name, email, user_id))
    else:
        # Создаем нового пользователя
        cursor.execute("""
        INSERT INTO users 
        (user_id, username, first_name, last_name, email, registration_date, registration_timestamp) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            user_id, 
            username, 
            first_name, 
            last_name, 
            email,
            current_date,
            current_time
        ))
    
    conn.commit()
    conn.close()

def save_consent(user_id: int, data_consent: bool, offer_consent: bool):
    conn = sqlite3.connect('database/land_course.db')
    cursor = conn.cursor()
    timestamp = datetime.now().isoformat()
    cursor.execute('''
        INSERT OR REPLACE INTO user_consents (user_id, data_consent, offer_consent, timestamp)
        VALUES (?, ?, ?, ?)
    ''', (user_id, data_consent, offer_consent, timestamp))
    conn.commit()
    conn.close()

def check_consent(user_id: int):
    conn = sqlite3.connect('database/land_course.db')
    cursor = conn.cursor()
    cursor.execute('SELECT data_consent, offer_consent FROM user_consents WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (False, False)


def save_yookassa_payment(user_id: int, payment):
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    
    payment_timestamp = int(time.time())
    # Сохраняем рубли, а не копейки (делим на 100)
    amount = float(payment.amount.value)  # Получаем 1.00 вместо 100
    
    cursor.execute("""
        INSERT INTO payments 
        (user_id, payment_id, amount, currency, payment_date, 
         payment_timestamp, payment_method, payment_status) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, 
        payment.id, 
        amount,  # Теперь сохраняется 1.00 вместо 100
        payment.amount.currency,
        datetime.fromtimestamp(payment_timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        payment_timestamp,
        payment.payment_method.type if payment.payment_method else "unknown",
        payment.status
    ))
    
    conn.commit()
    conn.close()

def has_payment(user_id: int) -> bool:
    """Проверяет наличие успешного платежа в БД"""
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM payments 
        WHERE user_id = ? 
        AND payment_status = 'succeeded'
        LIMIT 1
    """, (user_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def save_invite_link(user_id: int, invite_link: str):
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    
    current_time = int(time.time())
    current_date = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_links 
        (user_id, invite_link, created_at, created_date) 
        VALUES (?, ?, ?, ?)
    """, (user_id, invite_link, current_time, current_date))
    
    conn.commit()
    conn.close()

def validate_email(email: str) -> bool:
    """Простая проверка формата email"""
    if not email or '@' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    return '.' in parts[1] and len(parts[1].split('.')[-1]) >= 2

def get_user_email(user_id: int) -> str:
    """Получаем email пользователя из базы данных"""
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_user_email(user_id: int, email: str):
    """Сохраняет email пользователя в таблицу users"""
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE users SET email = ?
        WHERE user_id = ?
        """, (email, user_id))
        # Если пользователь не существует, создаём запись
        if cursor.rowcount == 0:
            cursor.execute("""
            INSERT INTO users (user_id, email, registration_date, registration_timestamp)
            VALUES (?, ?, ?, ?)
            """, (
                user_id, email,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                int(time.time())
            ))
        conn.commit()
    except Exception as e:
        print(f"Ошибка при сохранении email: {e}")
    finally:
        conn.close()

def get_user_invite_link(user_id: int) -> str:
    """Получить инвайт-ссылку пользователя из базы данных"""
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    cursor.execute("SELECT invite_link FROM user_links WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None