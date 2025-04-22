import json
from typing import Dict, Any
from app.orchestration.core.session import Session, SubTask
from app.orchestration.core.message import OrchestrationMessage, MessageType, Component
from app.orchestration.components.reviewer import ReviewerAI
from app.llm.llm_manager import LLMManager

def print_evaluation_result(result: Dict[str, Any]) -> None:
    """評価結果を表示"""
    print("\n=== 評価結果 ===")
    print(f"タスクID: {result['task_id']}")
    print(f"スコア: {result['score']:.2f}")
    print(f"\nフィードバック:")
    print(f"{result['feedback']}")
    
    print("\nメトリクス:")
    metrics = result['metrics']
    print(f"- 品質: {metrics['quality']:.2f}")
    print(f"- 完成度: {metrics['completeness']:.2f}")
    print(f"- 関連性: {metrics['relevance']:.2f}")
    print(f"- 創造性: {metrics['creativity']:.2f}")
    print(f"- 技術的精度: {metrics['technical_accuracy']:.2f}")
    
    print("\n強み:")
    for strength in result['strengths']:
        print(f"- {strength}")
    
    print("\n改善点:")
    for area in result['areas_for_improvement']:
        print(f"- {area}")
    
    print("\n改善提案:")
    for suggestion in result['suggestions']:
        print(f"- {suggestion}")

def main():
    """CUIインターフェースのメイン関数"""
    print("Evaluator AI CLI")
    print("================")
    
    # セッションの作成
    session = Session("test_session")
    
    # LLMマネージャーの初期化
    llm_manager = LLMManager()
    
    # Evaluator AIの初期化
    evaluator = ReviewerAI(session, llm_manager)
    
    while True:
        print("\n1. タスクを評価する")
        print("2. 終了")
        choice = input("選択してください (1-2): ")
        
        if choice == "1":
            # タスク情報の入力
            task_id = input("タスクID: ")
            title = input("タスクタイトル: ")
            description = input("タスク説明: ")
            result = input("実行結果: ")
            
            # タスクの作成
            task = SubTask(
                id=task_id,
                title=title,
                description=description,
                result=result
            )
            
            # セッションにタスクを追加
            session.add_subtask(task)
            
            # 評価メッセージの作成
            message = OrchestrationMessage(
                type=MessageType.COMMAND,
                sender=Component.DIRECTOR,
                receiver=Component.EVALUATOR,
                content={"action": "evaluate_task", "task_id": task_id},
                session_id=session.id
            )
            
            # メッセージの処理
            responses = evaluator.process_message(message)
            
            # 結果の表示
            if responses and responses[0].type == MessageType.RESPONSE:
                print_evaluation_result(responses[0].content["result"])
            else:
                print("エラーが発生しました:", responses[0].content["error"])
        
        elif choice == "2":
            print("終了します。")
            break
        
        else:
            print("無効な選択です。")

if __name__ == "__main__":
    main() 