import psycopg2

DB_CONFIG = {
    "dbname": "dbname",
    "user": "user",
    "password": "password",
    "host": "localhost",
    "port": "5432"
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)

def execute_query(query, params=None):
    """Универсальная функция для SELECT-запросов"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    result = cur.fetchall()
    cur.close()
    conn.close()
    return result

def execute_update(query, params=None):
    """Для INSERT/UPDATE/DELETE без возврата данных"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    conn.commit()
    cur.close()
    conn.close()

def execute_insert(query, params=None):
    """Для INSERT с RETURNING — возвращает результат"""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(query, params or ())
    result = cur.fetchall()
    conn.commit()
    cur.close()
    conn.close()
    return result
