import time
import mysql.connector
from mysql.connector import Error
from .config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME, DB_CREATE_ON_START


def get_connection():
    """Fetches a MySQL connection and ensures the target database exists."""
    retries = 5
    delay = 0.25

    for attempt in range(1, retries + 1):
        try:
            conn = mysql.connector.connect(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                connection_timeout=10,
                autocommit=False,
                use_pure=True,
                buffered=True
            )
            if not conn.is_connected():
                raise Error('Could not connect to MySQL server.')

            if DB_CREATE_ON_START:
                cursor = conn.cursor()
                cursor.execute(
                    f'CREATE DATABASE IF NOT EXISTS `{DB_NAME}` '
                    'CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci'
                )
                cursor.close()

            conn.database = DB_NAME
            return conn
        except Error as e:
            if attempt < retries:
                time.sleep(delay * attempt)
                continue
            print(f"MySQL connection error: {e}")
            return None
