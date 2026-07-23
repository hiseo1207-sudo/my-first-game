from tkinter import messagebox


class BaseCharacter:
    """모든 캐릭터의 기본 클래스"""
    def __init__(self, name: str, emoji: str, description: str, cost: int):
        self.name = name
        self.emoji = emoji
        self.description = description
        self.cost = cost  # 해금에 필요한 코인 수

    def on_game_start(self, app):
        """게임 시작 시 실행되는 이벤트 패시브"""
        pass

    def modify_sell_profit(self, raw_profit: float) -> float:
        """매도 시 수익/손실액을 변형하는 이벤트 패시브"""
        return raw_profit


class NormalCharacter(BaseCharacter):
    def __init__(self):
        super().__init__("평범", "😐", "능력치 없음 (기본 캐릭터)", 0)


class FoolCharacter(BaseCharacter):
    def __init__(self):
        super().__init__("기적의 바보", "🤪", "게임 시작 시 총 자산의 +5% 증식", 1)

    def on_game_start(self, app):
        app.total_cash *= 1.05
        messagebox.showinfo("기적의 바보 능력 발동!", "🤪 기적의 바보 능력으로 게임 시작 자산이 5% 증가했습니다!")


class MathCharacter(BaseCharacter):
    def __init__(self):
        super().__init__("까막눈 수학자", "🧮", "매도 시, 수익과 손해가 무조건 2배", 1)

    def modify_sell_profit(self, raw_profit: float) -> float:
        return raw_profit * 2.0


class PickpocketCharacter(BaseCharacter):
    def __init__(self):
        super().__init__("소매치기", "🥷", "매도 시 수익 +10% 추가, 손실 10% 환급", 1)

    def modify_sell_profit(self, raw_profit: float) -> float:
        if raw_profit > 0:
            return raw_profit * 1.10
        else:
            return raw_profit * 0.90


# 🎭 게임 캐릭터 레지스트리 (이름 기준 딕셔너리)
CHARACTERS = {
    "평범": NormalCharacter(),
    "기적의 바보": FoolCharacter(),
    "까막눈 수학자": MathCharacter(),
    "소매치기": PickpocketCharacter(),
}