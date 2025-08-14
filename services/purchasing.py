from datetime import datetime
import time
import mysql.connector
from aiogram import types

# Настройки подключения к MySQL
MYSQL_CONFIG = {
    'host': 'localhost',
    'port': 3306,
    'user': 'root',
    'password': '24745500800Max!',
    'database': 'land_course',
    'autocommit': True
}

def get_mysql_conn():
    return mysql.connector.connect(**MYSQL_CONFIG)

def init_db():
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        username VARCHAR(255),
        first_name VARCHAR(255),
        last_name VARCHAR(255),
        email VARCHAR(255) UNIQUE,
        registration_date DATETIME,
        registration_timestamp BIGINT
    )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_consents (
            user_id BIGINT PRIMARY KEY,
            data_consent BOOLEAN NOT NULL,
            offer_consent BOOLEAN NOT NULL,
            timestamp DATETIME NOT NULL
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_links (
            user_id BIGINT PRIMARY KEY,
            invite_link TEXT,
            created_at BIGINT,
            created_date DATETIME
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            user_id BIGINT,
            payment_id VARCHAR(255),
            amount FLOAT,
            currency VARCHAR(10),
            payment_timestamp BIGINT,
            payment_date DATETIME,
            payment_method VARCHAR(50),
            payment_status VARCHAR(50) NOT NULL,
            PRIMARY KEY (user_id, payment_id)
        )
    """)
    conn.close()

init_db()

def save_or_update_user(user_id: int, username: str = None, first_name: str = None, 
                       last_name: str = None, email: str = None):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    current_time = int(time.time())
    current_date = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("SELECT 1 FROM users WHERE user_id = %s", (user_id,))
    user_exists = cursor.fetchone() is not None
    if user_exists:
        cursor.execute("""
        UPDATE users SET
            username = COALESCE(%s, username),
            first_name = COALESCE(%s, first_name),
            last_name = COALESCE(%s, last_name),
            email = COALESCE(%s, email)
        WHERE user_id = %s
        """, (username, first_name, last_name, email, user_id))
    else:
        cursor.execute("""
        INSERT INTO users 
        (user_id, username, first_name, last_name, email, registration_date, registration_timestamp) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            user_id, 
            username, 
            first_name, 
            last_name, 
            email,
            current_date,
            current_time
        ))
    conn.close()

def save_consent(user_id: int, data_consent: bool, offer_consent: bool):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO user_consents (user_id, data_consent, offer_consent, timestamp)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE data_consent=VALUES(data_consent), offer_consent=VALUES(offer_consent), timestamp=VALUES(timestamp)
    """, (user_id, data_consent, offer_consent, timestamp))
    conn.close()

def check_consent(user_id: int):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute('SELECT data_consent, offer_consent FROM user_consents WHERE user_id = %s', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (False, False)

def save_yookassa_payment(user_id: int, payment):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    payment_timestamp = int(time.time())
    amount = float(payment.amount.value)
    cursor.execute("""
        INSERT INTO payments 
        (user_id, payment_id, amount, currency, payment_date, 
         payment_timestamp, payment_method, payment_status) 
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE payment_status=VALUES(payment_status)
    """, (
        user_id, 
        payment.id, 
        amount,
        payment.amount.currency,
        datetime.fromtimestamp(payment_timestamp).strftime('%Y-%m-%d %H:%M:%S'),
        payment_timestamp,
        getattr(payment.payment_method, 'type', "unknown"),
        payment.status
    ))
    conn.close()

def has_payment(user_id: int) -> bool:
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 1 FROM payments 
        WHERE user_id = %s 
        AND payment_status = 'succeeded'
        LIMIT 1
    """, (user_id,))
    result = cursor.fetchone() is not None
    conn.close()
    return result

def save_invite_link(user_id: int, invite_link: str):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    current_time = int(time.time())
    current_date = datetime.fromtimestamp(current_time).strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute("""
        INSERT INTO user_links 
        (user_id, invite_link, created_at, created_date) 
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE invite_link=VALUES(invite_link), created_at=VALUES(created_at), created_date=VALUES(created_date)
    """, (user_id, invite_link, current_time, current_date))
    conn.close()

def validate_email(email: str) -> bool:
    if not email or '@' not in email:
        return False
    parts = email.split('@')
    if len(parts) != 2:
        return False
    return '.' in parts[1] and len(parts[1].split('.')[-1]) >= 2

def get_user_email(user_id: int) -> str:
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM users WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def save_user_email(user_id: int, email: str):
    conn = get_mysql_conn()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE users SET email = %s
        WHERE user_id = %s
        """, (email, user_id))
        if cursor.rowcount == 0:
            cursor.execute("""
            INSERT INTO users (user_id, email, registration_date, registration_timestamp)
            VALUES (%s, %s, %s, %s)
            """, (
                user_id, email,
                datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                int(time.time())
            ))
    except Exception as e:
        print(f"Ошибка при сохранении email: {e}")
    finally:
        conn.close()

def get_user_invite_link(user_id: int) -> str:
    conn = get_mysql_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT invite_link FROM user_links WHERE user_id = %s", (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result and result[0] else None