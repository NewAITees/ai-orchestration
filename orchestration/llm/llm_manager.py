"""
Agnoフレームワークを活用した LLM 管理モジュール

LLMManagerは、オーケストレーションシステム全体でのLLM操作を一元管理します。
AgnoClientを内部で使用することで、高度なLLM機能を提供します。
"""

import asyncio
import json
import os
from collections.abc import AsyncGenerator
from datetime import datetime
from difflib import get_close_matches
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from ..agno_client import AgnoClient
from ..ai_types import ModelName
from ..config import settings


class PromptTemplate:
    """プロンプトテンプレート管理"""

    def __init__(self, template_str: str, template_id: str | None = None) -> None:
        """
        プロンプトテンプレートの初期化

        Args:
            template_str: テンプレート文字列
            template_id: テンプレートID（オプション）
        """
        self.template_str = template_str
        self.id = template_id or f"template_{datetime.now().timestamp()}"

    def render(self, **variables) -> str:
        """
        テンプレートを変数で埋めて出力

        Args:
            **variables: テンプレート変数

        Returns:
            レンダリングされたプロンプト
        """
        result = self.template_str
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            if isinstance(value, dict):
                # 辞書の場合は整形して置換
                formatted_value = json.dumps(value, ensure_ascii=False, indent=2)
                result = result.replace(placeholder, formatted_value)
            elif isinstance(value, list):
                # リストの場合は箇条書きで置換
                formatted_value = "\n".join([f"- {item}" for item in value])
                result = result.replace(placeholder, formatted_value)
            else:
                # それ以外はそのまま置換
                result = result.replace(placeholder, str(value))

        return result


class PromptTemplateLoader:
    """プロンプトテンプレートのロード機能"""

    def __init__(self, templates_dir: str | None = None) -> None:
        """
        テンプレートローダーの初期化

        Args:
            templates_dir: テンプレートディレクトリ（オプション）
        """
        self.templates_dir = templates_dir or os.path.join(
            os.path.dirname(__file__), "..", "prompts"
        )
        self.templates: dict[str, PromptTemplate] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """テンプレートファイルを読み込む"""
        templates_path = Path(self.templates_dir)
        if not templates_path.exists():
            print(f"テンプレートディレクトリ {self.templates_dir} が見つかりません")
            return

        for component_dir in templates_path.iterdir():
            if component_dir.is_dir():
                component_name = component_dir.name
                for template_file in component_dir.glob("*.txt"):
                    template_name = template_file.stem
                    with open(template_file, encoding="utf-8") as f:
                        template_str = f.read()

                    template_id = f"{component_name}/{template_name}"
                    self.templates[template_id] = PromptTemplate(template_str, template_id)
                    print(f"テンプレート読み込み: {template_id}")

    def load_template(self, template_id: str) -> PromptTemplate:
        """
        テンプレートの取得

        Args:
            template_id: テンプレートID

        Returns:
            プロンプトテンプレート

        Raises:
            ValueError: テンプレートが見つからない場合
        """
        if template_id not in self.templates:
            # 近い候補を出力
            candidates = get_close_matches(
                template_id, list(self.templates.keys()), n=3, cutoff=0.5
            )
            error_msg = f"テンプレート {template_id} が見つかりません。候補: {candidates}\n現在登録済み: {list(self.templates.keys())}"
            print(error_msg)
            raise ValueError(error_msg)

        return self.templates[template_id]

    def register_template(self, template_id: str, template_str: str) -> PromptTemplate:
        """
        新しいテンプレートを登録

        Args:
            template_id: テンプレートID
            template_str: テンプレート文字列

        Returns:
            登録されたプロンプトテンプレート
        """
        template = PromptTemplate(template_str, template_id)
        self.templates[template_id] = template
        return template


class ResponseParser:
    """LLMレスポンスの解析クラス"""

    @staticmethod
    def parse_json_response(response: str) -> dict[str, Any]:
        """
        JSON形式のレスポンスを解析

        Args:
            response: LLMからのレスポンス

        Returns:
            解析されたJSON辞書

        Raises:
            ValueError: JSONの解析に失敗した場合
        """
        try:
            # コードブロックや余分なテキストを除去
            json_str = response

            # Markdown形式のJSONコードブロックを処理
            if "```json" in json_str and "```" in json_str:
                start = json_str.find("```json") + 7
                end = json_str.find("```", start)
                json_str = json_str[start:end].strip()
            elif "```" in json_str and "```" in json_str:
                start = json_str.find("```") + 3
                end = json_str.find("```", start)
                json_str = json_str[start:end].strip()

            # 先頭と末尾の不要なテキストを除去
            result = json.loads(json_str)
            return result
        except json.JSONDecodeError as e:
            raise ValueError(f"JSONの解析に失敗しました: {e}\nレスポンス: {response[:100]}...")


class BaseLLMManager:
    """LLMマネージャーの基底クラス"""

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        parameters: dict[str, Any] | None = None,
    ) -> None:
        """
        初期化

        Args:
            model_name: モデル名
            api_key: API キー
            base_url: ベース URL
            parameters: 追加パラメータ
        """
        self.model_name = model_name or settings.DEFAULT_MODEL
        self.api_key = api_key
        self.base_url = base_url or settings.OLLAMA_BASE_URL
        self.parameters = parameters or {}
        self.last_used = datetime.now()

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        テキスト生成のコア機能

        Args:
            prompt: 入力プロンプト
            **kwargs: 追加パラメータ

        Returns:
            生成されたテキスト
        """
        raise NotImplementedError("サブクラスで実装する必要があります")

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        ストリーミングテキスト生成

        Args:
            prompt: 入力プロンプト
            **kwargs: 追加パラメータ

        Yields:
            生成されたテキストのチャンク
        """
        raise NotImplementedError("サブクラスで実装する必要があります")

    def update_last_used(self) -> None:
        """最終使用時刻を更新"""
        self.last_used = datetime.now()


class LLMManager(BaseLLMManager):
    """
    統合LLMマネージャー

    AgnoClientを使用して高度なLLM機能を提供します。
    プロンプトテンプレートとレスポンス解析機能を備えています。
    """

    def __init__(
        self,
        model_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        parameters: dict[str, Any] | None = None,
        templates_dir: str | None = None,
    ) -> None:
        """
        初期化

        Args:
            model_name: モデル名
            api_key: API キー
            base_url: ベース URL
            parameters: 追加パラメータ
            templates_dir: テンプレートディレクトリ
        """
        super().__init__(model_name, api_key, base_url, parameters)

        # AgnoClientの初期化
        self.agno_client = AgnoClient(
            model_name=self.model_name,
            debug_level=settings.LOG_LEVEL,
            base_url=self.base_url or settings.OLLAMA_BASE_URL,
        )

        # プロンプトテンプレートローダーの初期化
        self.template_loader = PromptTemplateLoader(templates_dir)

        # レスポンスパーサーの初期化
        self.response_parser = ResponseParser()

        print(f"LLMManager initialized with model: {self.model_name}")

    async def generate(self, prompt: str, **kwargs) -> str:
        """
        テキスト生成の実装

        Args:
            prompt: 入力プロンプト
            **kwargs: 追加パラメータ

        Returns:
            生成されたテキスト
        """
        self.update_last_used()

        # パラメータの結合（デフォルト + インスタンス + 呼び出し時）
        merged_params = {**self.parameters, **kwargs}

        # 画像パラメータの処理
        images = merged_params.pop("images", None)

        try:
            # AgnoClientを使用して生成
            response = await self.agno_client.run_query(prompt, images=images, **merged_params)
            return response
        except Exception as e:
            print(f"Error generating text: {e}")
            return f"エラーが発生しました: {e!s}"

    async def stream(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        """
        ストリーミングテキスト生成の実装

        Args:
            prompt: 入力プロンプト
            **kwargs: 追加パラメータ

        Yields:
            生成されたテキストのチャンク
        """
        self.update_last_used()

        # パラメータの結合
        merged_params = {**self.parameters, **kwargs}

        # 画像パラメータの処理
        images = merged_params.pop("images", None)

        try:
            # AgnoClientのストリーミングモードを使用
            async for chunk in self.agno_client.process_query(
                prompt, images=images, stream=True, **merged_params
            ):
                yield chunk
        except Exception as e:
            print(f"Error streaming text: {e}")
            yield f"エラーが発生しました: {e!s}"

    async def generate_with_template(
        self, template_id: str, variables: dict[str, Any], **kwargs
    ) -> str:
        """
        テンプレートを使用したテキスト生成

        Args:
            template_id: テンプレートID
            variables: テンプレート変数
            **kwargs: 生成パラメータ

        Returns:
            生成されたテキスト
        """
        try:
            # テンプレートのロードとレンダリング
            template = self.template_loader.load_template(template_id)
            prompt = template.render(**variables)

            # テキスト生成
            return await self.generate(prompt, **kwargs)
        except ValueError as e:
            # テンプレートが見つからない場合
            print(f"Error with template: {e}")

            # インラインテンプレートとして処理
            if "\n" in template_id or len(template_id) > 50:
                inline_template = PromptTemplate(template_id)
                prompt = inline_template.render(**variables)
                return await self.generate(prompt, **kwargs)

            return f"テンプレートエラー: {e!s}"

    async def parse_json_response(self, response: str) -> dict[str, Any]:
        """
        JSONレスポンスの解析

        Args:
            response: LLMからのレスポンス

        Returns:
            解析されたJSON辞書
        """
        try:
            return self.response_parser.parse_json_response(response)
        except ValueError as e:
            print(f"JSON解析エラー: {e}")
            # 再試行: より寛容なJSONの抽出と解析
            try:
                # テキストからJSONらしき部分を抽出
                import re

                json_pattern = r"\{.*\}"
                match = re.search(json_pattern, response, re.DOTALL)
                if match:
                    json_str = match.group(0)
                    return json.loads(json_str)
                else:
                    return {
                        "error": "JSON形式のレスポンスを抽出できませんでした",
                        "raw_response": response,
                    }
            except Exception:
                return {"error": "レスポンスの解析に失敗しました", "raw_response": response}

    async def close(self) -> None:
        """リソースの解放"""
        if hasattr(self, "agno_client") and self.agno_client:
            await self.agno_client.close()
