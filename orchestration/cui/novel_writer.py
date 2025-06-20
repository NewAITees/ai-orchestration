import asyncio
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from ..ai_types import Component, MessageType, OrchestrationMessage, Task
from ..components.director import DirectorAI
from ..components.planner import PlannerAI
from ..components.reviewer import ReviewerAI
from ..components.worker import WorkerAI
from ..core.session import Session, SubTask, TaskStatus
from ..llm.llm_manager import LLMManager


@dataclass
class NovelWriterConfig:
    """小説作成システムの設定"""

    genres: dict[str, str] = field(
        default_factory=lambda: {"1": "ファンタジー", "2": "SF", "3": "恋愛", "4": "ミステリー"}
    )
    default_requirements: list[str] = field(
        default_factory=lambda: ["魅力的な主人公", "起承転結のある物語展開", "読者を引き込む世界観"]
    )
    genre_descriptions: dict[str, str] = field(
        default_factory=lambda: {
            "1": "魔法や異世界が舞台のファンタジー作品",
            "2": "科学技術や未来社会を描くSF作品",
            "3": "人々の恋愛模様を描く恋愛作品",
            "4": "謎解きや事件を扱うミステリー作品",
        }
    )


@dataclass
class NovelWriterInput:
    """小説作成の入力データ"""

    title: str
    genre: str
    requirements: list[str]
    revisions: dict[str, list[str]] = field(default_factory=dict)  # タスクIDごとの修正内容リスト


class NovelWriter:
    """小説作成支援システム"""

    def __init__(self, session, components, input_func=input, output_func=print) -> None:
        self.session = session
        self.components = components
        self.input_func = input_func
        self.output_func = output_func
        self.default_requirements = [
            "魅力的な主人公",
            "起承転結のある物語展開",
            "読者を引き込む世界観",
        ]
        self.genres = {"1": "ファンタジー", "2": "SF", "3": "恋愛", "4": "ミステリー"}

    async def run(self) -> None:
        """小説作成プロセスを実行"""
        self.output_func("=== 小説作成支援システム ===")

        # 1. プロジェクト設定
        self._setup_project()

        # 2. タスク計画
        self.output_func("\n=== タスク計画 ===")
        planner = self.components["planner"]
        plan_result = await planner.plan_task(self.session.id, self.session.requirements)

        # 3. サブタスク追加
        for subtask_data in plan_result["subtasks"]:
            subtask = SubTask(
                id=subtask_data["id"],
                title=subtask_data["title"],
                description=subtask_data["description"],
            )
            self.session.add_subtask(subtask)

        # 4. タスク実行と評価
        await self._execute_tasks()

        self.output_func("\n=== 小説作成が完了しました ===")

    def _setup_project(self) -> None:
        """プロジェクト設定"""
        # タイトル入力
        title = self._get_input("小説のタイトルを入力してください: ")
        self.session.title = title

        # ジャンル選択
        self.output_func("\nジャンルを選択してください:")
        for key, name in self.genres.items():
            self.output_func(f"{key}: {name}")

        genre_key = self._get_input("選択 (1-4): ", lambda x: x in self.genres)
        self.session.genre = self.genres[genre_key]

        # 要件収集
        self.output_func("\n物語の要件を入力してください（終了は空入力）:")
        requirements = []

        while True:
            req = self.input_func("要件: ")
            if not req:
                break
            requirements.append(req)

        if not requirements:
            self.output_func("デフォルトの要件を使用します。")
            requirements = self.default_requirements.copy()

        self.session.requirements = requirements

    async def _execute_tasks(self) -> None:
        """タスク実行"""
        worker = self.components["worker"]
        reviewer = self.components["reviewer"]

        for _task_id, task in self.session.subtasks.items():
            self.output_func(f"\n=== タスク「{task.title}」を実行中... ===")

            # 実行
            result = await worker.execute_task(task)
            task.result = result.result

            # 評価
            evaluation = await reviewer.evaluate_task(task)

            self.output_func(f"\n評価スコア: {evaluation.score}")
            self.output_func(f"フィードバック: {evaluation.feedback}")

            # 完了
            task.update_status(TaskStatus.COMPLETED)

    def _get_input(self, prompt, validator=None):
        """入力取得"""
        while True:
            value = self.input_func(prompt)
            if not validator or validator(value):
                return value
            self.output_func("無効な入力です。再入力してください。")


async def main() -> None:
    """メイン実行関数"""
    # カスタム設定の作成（例）
    custom_config = NovelWriterConfig(
        genres={
            "1": "ファンタジー",
            "2": "SF",
            "3": "恋愛",
            "4": "ミステリー",
            "5": "ホラー",
            "6": "歴史",
        },
        genre_descriptions={
            "1": "魔法や異世界が舞台のファンタジー作品",
            "2": "科学技術や未来社会を描くSF作品",
            "3": "人々の恋愛模様を描く恋愛作品",
            "4": "謎解きや事件を扱うミステリー作品",
            "5": "恐怖や超自然現象を描くホラー作品",
            "6": "歴史的な出来事や時代を描く作品",
        },
        default_requirements=[
            "魅力的な主人公",
            "起承転結のある物語展開",
            "読者を引き込む世界観",
            "印象的なクライマックス",
            "伏線の回収",
        ],
    )

    # セッションとコンポーネントの初期化
    session = Session(id="novel-session")
    llm_manager = LLMManager()
    director = DirectorAI(session, llm_manager)
    reviewer = ReviewerAI(session, llm_manager)
    planner = PlannerAI(session, llm_manager)
    worker = WorkerAI(session, llm_manager)

    # 小説作成システムの実行
    writer = NovelWriter(
        session=session,
        components={
            "director": director,
            "reviewer": reviewer,
            "planner": planner,
            "worker": worker,
        },
    )
    await writer.run()


if __name__ == "__main__":
    asyncio.run(main())
