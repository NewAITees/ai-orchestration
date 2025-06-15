import asyncio
import glob
import json
import subprocess
import sys
import time
from pathlib import Path

import pytest

# テストモジュールをインポート
from tests.test_director_ai import test_director_integration
from tests.test_planner_ai import test_planner_task_planning
from tests.test_worker_ai import test_worker_task_execution


async def run_all_tests():
    """全テストを実行し、結果をまとめる"""
    print("=== AIオーケストレーションシステム 単独コンポーネントテスト ===")
    print("各コンポーネントがtemperature=0で同じ入力に対して同じ出力を生成するかテスト\n")

    # 結果保存用ディレクトリの作成
    base_dir = Path("./tests")
    results_dir = Path("./test_results")
    for dir_name in [
        "director_test_data",
        "planner_test_data",
        "worker_test_data",
        "reviewer_test_data",
    ]:
        (base_dir / dir_name).mkdir(parents=True, exist_ok=True)
    results_dir.mkdir(parents=True, exist_ok=True)

    # テスト結果の収集
    test_results = {}

    # 1. Director AIテスト
    print("\n=== Director AI テスト実行中... ===")
    try:
        director_identical, _director_result1, _director_result2 = await test_director_integration()
        test_results["director"] = {
            "success": director_identical,
            "message": "同じ入力に対して同じ出力が生成されました"
            if director_identical
            else "出力に差異があります",
            "results_dir": str(base_dir / "director_test_data"),
        }
    except Exception as e:
        print(f"Director AIテスト実行エラー: {e}")
        test_results["director"] = {
            "success": False,
            "message": f"テスト実行中にエラーが発生しました: {e!s}",
        }

    # 2. Planner AIテスト
    print("\n=== Planner AI テスト実行中... ===")
    try:
        planner_identical, _planner_result1, _planner_result2 = await test_planner_task_planning()
        test_results["planner"] = {
            "success": planner_identical,
            "message": "同じ入力に対して同じ出力が生成されました"
            if planner_identical
            else "出力に差異があります",
            "results_dir": str(base_dir / "planner_test_data"),
        }
    except Exception as e:
        print(f"Planner AIテスト実行エラー: {e}")
        test_results["planner"] = {
            "success": False,
            "message": f"テスト実行中にエラーが発生しました: {e!s}",
        }

    # 3. Worker AIテスト
    print("\n=== Worker AI テスト実行中... ===")
    try:
        worker_identical, _worker_result1, _worker_result2 = await test_worker_task_execution()
        test_results["worker"] = {
            "success": worker_identical,
            "message": "同じ入力に対して同じ出力が生成されました"
            if worker_identical
            else "出力に差異があります",
            "results_dir": str(base_dir / "worker_test_data"),
        }
    except Exception as e:
        print(f"Worker AIテスト実行エラー: {e}")
        test_results["worker"] = {
            "success": False,
            "message": f"テスト実行中にエラーが発生しました: {e!s}",
        }

    # 4. Reviewer AIテスト
    print("\n=== Reviewer AI テスト実行中... ===")
    try:
        # pytestを別プロセスで実行
        result = subprocess.run(
            ["poetry", "run", "pytest", "-v", "tests/test_reviewer_ai.py"],
            capture_output=True,
            text=True,
        )
        reviewer_success = result.returncode == 0
        test_results["reviewer"] = {
            "success": reviewer_success,
            "message": "テストが成功しました" if reviewer_success else "テストが失敗しました",
            "results_dir": str(base_dir / "reviewer_test_data"),
        }
        # 出力ファイルの有無を確認
        reviewer_files = list(Path("./tests/reviewer_test_data").glob("evaluation_history_*.json"))
        if not reviewer_files:
            print(
                "[WARNING] Reviewerテストの出力ファイルが生成されていません。テストコードやパスを確認してください。"
            )
        else:
            print(f"Reviewerテスト出力ファイル: {reviewer_files[-1]}")
    except Exception as e:
        print(f"Reviewer AIテスト実行エラー: {e}")
        test_results["reviewer"] = {
            "success": False,
            "message": f"テスト実行中にエラーが発生しました: {e!s}",
        }

    # 結果のサマリーを作成
    success_count = sum(1 for r in test_results.values() if r["success"])
    total_count = len(test_results)

    summary = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "success_rate": f"{success_count}/{total_count}",
        "component_results": test_results,
    }

    # 結果を保存
    with open(results_dir / "test_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    # 結果を表示
    print("\n=== テスト結果サマリー ===")
    print(f"成功率: {success_count}/{total_count}")
    for component, result in test_results.items():
        status = "✅ 成功" if result["success"] else "❌ 失敗"
        print(f"{component}: {status} - {result['message']}")
        if "results_dir" in result:
            print(f"  結果ディレクトリ: {result['results_dir']}")

    print(f"\n詳細な結果は {results_dir} に保存されています")

    return summary


if __name__ == "__main__":
    asyncio.run(run_all_tests())
