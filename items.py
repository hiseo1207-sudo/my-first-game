# from tkinter import messagebox
import copy


class BaseItem:
    """모든 아이템의 기본 클래스"""
    def __init__(self, name: str, cost_ratio: float, description: str):
        self.name = name
        self.cost_ratio = cost_ratio  # 구매 비용 비율 (예: 0.1 = 자산의 10%)
        self.description = description

    def use(self, app) -> bool:
        """아이템 효과 실행. 사용 성공 시 True, 취소/실패 시 False 반환"""
        raise NotImplementedError


class YetoItem(BaseItem):
    def __init__(self):
        super().__init__("예토전생 🧟‍♂️", 0.50, "시작 전 자산으로 복구 및 종료")

    def use(self, app) -> bool:
        if messagebox.askyesno("예토전생 사용", "게임을 즉시 종료하고 게임 시작 전 자산으로 돌아갑니까?"):
            app.total_cash = app.initial_cash_before_game
            messagebox.showinfo("예토전생 발동", "시간을 되돌려 시작 전 자산으로 복구되었습니다!")
            app.show_start_screen()
            return True
        return False


class AchaItem(BaseItem):
    def __init__(self):
        super().__init__("아차차 ⏪", 0.10, "3턴 전으로 돌아감")

    def use(self, app) -> bool:
        if len(app.history) == 0:
            messagebox.showwarning("사용 불가", "돌아갈 이전 히스토리가 없습니다.")
            return False

        steps = min(3, len(app.history))
        target = app.history[-steps]
        app.history = app.history[:-steps]

        app.current_idx = target['idx']
        app.total_cash = target['cash']
        app.holdings_count = target['holdings']
        app.average_buy_price = target['avg_price']
        app.turns_left = target['turns']
        app.last_sell_profit = target['last_profit']
        app.buy_signals = copy.deepcopy(target['buys'])
        app.sell_signals = copy.deepcopy(target['sells'])

        app.update_chart()
        messagebox.showinfo("아차차 발동", f"{steps}턴 전으로 타임리프했습니다!")
        return True


class EyeItem(BaseItem):
    def __init__(self):
        super().__init__("예언자의 눈 🔮", 0.10, "3일 후 주가 확인")

    def use(self, app) -> bool:
        target_idx = app.current_idx + 3
        if target_idx < len(app.df):
            f_price = app.df.iloc[target_idx]['Adj Close']
            f_date = app.df.iloc[target_idx]['index'].strftime('%Y-%m-%d')
            messagebox.showinfo("예언자의 눈 🔮", f"3일 후({f_date}) 종가 예언:\n\n👉 {int(f_price):,}원 👈")
            return True
        else:
            messagebox.showwarning("사용 불가", "미래의 주가 데이터가 없습니다.")
            return False


class DoubleItem(BaseItem):
    def __init__(self):
        super().__init__("더블 ✖️2️⃣", 0.10, "지난 매도 익절 수익 1번 더 획득")

    def use(self, app) -> bool:
        if app.last_sell_profit <= 0:
            messagebox.showwarning("사용 불가", "직전 매도에서 수익(익절)이 발생하지 않았습니다.")
            return False
        app.total_cash += app.last_sell_profit
        messagebox.showinfo("더블 ✖️2️⃣ 발동", f"지난 매도 수익 {int(app.last_sell_profit):,}원을 한 번 더 받았습니다!")
        return True


class TripleItem(BaseItem):
    def __init__(self):
        super().__init__("트리플 ✖️3️⃣", 0.20, "지난 매도 익절 수익 2번 더 획득")

    def use(self, app) -> bool:
        if app.last_sell_profit <= 0:
            messagebox.showwarning("사용 불가", "직전 매도에서 수익(익절)이 발생하지 않았습니다.")
            return False
        bonus = app.last_sell_profit * 2.0
        app.total_cash += bonus
        messagebox.showinfo("트리플 ✖️3️⃣ 발동", f"지난 매도 수익의 2배({int(bonus):,}원)를 추가 획득했습니다!")
        return True


class CutterItem(BaseItem):
    def __init__(self):
        super().__init__("절단기 ✂️", 0.30, "지난 매도 손실액의 50% 복구")

    def use(self, app) -> bool:
        if app.last_sell_profit >= 0:
            messagebox.showwarning("사용 불가", "직전 매도에서 손실이 발생하지 않았습니다.")
            return False
        refund = abs(app.last_sell_profit) * 0.50
        app.total_cash += refund
        messagebox.showinfo("절단기 ✂️ 발동", f"지난 매도 손실액의 절반({int(refund):,}원)을 복구했습니다!")
        return True


class MerongItem(BaseItem):
    def __init__(self):
        super().__init__("메롱 😜", 0.10, "어제(1일 전) 종가로 전량 매도")

    def use(self, app) -> bool:
        if app.holdings_count <= 0:
            messagebox.showwarning("사용 불가", "보유 주식이 없습니다.")
            return False
        if app.current_idx <= 0:
            messagebox.showwarning("사용 불가", "첫 번째 날에는 메롱 아이템을 사용할 수 없습니다.")
            return False

        yesterday_price = app.df.iloc[app.current_idx - 1]['Adj Close']
        raw_revenue = app.holdings_count * yesterday_price
        raw_cost = app.holdings_count * app.average_buy_price
        raw_profit = raw_revenue - raw_cost

        app.total_cash += raw_revenue
        app.last_sell_profit = raw_profit
        app.holdings_count = 0
        app.average_buy_price = 0.0

        messagebox.showinfo("메롱 😜 발동", f"어제 종가({int(yesterday_price):,}원)로 전량 매도 완료되었습니다!")
        app.update_chart()
        return True


# 🎁 게임에서 사용할 전체 아이템 레지스트리
ITEMS = [
    YetoItem(),
    AchaItem(),
    EyeItem(),
    DoubleItem(),
    TripleItem(),
    CutterItem(),
    MerongItem()
]
