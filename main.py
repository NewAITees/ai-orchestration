from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from backend.app.api.router import api_router
from backend.app.core.config import settings

app = FastAPI(
    title="General AI Playground API",
    description="Agnoフレームワークベースの汎用AIプレイグラウンドAPI",
    version="0.1.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# APIルーターの追加
app.include_router(api_router, prefix="/api")

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
                    openapi_schema["paths"][path][method]["operationId"] = route_name.replace("chat_", "")
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

def start_app():
    """エントリーポイント関数: poetry run app コマンドで実行されます"""
    import uvicorn
    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    start_app() 