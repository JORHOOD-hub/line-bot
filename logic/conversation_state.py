import json
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from utils.config import config

@dataclass
class UserState:
    """ユーザーの会話状態"""
    user_id: str
    state: str  # waiting_pdf, waiting_price, waiting_down_payment, waiting_expiration, generating, completed
    property_data: Dict[str, Any] = None
    timestamp: str = None

    def __post_init__(self):
        if self.property_data is None:
            self.property_data = {}
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        """辞書に変換"""
        data = asdict(self)
        return data

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'UserState':
        """辞書から復元"""
        return UserState(
            user_id=data.get('user_id'),
            state=data.get('state'),
            property_data=data.get('property_data', {}),
            timestamp=data.get('timestamp')
        )


class ConversationStateManager:
    """JSON ファイルベースのステート管理"""

    def __init__(self, state_file_path: str = None):
        self.state_file_path = Path(state_file_path or config.STATE_FILE_PATH)
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """ステートファイルが存在しない場合は作成"""
        if not self.state_file_path.exists():
            self._write_states({})

    def _read_states(self) -> Dict[str, Dict]:
        """ファイルからすべてのステートを読み込む"""
        try:
            with open(self.state_file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write_states(self, states: Dict[str, Dict]):
        """ステートをファイルに書き込む"""
        with open(self.state_file_path, 'w', encoding='utf-8') as f:
            json.dump(states, f, ensure_ascii=False, indent=2)

    def get_state(self, user_id: str) -> UserState:
        """ユーザーの状態を取得"""
        states = self._read_states()
        if user_id in states:
            return UserState.from_dict(states[user_id])
        # 新規ユーザーは待機状態
        return UserState(user_id=user_id, state='waiting_pdf')

    def set_state(self, user_state: UserState):
        """ユーザーの状態を保存"""
        states = self._read_states()
        states[user_state.user_id] = user_state.to_dict()
        self._write_states(states)

    def update_property_data(self, user_id: str, key: str, value: Any):
        """物件データを更新"""
        user_state = self.get_state(user_id)
        user_state.property_data[key] = value
        user_state.timestamp = datetime.now().isoformat()
        self.set_state(user_state)

    def clear_state(self, user_id: str):
        """ユーザーの状態をリセット"""
        states = self._read_states()
        if user_id in states:
            del states[user_id]
        self._write_states(states)

    def get_all_states(self) -> Dict[str, UserState]:
        """すべてのユーザーの状態を取得（デバッグ用）"""
        states = self._read_states()
        return {user_id: UserState.from_dict(data) for user_id, data in states.items()}


# グローバルインスタンス
state_manager = ConversationStateManager()
