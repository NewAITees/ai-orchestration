from typing import Dict, List

from app.cui.novel_writer import NovelWriter, NovelWriterConfig, NovelWriterInput
from app.llm.llm_manager import LLMManager
from app.orchestration.components.director import DefaultDirectorAI
from app.orchestration.components.planner import DefaultPlannerAI
from app.orchestration.components.reviewer import ReviewerAI
from app.orchestration.components.worker import DefaultWorkerAI
from app.orchestration.core.session import Session


def create_sample_config() -> NovelWriterConfig:
    """サンプル設定を作成"""
    return NovelWriterConfig(
        genres={
            "1": "現代ファンタジー",
            "2": "ハードSF",
            "3": "ラブコメディ",
            "4": "ミステリー",
            "5": "パニックホラー",
            "6": "時代小説",
        },
        genre_descriptions={
            "1": "現代社会を舞台に不思議な出来事が起こるファンタジー作品",
            "2": "科学的な考証を重視したSF作品",
            "3": "笑いと恋愛を織り交ぜたラブコメディ作品",
            "4": "論理的な謎解きを楽しむミステリー作品",
            "5": "恐怖と混乱の中で生き抜くホラー作品",
            "6": "日本の歴史を舞台にした時代小説",
        },
        default_requirements=[
            "個性的な登場人物",
            "予想外の展開",
            "緻密な世界設定",
            "印象的な名シーン",
            "読後感の良いエンディング",
        ],
    )


def create_sample_input() -> NovelWriterInput:
    """サンプル入力データを作成"""
    return NovelWriterInput(
        title="月光の魔法使い",
        genre="現代ファンタジー",
        requirements=[
            "都会に潜む魔法の存在",
            "主人公の成長物語",
            "現代社会と魔法の融合",
            "謎めいた敵の存在",
            "仲間との絆",
        ],
        revisions={
            # タスクIDに対する修正内容を指定可能
            # "task-1": ["修正内容1", "修正内容2"]
        },
    )


def run_novel_writer(
    session_id: str = "sample-novel-session",
    task: str = "小説執筆",
    mode: str = "creative",
    config: NovelWriterConfig = None,
    input_data: NovelWriterInput = None,
) -> None:
    """NovelWriterを実行"""
    # セッションの初期化
    session = Session(id=session_id, task=task, mode=mode)

    # 必要なコンポーネントの初期化
    llm_manager = LLMManager()
    director = DefaultDirectorAI(session, llm_manager)
    evaluator = ReviewerAI(session, llm_manager)
    planner = DefaultPlannerAI(session, llm_manager)
    worker = DefaultWorkerAI(session, llm_manager)

    # 設定とデータの準備
    if config is None:
        config = create_sample_config()
    if input_data is None:
        input_data = create_sample_input()

    # NovelWriterの初期化と実行
    writer = NovelWriter(
        session=session,
        director=director,
        evaluator=evaluator,
        planner=planner,
        worker=worker,
        config=config,
        input_data=input_data,
    )

    # 実行
    writer.run()


if __name__ == "__main__":
    # デフォルトの設定と入力データで実行
    run_novel_writer()
