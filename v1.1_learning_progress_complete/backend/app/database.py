"""
数据库连接管理

创建 SQLAlchemy 引擎和会话工厂。
后续数据模型通过继承 Base 类来定义数据库表。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


# 创建数据库引擎
# connect_args 仅 SQLite 需要（禁止跨线程检查）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,  # 生产环境应设为 False，调试时可设为 True
)

# 会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """
    声明式基类

    所有数据模型继承此类，自动关联到 SQLAlchemy 元数据。
    """
    pass


def get_db():
    """
    FastAPI 依赖注入：获取数据库会话

    每次请求获取一个新会话，请求结束后自动关闭。
    用法：
        @router.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    初始化数据库：根据所有已注册的模型创建表

    在应用启动时调用，确保数据库表结构与模型定义一致。
    后续添加新模型后无需修改此函数。
    """
    Base.metadata.create_all(bind=engine)
