from datetime import datetime
import sqlite3
import time
from aiogram import types

def init_db():
    conn = sqlite3.connect('database/land_course.db')
    cursor = conn.cursor()
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
        amount INTEGER,
        currency TEXT,
        payment_timestamp INTEGER,
        payment_date TEXT,
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


def save_payment(user_id: int, payment_info: types.SuccessfulPayment):
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    
    # Получаем текущее время в Unix timestamp и преобразуем в читаемую дату
    payment_timestamp = int(time.time())
    payment_date = datetime.fromtimestamp(payment_timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        INSERT INTO payments 
        (user_id, payment_id, amount, currency, payment_date, payment_timestamp) 
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id, 
        payment_info.telegram_payment_charge_id, 
        payment_info.total_amount, 
        payment_info.currency,
        payment_date,
        payment_timestamp,
    ))
    
    conn.commit()
    conn.close()

# Проверка наличия платежа у пользователя
def has_payment(user_id: int) -> bool:
    conn = sqlite3.connect("database/land_course.db")
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM payments WHERE user_id = ? LIMIT 1", (user_id,))
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

