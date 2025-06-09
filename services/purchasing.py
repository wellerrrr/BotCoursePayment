from datetime import datetime
import sqlite3


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