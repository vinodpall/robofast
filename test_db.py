from app.database.database import engine
from sqlalchemy import text

def test_connection():
    try:
        with engine.connect() as conn:
            result = conn.execute(text('SHOW TABLES'))
            tables = list(result)
            print("Connected to database successfully!")
            print("Tables in database:", tables)
    except Exception as e:
        print("Failed to connect to database!")
        print("Error:", str(e))

if __name__ == "__main__":
    test_connection() 