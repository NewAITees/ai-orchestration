from typing import Dict, Any, List, TypeVar, Optional
from datetime import datetime
import json
import uuid

T = TypeVar('T')

def generate_id(prefix: str = "") -> str:
    """ユニークIDの生成"""
    unique_id = str(uuid.uuid4())
    return f"{prefix}-{unique_id}" if prefix else unique_id

def current_timestamp() -> str:
    """現在のタイムスタンプを取得"""
    return datetime.now().isoformat()

def json_serialize(obj: Any) -> str:
    """オブジェクトをJSON文字列にシリアライズ"""
    class DateTimeEncoder(json.JSONEncoder):
        def default(self, obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            return super().default(obj)
    
    return json.dumps(obj, cls=DateTimeEncoder)

def json_deserialize(json_str: str) -> Any:
    """JSON文字列からオブジェクトを復元"""
    return json.loads(json_str)

def safe_get(dictionary: Dict[str, Any], key_path: str, default: T = None) -> T:
    """ネストした辞書から安全にデータを取得"""
    keys = key_path.split('.')
    current = dictionary
    
    try:
        for key in keys:
            if isinstance(current, dict):
                current = current.get(key)
            else:
                return default
        return current if current is not None else default
    except Exception:
        return default

def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """2つの辞書を再帰的にマージ"""
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
            
    return result 