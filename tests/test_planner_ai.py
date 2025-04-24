import asyncio
import json
import os
from typing import Dict, Any, List
from pathlib import Path

from orchestration.llm.llm_manager import LLMManager
from orchestration.components.planner import PlannerAI
from orchestration.core.session import Session
from orchestration.types import TaskModel

async def test_planner_task_planning():
    """
    Planner AI のタスク計画機能をテストする
    同じ入力に対して同じ出力が得られることを確認
    """
    print("=== Planner AI タスク計画機能テスト ===")
    
    # テスト用データディレクトリの作成
    test_dir = Path("./tests/planner_test_data")
    test_dir.mkdir(parents=True, exist_ok=True)
    
    # テスト用のセッション作成
    session = Session(id="test-planner-session")
    
    # LLMManager初期化 (temperature=0 で決定論的な応答を得る)
    llm_manager = LLMManager(
        parameters={"temperature": 0.0, "top_p": 1.0, "max_tokens": 2000}
    )
    
    # Planner AIインスタンス化
    planner = PlannerAI(session, llm_manager)
    
    # テスト用のタスク定義
    test_task = TaskModel(
        id="task-1",
        title="小説のプロット作成",
        description="ファンタジージャンルの短編小説のプロットを作成する。主人公は魔法使いの見習い。",
        requirements=["起承転結の構造", "予想外の展開を含める", "魔法のシステムを設計する"]
    )
    
    # テスト実行 (2回実行して結果を比較)
    print("最初の実行...")
    # タスクを追加
    session.add_subtask(test_task)
    
    # plan_task メソッドを呼び出し
    result1 = await planner.plan_task(test_task.id)
    
    # 結果をJSONファイルとして保存
    with open(test_dir / "planner_result1.json", "w", encoding="utf-8") as f:
        json.dump(result1, f, ensure_ascii=False, indent=2)
    
    print("2回目の実行...")
    result2 = await planner.plan_task(test_task.id)
    
    # 2回目の結果を保存
    with open(test_dir / "planner_result2.json", "w", encoding="utf-8") as f:
        json.dump(result2, f, ensure_ascii=False, indent=2)
    
    # 結果の比較
    are_identical = result1 == result2
    print(f"結果は一致しています: {are_identical}")
    
    if not are_identical:
        print("差異があります:")
        # サブタスクの数を比較
        subtasks1 = result1.get("subtasks", [])
        subtasks2 = result2.get("subtasks", [])
        print(f"サブタスク数: {len(subtasks1)} vs {len(subtasks2)}")
        
        # 戦略を比較
        strategy1 = result1.get("strategy", "")
        strategy2 = result2.get("strategy", "")
        print(f"戦略: '{strategy1[:50]}...' vs '{strategy2[:50]}...'")
    
    return are_identical, result1, result2

if __name__ == "__main__":
    asyncio.run(test_planner_task_planning())