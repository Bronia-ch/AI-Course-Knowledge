"""
数据库连接管理

创建 SQLAlchemy 引擎和会话工厂。
后续数据模型通过继承 Base 类来定义数据库表。
"""

from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


# 创建数据库引擎
# connect_args 仅 SQLite 需要（禁止跨线程检查）
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,  # 生产环境应设为 False，调试时可设为 True
)


if "sqlite" in settings.DATABASE_URL:
    @event.listens_for(engine, "connect")
    def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record) -> None:
        """SQLite 默认关闭外键校验，每个新连接都必须显式开启。"""
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

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
    _ensure_compatibility_columns()


def _ensure_compatibility_columns() -> None:
    """为无迁移工具的本地 SQLite 数据库补充向后兼容字段。"""
    column_specs = [
        (
            "portfolio_opportunities",
            "chapter_id",
            "ALTER TABLE portfolio_opportunities ADD COLUMN chapter_id INTEGER REFERENCES chapters(id)",
        ),
        (
            "portfolio_projects",
            "chapter_id",
            "ALTER TABLE portfolio_projects ADD COLUMN chapter_id INTEGER REFERENCES chapters(id)",
        ),
        (
            "portfolio_project_showcases",
            "demo_video_url",
            "ALTER TABLE portfolio_project_showcases ADD COLUMN demo_video_url VARCHAR(500)",
        ),
        (
            "portfolio_project_showcases",
            "screenshot_urls",
            "ALTER TABLE portfolio_project_showcases ADD COLUMN screenshot_urls TEXT NOT NULL DEFAULT '[]'",
        ),
        (
            "portfolio_code_analyses",
            "interview_showcase",
            "ALTER TABLE portfolio_code_analyses ADD COLUMN interview_showcase TEXT NOT NULL DEFAULT '{}'",
        ),
        (
            "portfolio_code_analyses",
            "implementation_status",
            "ALTER TABLE portfolio_code_analyses ADD COLUMN implementation_status TEXT NOT NULL DEFAULT '{}'",
        ),
    ]
    with engine.begin() as connection:
        inspector = inspect(connection)
        table_names = set(inspector.get_table_names())
        for table_name, column_name, statement in column_specs:
            if table_name not in table_names:
                continue
            columns = {item["name"] for item in inspector.get_columns(table_name)}
            if column_name not in columns:
                connection.exec_driver_sql(statement)
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_portfolio_opportunities_chapter_id "
            "ON portfolio_opportunities (chapter_id)"
        )
        connection.exec_driver_sql(
            "CREATE INDEX IF NOT EXISTS ix_portfolio_projects_chapter_id "
            "ON portfolio_projects (chapter_id)"
        )
