"""
Agnoフレームワークを活用した統合APIクライアント

最新のAgno 1.0.8に対応した実装
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

# 最新のAgnoインポート
from agno.agent import Agent
from agno.media import Image
from agno.models.ollama import Ollama

from .config import settings
from .utils.debugger import Debugger


class AgnoClient:
    """
    Agnoベースの統合クライアント

    主な責務:
    - Ollamaモデルとの連携
    - マルチモーダル処理
    - 会話履歴の管理
    """

    def __init__(
        self,
        model_name: str | None = None,
        debug_level: str = "info",
        direct_mode: bool = True,
        base_url: str = "http://localhost:11434",
        session_id: str | None = None,
    ) -> None:
        """
        統合クライアントの初期化

        Args:
            model_name: 使用するモデル名
            debug_level: デバッグレベル
            direct_mode: Ollamaと直接通信するかどうか
            base_url: Ollama API の URL
            session_id: セッションID (None の場合は新規生成)
        """
        self.model_name = model_name or settings.DEFAULT_MODEL
        self.debug_level = debug_level
        self.direct_mode = direct_mode
        self.base_url = base_url
        self.session_id = session_id or f"session_{uuid.uuid4().hex}"

        # デバッガーの初期化
        self.debugger = Debugger(debug_level)
        self.debugger.log("info", f"Initializing AgnoClient with model {self.model_name}")

        # モデルパラメータ
        self.model_params = {"temperature": 0.7, "top_p": 0.9, "max_tokens": 2000}

        # エージェントの初期化
        self.agent: Agent | None = None
        self.setup_complete = False

        # ツール管理
        self.available_tools: list[str] = []
        self.connected = False

    async def run_query(self, query: str, images: list[Image] | None = None, **kwargs: Any) -> str:
        """
        直接エージェントにクエリを実行

        Args:
            query: ユーザーからの入力テキスト
            images: 添付画像
            **kwargs: その他のパラメータ

        Returns:
            応答テキスト
        """
        max_retries = 3
        retry_delay = 2  # 秒

        for attempt in range(max_retries):
            try:
                if not self.setup_complete:
                    await self.setup()

                # Agnoエージェントを使用して応答を生成
                if self.agent is None:
                    raise RuntimeError("Agent is not initialized")

                response = await self.agent.arun(query, images=images, **kwargs)
                return response.content if hasattr(response, "content") else str(response)
            except Exception as e:
                error_msg = f"Error running query (attempt {attempt + 1}/{max_retries}): {e!s}"
                self.debugger.record_error("run_error", error_msg)

                if (
                    "loading model" in str(e).lower() or "timed out" in str(e).lower()
                ) and attempt < max_retries - 1:
                    # モデルロード中の場合は少し待ってリトライ
                    self.debugger.log(
                        "info", f"Model is loading, waiting {retry_delay}s before retry..."
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 指数バックオフ
                    continue

                if attempt >= max_retries - 1:
                    return f"エラーが発生しました: {e!s}。Ollamaサーバーが起動しているか、選択したモデルが正しくインストールされているか確認してください。"

        return "複数回の試行後もエラーが発生しました。しばらくしてから再度お試しください。"

    async def setup(self) -> None:
        """エージェントのセットアップ"""
        if self.setup_complete:
            return

        try:
            # Ollamaモデルの設定
            ollama_model = Ollama(
                id=self.model_name,
                # base_url=self.base_url,
                # temperature=self.model_params["temperature"],
                # top_p=self.model_params["top_p"],
                # max_tokens=self.model_params["max_tokens"]
            )

            # エージェントの初期化
            self.agent = Agent(model=ollama_model, markdown=True)

            self.setup_complete = True
            self.connected = True
            self.debugger.log("info", "AgnoClient setup completed")

        except Exception as e:
            self.debugger.record_error("setup_error", f"Error during agent setup: {e!s}")
            raise

    async def process_query(
        self,
        query: str,
        images: list[str | Path] | None = None,
        mode: str = "standard",
        stream: bool = False,
        **kwargs: Any,
    ) -> str | AsyncGenerator[str, None]:
        """
        クエリを処理して応答を返す

        Args:
            query: ユーザーからの入力テキスト
            images: 添付画像のパスリスト
            mode: 使用するチャットモード（現在はstandardのみ対応）
            stream: ストリーミングレスポンスを使用するかどうか
            **kwargs: その他のパラメータ

        Returns:
            処理結果のテキスト（ストリーミングの場合はジェネレータ）
        """
        if not self.setup_complete:
            await self.setup()

        try:
            # モードの検証
            if mode != "standard":
                raise ValueError("現在はstandardモードのみ対応しています")

            # Agno画像オブジェクトのリスト作成
            agno_images: list[Image] = []
            if images:
                for img_path in images:
                    img_path = Path(img_path) if isinstance(img_path, str) else img_path
                    if img_path.exists():
                        image = Image(filepath=str(img_path))
                        agno_images.append(image)
                        self.debugger.log("debug", f"Added image: {img_path}")
                    else:
                        self.debugger.record_error(
                            "image_error", f"Image file not found: {img_path}"
                        )

            # ストリーミングモードの処理
            if stream:
                return self._stream_response(query, agno_images, **kwargs)

            # 直接エージェントを使用
            return await self.run_query(
                query, images=agno_images if agno_images else None, **kwargs
            )

        except Exception as e:
            error_msg = f"Error processing query: {e!s}"
            self.debugger.record_error("process_error", error_msg)
            return error_msg

    async def _stream_response(
        self, query: str, images: list[Image] | None = None, **kwargs: Any
    ) -> AsyncGenerator[str, None]:
        """
        ストリーミングレスポンスを生成

        Args:
            query: ユーザーからの入力テキスト
            images: Agno画像オブジェクトのリスト
            **kwargs: その他のパラメータ

        Yields:
            生成されたテキストチャンク
        """
        try:
            if not self.agent:
                await self.setup()

            if self.agent is None:
                raise RuntimeError("Agent is not initialized")

            # ストリーミングモードで応答を生成
            async for chunk in self.agent.astream(query, images=images, **kwargs):
                content = chunk.content
                yield content

        except Exception as e:
            error_msg = f"Error in streaming response: {e!s}"
            self.debugger.record_error("stream_error", error_msg)
            yield error_msg

    async def get_available_models(self) -> list[str]:
        """
        利用可能なモデル一覧を取得

        Returns:
            モデル名のリスト
        """
        try:
            # Ollamaのモデル一覧を取得
            import aiohttp

            async with aiohttp.ClientSession() as session, session.get(
                f"{self.base_url}/api/tags"
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    models = [model["name"] for model in data.get("models", [])]
                    self.debugger.log("info", f"Retrieved {len(models)} models")
                    return models
                else:
                    self.debugger.record_error(
                        "model_error", f"Failed to retrieve models: {response.status}"
                    )
                    return self._get_default_models()
        except Exception as e:
            self.debugger.record_error("model_error", f"Error retrieving models: {e!s}")
            return self._get_default_models()

    def _get_default_models(self) -> list[str]:
        """デフォルトのモデル一覧を返す"""
        return ["gemma:2b", "gemma:7b", "llama2:7b", "mistral:7b"]

    def set_model(self, model_name: str) -> None:
        """
        使用するモデルを設定

        Args:
            model_name: モデル名
        """
        self.model_name = model_name
        self.setup_complete = False
        self.agent = None
        self.debugger.log("info", f"Model changed to {model_name}")

    def set_model_parameters(self, params: dict[str, Any]) -> None:
        """
        モデルパラメータを設定

        Args:
            params: パラメータ辞書
        """
        self.model_params.update(params)
        self.setup_complete = False
        self.agent = None
        self.debugger.log("info", f"Model parameters updated: {params}")

    async def close(self) -> None:
        """クライアントを終了"""
        if self.agent:
            # 必要なクリーンアップ処理があれば実行
            self.agent = None
            self.setup_complete = False
            self.connected = False
            self.debugger.log("info", "AgnoClient closed")

    async def __aenter__(self) -> "AgnoClient":
        """非同期コンテキストマネージャのエントリーポイント"""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """非同期コンテキストマネージャの終了処理"""
        await self.close()

    async def get_conversation_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """
        会話履歴を取得

        Args:
            limit: 取得する履歴の最大数

        Returns:
            会話履歴のリスト
        """
        # 現在は履歴管理機能は未実装
        return []

    async def clear_conversation(self) -> bool:
        """
        会話履歴をクリア

        Returns:
            クリアが成功したかどうか
        """
        # 現在は履歴管理機能は未実装
        return True

    async def connect_to_server(self, server_path: str) -> list[str]:
        """
        サーバーに接続

        Args:
            server_path: サーバーのパス

        Returns:
            利用可能なモデルのリスト
        """
        self.base_url = server_path
        self.connected = True
        return await self.get_available_models()


"""
Commented out original implementation for reference:

# Original complex implementation
# class AgnoClient:
#     def __init__(self, ...):
#         ...
#
# [Rest of the original implementation...]
"""
