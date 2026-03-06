import pymysql
import pymysql.cursors

# Database configurations
DB_HOST = "localhost"
DB_USER = "root"
DB_PASS = ""
DB_NAME = "dent_consent"

def get_db_connection():
    """Returns a pymysql connection object to be used across the app."""
    return pymysql.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )
