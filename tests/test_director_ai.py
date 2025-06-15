import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from orchestration.components.director import DefaultDirectorAI
from orchestration.core.session import Session
from orchestration.llm.llm_manager import LLMManager


async def test_director_integration():
    """
    Director AI の結果統合機能をテストする
    同じ入力に対して同じ出力が得られることを確認
    """
    print("=== Director AI 統合機能テスト ===")

    # テスト用データディレクトリの作成
    test_dir = Path("./tests/director_test_data")
    test_dir.mkdir(parents=True, exist_ok=True)

    # テスト用のセッション作成
    session = Session(id="test-director-session")
    session.mode = "creative"  # テンプレート名に合わせて明示的に設定

    # LLMManager初期化 (temperature=0 で決定論的な応答を得る)
    llm_manager = LLMManager(parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 2000})

    # Director AIインスタンス化
    director = DefaultDirectorAI(session, llm_manager)

    # テスト用の入力データ (サブタスク結果)
    test_results = [
        {
            "task_id": "subtask-1",
            "status": "completed",
            "result": {
                "content": "これはサブタスク1の結果です。重要なポイント: A, B, C",
                "requirements_met": ["要件1", "要件2"],
                "execution_time_ms": 1500,
            },
            "created_at": datetime.now().isoformat(),
        },
        {
            "task_id": "subtask-2",
            "status": "completed",
            "result": {
                "content": "サブタスク2の実行結果。分析結果: X, Y, Z",
                "requirements_met": ["要件3"],
                "execution_time_ms": 2000,
            },
            "created_at": datetime.now().isoformat(),
        },
    ]

    # テスト実行 (2回実行して結果を比較)
    print("最初の実行...")
    result1 = await director.integrate_results(test_results)

    # 結果をJSONファイルとして保存
    with open(test_dir / "director_result1.json", "w", encoding="utf-8") as f:
        json.dump(result1, f, ensure_ascii=False, indent=2)

    print("2回目の実行...")
    result2 = await director.integrate_results(test_results)

    # 2回目の結果を保存
    with open(test_dir / "director_result2.json", "w", encoding="utf-8") as f:
        json.dump(result2, f, ensure_ascii=False, indent=2)

    # 結果の比較
    are_identical = result1 == result2
    print(f"結果は一致しています: {are_identical}")

    if not are_identical:
        print("差異があります:")
        print(f"Result1: {result1.get('integrated_content', '')[:100]}...")
        print(f"Result2: {result2.get('integrated_content', '')[:100]}...")

    return are_identical, result1, result2


if __name__ == "__main__":
    asyncio.run(test_director_integration())
