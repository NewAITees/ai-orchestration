from typing import List, Optional, Callable, Dict
import sys
from dataclasses import dataclass, field
from app.orchestration.core.session import Session, Task, TaskStatus
from app.orchestration.components.director import DefaultDirectorAI
from app.orchestration.components.evaluator import DefaultEvaluatorAI
from app.orchestration.components.planner import DefaultPlannerAI
from app.orchestration.components.worker import DefaultWorkerAI
from app.llm.llm_manager import LLMManager
from app.orchestration.core.message import OrchestrationMessage, MessageType, Component

@dataclass
class NovelWriterConfig:
    """小説作成システムの設定"""
    genres: Dict[str, str] = field(default_factory=lambda: {
        "1": "ファンタジー",
        "2": "SF",
        "3": "恋愛",
        "4": "ミステリー"
    })
    default_requirements: List[str] = field(default_factory=lambda: [
        "魅力的な主人公",
        "起承転結のある物語展開",
        "読者を引き込む世界観"
    ])
    genre_descriptions: Dict[str, str] = field(default_factory=lambda: {
        "1": "魔法や異世界が舞台のファンタジー作品",
        "2": "科学技術や未来社会を描くSF作品",
        "3": "人々の恋愛模様を描く恋愛作品",
        "4": "謎解きや事件を扱うミステリー作品"
    })

@dataclass
class NovelWriterInput:
    """小説作成の入力データ"""
    title: str
    genre: str
    requirements: List[str]
    revisions: Dict[str, List[str]] = field(default_factory=dict)  # タスクIDごとの修正内容リスト

class NovelWriter:
    def __init__(
        self,
        session: Session,
        director: DefaultDirectorAI,
        evaluator: DefaultEvaluatorAI,
        planner: DefaultPlannerAI,
        worker: DefaultWorkerAI,
        config: Optional[NovelWriterConfig] = None,
        input_data: Optional[NovelWriterInput] = None,
        input_func: Callable[[str], str] = input,
        output_func: Callable[[str], None] = print
    ):
        self.session = session
        self.director = director
        self.evaluator = evaluator
        self.planner = planner
        self.worker = worker
        self.config = config or NovelWriterConfig()
        self.input_data = input_data
        self.input_func = input_func
        self.output_func = output_func

    def run(self):
        """小説作成プロセスを実行"""
        self.output_func("=== 小説作成支援システム ===")
        
        if self.input_data:
            self._setup_project_with_input()
        else:
            self._setup_project_interactive()
        
        # タスクの生成
        self.output_func("\n=== タスク生成 ===")
        message = OrchestrationMessage(
            type=MessageType.COMMAND,
            sender=Component.DIRECTOR,
            receiver=Component.PLANNER,
            content={"task": "start_session"},
            action="start_session",
            session_id=self.session.id
        )
        self.director.process_message(message)
        
        # タスクの実行
        while True:
            if not self._execute_next_task():
                break

        self.output_func("\n=== 小説作成が完了しました ===")

    def _setup_project_with_input(self):
        """入力データを使用してプロジェクトを設定"""
        self.session.title = self.input_data.title
        self.session.genre = self.input_data.genre
        self.session.requirements = self.input_data.requirements.copy()

    def _setup_project_interactive(self):
        """対話的にプロジェクトを設定"""
        self.output_func("\n=== プロジェクト設定 ===")
        title = self._get_valid_input("小説のタイトルを入力してください", lambda x: len(x.strip()) > 0)
        self.session.title = title
        
        genre_prompt = "ジャンルを選択してください\n"
        for key, name in self.config.genres.items():
            desc = self.config.genre_descriptions.get(key, "")
            genre_prompt += f"{key}: {name} - {desc}\n"
        genre_prompt += f"選択 (1-{len(self.config.genres)}): "
        
        genre = self._get_valid_input(
            genre_prompt,
            lambda x: x in self.config.genres.keys()
        )
        self.session.genre = self.config.genres[genre]
        
        self._collect_requirements_interactive()

    def _collect_requirements_interactive(self):
        """対話的に要件を収集"""
        self.output_func("\n=== 要件の収集 ===")
        self.output_func("物語の要件を入力してください（終了する場合は空入力）")
        
        while True:
            requirement = self.input_func("要件: ").strip()
            if not requirement:
                break
            self.session.requirements.append(requirement)
            
        if not self.session.requirements:
            self.output_func("要件が設定されていません。デフォルトの要件を使用します。")
            self.session.requirements = self.config.default_requirements.copy()

    def _execute_next_task(self) -> bool:
        """次のタスクを実行"""
        self.output_func("\n=== タスク実行 ===")
        
        current_tasks = [task for task in self.session.tasks if task.status != TaskStatus.COMPLETED]
        if not current_tasks:
            return False
            
        # 自動的に最初のタスクを選択
        selected_task = current_tasks[0]
        
        # タスク実行
        self.output_func(f"\nタスク「{selected_task.title}」を実行中...")
        result = self.worker.execute_task(selected_task)
        
        # 評価
        self.output_func("\n=== 評価結果 ===")
        evaluation = self.evaluator.evaluate_task(selected_task)
        self.output_func(f"評価スコア: {evaluation.score}")
        self.output_func(f"フィードバック: {evaluation.feedback}")
        
        # 修正の適用（入力データから）
        if self.input_data and selected_task.id in self.input_data.revisions:
            for revision in self.input_data.revisions[selected_task.id]:
                selected_task.result = revision
                new_evaluation = self.evaluator.evaluate_task(selected_task)
                self.output_func(f"\n新しい評価スコア: {new_evaluation.score}")
                self.output_func(f"フィードバック: {new_evaluation.feedback}")
        
        selected_task.status = TaskStatus.COMPLETED
        return True

    def _get_valid_input(self, prompt: str, validator: Callable[[str], bool]) -> str:
        """有効な入力を取得"""
        while True:
            self.output_func(prompt)
            value = self.input_func("").strip()
            if validator(value):
                return value
            self.output_func("無効な入力です。もう一度入力してください。")

def main():
    """メイン実行関数"""
    # カスタム設定の作成（例）
    custom_config = NovelWriterConfig(
        genres={
            "1": "ファンタジー",
            "2": "SF",
            "3": "恋愛",
            "4": "ミステリー",
            "5": "ホラー",
            "6": "歴史"
        },
        genre_descriptions={
            "1": "魔法や異世界が舞台のファンタジー作品",
            "2": "科学技術や未来社会を描くSF作品",
            "3": "人々の恋愛模様を描く恋愛作品",
            "4": "謎解きや事件を扱うミステリー作品",
            "5": "恐怖や超自然現象を描くホラー作品",
            "6": "歴史的な出来事や時代を描く作品"
        },
        default_requirements=[
            "魅力的な主人公",
            "起承転結のある物語展開",
            "読者を引き込む世界観",
            "印象的なクライマックス",
            "伏線の回収"
        ]
    )
    
    # セッションとコンポーネントの初期化
    session = Session(id="novel-session")
    llm_manager = LLMManager()
    director = DefaultDirectorAI(session, llm_manager)
    evaluator = DefaultEvaluatorAI(session, llm_manager)
    planner = DefaultPlannerAI(session, llm_manager)
    worker = DefaultWorkerAI(session, llm_manager)
    
    # 小説作成システムの実行
    writer = NovelWriter(
        session=session,
        director=director,
        evaluator=evaluator,
        planner=planner,
        worker=worker,
        config=custom_config  # カスタム設定を使用
    )
    writer.run()

if __name__ == "__main__":
    main()

