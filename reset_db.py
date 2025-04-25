from sqlalchemy import create_engine, text
from app.database.database import MYSQL_URL

def reset_database():
    engine = create_engine(MYSQL_URL)
    
    # 要删除的表（按照外键依赖顺序）
    tables = [
        "data_records",      # 依赖于robots和data_types
        "robots",           # 依赖于companies, training_fields, awards
        "companies",        # 依赖于awards
        "visitor_records",  # 独立表
        "videos",          # 独立表
        "awards",          # 被companies和robots依赖
        "training_fields", # 被robots依赖
        "data_types",     # 被data_records依赖
        "web_configs",    # 独立表
        "alembic_version" # 独立表
    ]
    
    # 删除所有表
    with engine.connect() as conn:
        for table in tables:
            try:
                conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
                conn.commit()
                print(f"表 {table} 已删除")
            except Exception as e:
                print(f"删除表 {table} 时出错: {str(e)}")

if __name__ == "__main__":
    reset_database() 