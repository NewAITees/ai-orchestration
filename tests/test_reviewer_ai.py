import asyncio
import json
import os
from typing import Dict, Any, List
from pathlib import Path

from orchestration.llm.llm_manager import LLMManager
from orchestration.components.reviewer import ReviewerAI
from orchestration.core.session import Session, SubTask
from orchestration.types import TaskExecutionResult, TaskStatus

async def test_reviewer_task_evaluation():
    """
    Reviewer AI の評価機能をテストする
    同じ入力に対して同じ出力が得られることを確認
    """
    print("=== Reviewer AI 評価機能テスト ===")
    
    # テスト用データディレクトリの作成
    test_dir = Path("./tests/reviewer_test_data")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # テスト用のセッション作成
    session = Session(id="test-reviewer-session")
    
    # LLMManager初期化 (temperature=0 で決定論的な応答を得る)
    llm_manager = LLMManager(
        parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 2000}
    )
    
    # Reviewer AIインスタンス化
    reviewer = ReviewerAI(session, llm_manager)
    
    # テスト用のサブタスクと実行結果
    test_subtask = SubTask(
        id="subtask-1",
        title="プロット概要の作成",
        description="ファンタジー短編小説のプロット概要の作成",
        requirements=["起承転結の構造", "予想外の展開", "明確なテーマ"]
    )
    
    test_result = TaskExecutionResult(
        task_id=test_subtask.id,
        status=TaskStatus.COMPLETED,
        result={
            "content": """
            魔法使いの見習いであるマリオンは、師匠から禁じられていた禁忌の魔法書を偶然見つける。
            好奇心から呪文を唱えてしまったマリオンは、自分の影が実体化し、暴走するという問題を引き起こす。
            影は次第に力を増し、町の人々を脅かし始める。マリオンは師匠の助けを借りることなく問題を解決しようとするが失敗を重ねる。
            最終的にマリオンは、魔法の本質は力ではなく責任であることを理解し、自分の弱さを認めて師匠に助けを求める。
            二人の協力により影を鎮め、マリオンは真の魔法使いへの一歩を踏み出す。
            """
        }
    )
    
    # テスト実行 (2回実行して結果を比較)
    print("最初の実行...")
    # サブタスクをセッションに追加
    session.add_subtask(test_subtask)
    
    # review_task メソッドを呼び出し
    result1 = reviewer.review_task(test_subtask, test_result)
    
    # 結果をJSONファイルとして保存
    with open(test_dir / "reviewer_result1.json", "w", encoding="utf-8") as f:
        json.dump(result1.model_dump(), f, ensure_ascii=False, indent=2, default=str)
    
    print("2回目の実行...")
    result2 = reviewer.review_task(test_subtask, test_result)
    
    # 2回目の結果を保存
    with open(test_dir / "reviewer_result2.json", "w", encoding="utf-8") as f:
        json.dump(result2.model_dump(), f, ensure_ascii=False, indent=2, default=str)
    
    # 結果の比較
    result_dict1 = result1.model_dump()
    result_dict2 = result2.model_dump()
    
    are_identical = result_dict1 == result_dict2
    print(f"結果は一致しています: {are_identical}")
    
    if not are_identical:
        print("差異があります:")
        # スコアを比較
        score1 = result_dict1.get("score", 0)
        score2 = result_dict2.get("score", 0)
        print(f"スコア: {score1} vs {score2}")
        
        # フィードバックの先頭部分を比較
        feedback1 = result_dict1.get("feedback", "")
        feedback2 = result_dict2.get("feedback", "")
        print(f"フィードバック1: {feedback1[:100]}...")
        print(f"フィードバック2: {feedback2[:100]}...")
    
    return are_identical, result_dict1, result_dict2

if __name__ == "__main__":
    asyncio.run(test_reviewer_task_evaluation())