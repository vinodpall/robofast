# RoboFast

一个基于FastAPI的机器人信息管理系统。

## 功能特点

- 机器人信息管理
- 奖项管理
- 数据库迁移支持
- RESTful API接口

## 技术栈

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL

## 安装说明

1. 克隆项目
```bash
git clone [项目地址]
cd robofast
```

2. 创建并激活虚拟环境
```bash
conda create -n robofast python=3.8
conda activate robofast
```

3. 安装依赖
```bash
pip install -r requirements.txt
```

4. 初始化数据库
```bash
alembic upgrade head
```

5. 启动服务
```bash
uvicorn app.main:app --reload
```

## API文档

启动服务后访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 项目结构

```
robofast/
├── alembic/          # 数据库迁移文件
├── app/              # 应用主目录
│   ├── api/         # API路由
│   ├── core/        # 核心配置
│   ├── db/          # 数据库配置
│   ├── models/      # 数据模型
│   └── schemas/     # Pydantic模型
├── requirements.txt  # 项目依赖
└── alembic.ini      # Alembic配置
``` 