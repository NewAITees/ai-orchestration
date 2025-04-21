import pytest
from unittest.mock import Mock, patch
from app.cui.creative_mode import CreativeModeSession

def test_creative_mode_session():
    # テストセッションの作成
    test_session = CreativeModeSession()
    
    # モックの設定
    mock_input = Mock()
    mock_output = Mock()
    mock_output.outputs = []
    
    # 入力のシミュレーション
    mock_input.side_effect = [
        "1",  # プロジェクトタイプ選択
        "魔法学校での冒険",  # タイトル
        "y",  # 要件追加
        "主人公は魔法の才能を持つ少年",  # 要件1
        "y",  # 要件追加
        "敵は邪悪な魔法使い",  # 要件2
        "y",  # 要件追加
        "最終目標は魔法の杖を手に入れること",  # 要件3
        "n",  # 要件追加終了
    ]
    
    # テスト実行
    with patch("builtins.input", mock_input), patch("builtins.print", lambda x: mock_output.outputs.append(str(x))):
        test_session.run()
    
    # 出力の検証
    outputs = mock_output.outputs
    assert any("プロジェクトの種類を選択してください" in out for out in outputs)
    assert any("タイトルを入力してください" in out for out in outputs)
    assert any("要件を追加しますか?" in out for out in outputs)
    assert any("サブタスクが生成されました" in out for out in outputs)
    assert any("評価結果" in out for out in outputs)
    
    # セッションの状態検証
    assert test_session.title == "魔法学校での冒険"
    assert len(test_session.requirements) == 3
    assert len(test_session.tasks) > 0
    assert any(task.status == "completed" for task in test_session.tasks)
    assert any("主人公は魔法の才能を持つ少年" in requirement for requirement in test_session.requirements)
