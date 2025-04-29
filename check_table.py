from sqlalchemy import inspect
from app.database.database import engine

def check_table_structure():
    inspector = inspect(engine)
    columns = inspector.get_columns('videos')
    print("视频表结构：")
    for col in columns:
        print(f"字段名: {col['name']}, 类型: {col['type']}, 是否可空: {col['nullable']}")

if __name__ == "__main__":
    check_table_structure() 