import asyncio
import json
import os
from typing import Dict, Any, List
from pathlib import Path

from orchestration.llm.llm_manager import LLMManager
from orchestration.components.worker import WorkerAI
from orchestration.core.session import Session, SubTask

async def test_worker_task_execution():
    """
    Worker AI のタスク実行機能をテストする
    同じ入力に対して同じ出力が得られることを確認
    """
    print("=== Worker AI タスク実行機能テスト ===")
    
    # テスト用データディレクトリの作成
    test_dir = Path("./tests/worker_test_data")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # テスト用のセッション作成
    session = Session(id="test-worker-session")
    
    # LLMManager初期化 (temperature=0 で決定論的な応答を得る)
    llm_manager = LLMManager(
        parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 2000}
    )
    
    # Worker AIインスタンス化
    worker = WorkerAI(session, llm_manager)
    
    # テスト用のサブタスク
    test_subtask = SubTask(
        id="subtask-1",
        title="キャラクター設定の作成",
        description="魔法使いの見習いである主人公のキャラクター設定を作成する",
        requirements=["明確な背景設定", "独自の魔法の能力", "内面的な葛藤"]
    )
    
    # コンテキスト情報
    context = {
        "world_setting": "中世ファンタジー世界",
        "magic_system": "属性魔法（火、水、風、土）が基本",
        "story_tone": "成長物語"
    }
    
    # テスト実行 (2回実行して結果を比較)
    print("最初の実行...")
    result1 = await worker.execute_task(test_subtask, context=context)
    
    # 結果をJSONファイルとして保存 (TaskExecutionResultオブジェクトを辞書に変換)
    with open(test_dir / "worker_result1.json", "w", encoding="utf-8") as f:
        # taskStatusをstring形式に変換
        result_dict1 = result1.model_dump()
        json.dump(result_dict1, f, ensure_ascii=False, indent=2, default=str)
    
    print("2回目の実行...")
    result2 = await worker.execute_task(test_subtask, context=context)
    
    # 2回目の結果を保存
    with open(test_dir / "worker_result2.json", "w", encoding="utf-8") as f:
        result_dict2 = result2.model_dump()
        json.dump(result_dict2, f, ensure_ascii=False, indent=2, default=str)
    
    # 結果の比較（モデルオブジェクトを辞書にして比較）
    result_dict1 = result1.model_dump()
    result_dict2 = result2.model_dump()
    
    # 日時フィールドを除外して比較（それらは常に異なる）
    for r in [result_dict1, result_dict2]:
        if "created_at" in r:
            del r["created_at"]
    
    are_identical = result_dict1 == result_dict2
    print(f"結果は一致しています: {are_identical}")
    
    if not are_identical:
        print("差異があります:")
        # 実行結果のコンテンツを比較
        content1 = result_dict1.get("result", {}).get("content", "")
        content2 = result_dict2.get("result", {}).get("content", "")
        print(f"Content1: {content1[:100]}...")
        print(f"Content2: {content2[:100]}...")
    
    return are_identical, result_dict1, result_dict2

if __name__ == "__main__":
    asyncio.run(test_worker_task_execution())