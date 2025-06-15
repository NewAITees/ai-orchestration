import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi

from .config import settings
from .core.session import Session
from .cui.novel_writer import NovelWriter
from .factory import AIComponentFactory
from .llm.llm_manager import LLMManager

app = FastAPI(
    title="General AI Playground API",
    description="Agnoフレームワークベースの汎用AIプレイグラウンドAPI",
    version="0.1.0",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=getattr(settings, "CORS_ORIGINS", ["*"]),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to General AI Playground API", "docs_url": "/docs"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="General AI Playground API",
        version="0.1.0",
        description="Agnoフレームワークベースの汎用AIプレイグラウンドAPI",
        routes=app.routes,
    )

    # operationIdをカスタマイズ
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if "operationId" in openapi_schema["paths"][path][method]:
                route_name = openapi_schema["paths"][path][method]["operationId"]
                # 操作IDを簡略化（例: chat_post_chat__post → sendMessage）
                if route_name.startswith("chat_"):
                    openapi_schema["paths"][path][method]["operationId"] = route_name.replace(
                        "chat_", ""
                    )

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


def start_app() -> None:
    """エントリーポイント関数: poetry run app コマンドで実行されます"""
    import uvicorn

    uvicorn.run("orchestration.main:app", host="0.0.0.0", port=8000, reload=True)


async def run_novel_writer(args=None) -> None:
    """小説作成アプリを実行"""
    # セッション初期化
    session = Session()

    # LLMマネージャー初期化
    llm_manager = LLMManager()

    # コンポーネント生成
    components = AIComponentFactory.create_orchestration_system(session, llm_manager)

    # 小説作成システム実行
    writer = NovelWriter(session, components)
    await writer.run()


if __name__ == "__main__":
    asyncio.run(run_novel_writer())
