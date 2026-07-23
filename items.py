import streamlit as st
import copy


class BaseItem:
    """모든 아이템의 기본 클래스"""

    def __init__(self, name: str, cost_ratio: float, description: str):
        self.name = name
        self.cost_ratio = cost_ratio
        self.description = description

    def use(self, state, df) -> bool:
        """아이템 효과 실행. 사용 성공 시 True, 취소/실패 시 False 반환"""
        raise NotImplementedError


class YetoItem(BaseItem):
    def __init__(self):
        super().__init__("예토전생 🧟‍♂️", 0.50, "시작 전 자산으로 복구 및 종료")

    def use(self, state, df) -> bool:
        state.total_cash = state.initial_cash
        state.in_game = False
        st.toast("🧟‍♂️ 예토전생 발동! 시간을 되돌려 시작 전 자산으로 복구되었습니다.")
        return True


class AchaItem(BaseItem):
    def __init__(self):
        super().__init__("아차차 ⏪", 0.10, "3턴 전으로 돌아감")

    def use(self, state, df) -> bool:
        if len(state.history_snapshots) == 0:
            st.toast("⚠️ 돌아갈 이전 기록이 없습니다.", icon="⚠️")
            return False

        steps = min(3, len(state.history_snapshots))
        target = state.history_snapshots[-steps]
        state.history_snapshots = state.history_snapshots[:-steps]

        state.current_idx = target['idx']
        state.total_cash = target['cash']
        state.holdings_count = target['holdings']
        state.invested_amount = target['invested']
        state.turns_left = target['turns']
        state.last_sell_profit = target['last_profit']
        state.trade_history = copy.deepcopy(target['trades'])

        st.toast(f"⏪ 아차차 발동! {steps}턴 전으로 타임리프했습니다!")
        return True


class EyeItem(BaseItem):
    def __init__(self):
        super().__init__("예언자의 눈 🔮", 0.10, "3일 후 주가 확인")

    def use(self, state, df) -> bool:
        target_idx = state.current_idx + 3
        if target_idx < len(df):
            f_price = df.iloc[target_idx]['Adj Close']
            f_date = df.iloc[target_idx]['index'].strftime('%Y-%m-%d')
            st.info(f"🔮 **예언자의 눈:** 3일 후({f_date}) 종가는 👉 **{int(f_price):,}원** 입니다.")
            return True
        else:
            st.toast("⚠️ 미래의 주가 데이터가 없습니다.", icon="⚠️")
            return False


class DoubleItem(BaseItem):
    def __init__(self):
        super().__init__("더블 ✖️2️⃣", 0.10, "지난 매도 익절 수익 1번 더 획득")

    def use(self, state, df) -> bool:
        if state.last_sell_profit <= 0:
            st.toast("⚠️ 직전 매도에서 익절 수익이 없었습니다.", icon="⚠️")
            return False
        state.total_cash += state.last_sell_profit
        st.toast(f"✖️2️⃣ 더블 발동! 매도 수익 {int(state.last_sell_profit):,}원을 한 번 더 받았습니다!")
        return True


class TripleItem(BaseItem):
    def __init__(self):
        super().__init__("트리플 ✖️3️⃣", 0.20, "지난 매도 익절 수익 2번 더 획득")

    def use(self, state, df) -> bool:
        if state.last_sell_profit <= 0:
            st.toast("⚠️ 직전 매도에서 익절 수익이 없었습니다.", icon="⚠️")
            return False
        bonus = state.last_sell_profit * 2.0
        state.total_cash += bonus
        st.toast(f"✖️3️⃣ 트리플 발동! 지난 수익의 2배({int(bonus):,}원)를 추가 획득했습니다!")
        return True


class CutterItem(BaseItem):
    def __init__(self):
        super().__init__("절단기 ✂️", 0.30, "지난 매도 손실액의 50% 복구")

    def use(self, state, df) -> bool:
        if state.last_sell_profit >= 0:
            st.toast("⚠️ 직전 매도에서 손실이 발생하지 않았습니다.", icon="⚠️")
            return False
        refund = abs(state.last_sell_profit) * 0.50
        state.total_cash += refund
        st.toast(f"✂️ 절단기 발동! 매도 손실액의 절반({int(refund):,}원)을 복구했습니다!")
        return True


class MerongItem(BaseItem):
    def __init__(self):
        super().__init__("메롱 😜", 0.10, "어제(1일 전) 종가로 전량 매도")

    def use(self, state, df) -> bool:
        if state.holdings_count <= 0:
            st.toast("⚠️ 보유 주식이 없습니다.", icon="⚠️")
            return False
        if state.current_idx <= 0:
            st.toast("⚠️ 첫 번째 날에는 사용할 수 없습니다.", icon="⚠️")
            return False

        yesterday_price = float(df.iloc[state.current_idx - 1]['Adj Close'])
        raw_revenue = state.holdings_count * yesterday_price

        avg_price = state.invested_amount / state.holdings_count
        raw_profit = raw_revenue - (state.holdings_count * avg_price)

        # 캐릭터 패시브 적용
        from characters import CHARACTERS
        cur_char = CHARACTERS.get(state.selected_character, CHARACTERS["평범"])
        final_profit = cur_char.modify_sell_profit(raw_profit)
        final_revenue = (state.holdings_count * avg_price) + final_profit

        state.total_cash += final_revenue
        state.last_sell_profit = final_profit

        # 매도 마커 추가
        state.trade_history['sells'].append({'idx': state.current_idx, 'price': yesterday_price})

        state.holdings_count = 0
        state.invested_amount = 0.0

        st.toast(f"😜 메롱 발동! 어제 종가({int(yesterday_price):,}원)로 전량 매도 완료!")
        return True


ITEMS = [
    YetoItem(),
    AchaItem(),
    EyeItem(),
    DoubleItem(),
    TripleItem(),
    CutterItem(),
    MerongItem()
]
