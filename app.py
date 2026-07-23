import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import copy
import os

# 📦 모듈 임포트 (기존 items.py, characters.py 그대로 활용)
from items import ITEMS
from characters import CHARACTERS

# 한글 폰트 및 페이지 설정
st.set_page_config(page_title="턴제 주식 게임", page_icon="📈", layout="centered")
plt.rcParams['font.family'] = 'AppleGothic'  # 서버 환경에 따라 Sans-serif 기본 사용 가능
plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 1. 상태(Session State) 초기화
# ==========================================
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.total_cash = 10_000_000.0
    st.session_state.character_coins = 2
    st.session_state.selected_character = "평범"
    st.session_state.unlocked_characters = {name: (name == "평범") for name in CHARACTERS.keys()}
    st.session_state.inventory = {item.name: 0 for item in ITEMS}
    st.session_state.game_history = []
    st.session_state.in_game = False


# 데이터 로드 (상대 경로)
@st.cache_data
def load_data():
    df = pd.read_csv('11114.csv)  # 상대 경로로 수정
    df['index'] = pd.to_datetime(df['index'])
    return df


try:
    df = load_data()
except Exception as e:
    st.error(f"11114.csv 파일을 찾을 수 없습니다: {e}")
    st.stop()


# ==========================================
# 2. 메인 대기 화면 (시작 화면)
# ==========================================
def show_start_screen():
    st.title("🏛️ 턴제 주식 게임 🏛️")

    # 통산 성적판
    st.subheader("📊 통산 성적판")
    total_games = len(st.session_state.game_history)
    wins = sum(1 for g in st.session_state.game_history if g['wins'])
    losses = total_games - wins
    win_rate = (wins / total_games * 100) if total_games > 0 else 0.0

    st.info(f"전적: **{wins}승 {losses}패** (승률 **{win_rate:.1f}%**)")

    # 현재 캐릭터
    cur_char = CHARACTERS.get(st.session_state.selected_character, CHARACTERS["평범"])
    st.write(f"🎭 **현재 캐릭터:** {cur_char.emoji} **{cur_char.name}** - {cur_char.description}")

    # 자산 및 초기화
    st.success(f"💰 현재 총자산: **{int(st.session_state.total_cash):,}원**")
    if st.session_state.total_cash <= 1_000_000:
        if st.button("💥 자산 초기화 (1,000만원 복구)"):
            st.session_state.total_cash = 10_000_000.0
            st.rerun()

    # 상점
    st.subheader("🛒 아이템 상점")
    for item in ITEMS:
        col1, col2 = st.columns([3, 1])
        qty = st.session_state.inventory[item.name]
        cost = int(st.session_state.total_cash * item.cost_ratio)
        col1.write(f"**{item.name}** (비용: {int(item.cost_ratio * 100)}% / 보유: {qty}개)\n_{item.description}_")
        if col2.button(f"구매 ({cost:,}원)", key=f"buy_{item.name}"):
            if st.session_state.total_cash >= cost and st.session_state.total_cash > 0:
                st.session_state.total_cash -= cost
                st.session_state.inventory[item.name] += 1
                st.rerun()
            else:
                st.warning("자산이 부족합니다!")

    st.divider()
    if st.button("🎮 게임 시작 🎮", use_container_width=True, type="primary"):
        # 게임 전용 세션 초기화
        target_matches = df[df['index'] == '2017-12-01']
        st.session_state.start_idx = target_matches.index[0] if not target_matches.empty else 30
        st.session_state.current_idx = st.session_state.start_idx
        st.session_state.turns_left = 100
        st.session_state.holdings_count = 0
        st.session_state.average_buy_price = 0.0
        st.session_state.initial_cash = st.session_state.total_cash
        st.session_state.buy_signals = {}
        st.session_state.sell_signals = {}
        st.session_state.in_game = True
        st.rerun()


# ==========================================
# 3. 인게임 화면
# ==========================================
def show_game_screen():
    row = df.iloc[st.session_state.current_idx]
    current_price = row['Adj Close']
    date_str = row['index'].strftime('%Y-%m-%d')
    total_asset = st.session_state.total_cash + (st.session_state.holdings_count * current_price)

    # 상단 헤더
    col1, col2, col3 = st.columns([2, 1, 1])
    col1.subheader(f"📅 {date_str}")
    col2.metric("남은 턴", f"{st.session_state.turns_left}턴")
    if col3.button("🛑 그만하기"):
        auto_sell_and_end()

    # 캐릭터 및 보유 아이템
    cur_char = CHARACTERS.get(st.session_state.selected_character, CHARACTERS["평범"])
    st.caption(f"🎭 **캐릭터:** {cur_char.emoji} {cur_char.name} ({cur_char.description})")

    # 인게임 아이템 사용
    st.write("🎒 **보유 아이템:**")
    item_cols = st.columns(len(ITEMS))
    for idx, item in enumerate(ITEMS):
        qty = st.session_state.inventory[item.name]
        if item_cols[idx].button(f"{item.name}\n[{qty}개]", key=f"use_{item.name}"):
            if qty > 0:
                # 아이템 사용 로직 연결
                st.session_state.inventory[item.name] -= 1
                st.success(f"{item.name} 사용 완료!")
                st.rerun()
            else:
                st.warning("보유 수량이 없습니다.")

    # 차트 시각화
    start_idx = max(0, st.session_state.current_idx - 30)
    view_df = df.iloc[start_idx: st.session_state.current_idx + 1]

    fig, ax = plt.subplots(figsize=(6, 3))
    ax.plot(view_df['index'], view_df['Adj Close'], label='종가', color='black', linewidth=1.5)
    ax.set_title("최근 30일 주가 추이")
    ax.grid(True, alpha=0.3)
    st.pyplot(fig)

    # 자산 정보
    st.metric("현재 주가", f"{int(current_price):,}원")
    st.metric("총 자산", f"{int(total_asset):,}원", delta=f"{total_asset - st.session_state.initial_cash:,.0f}원")

    # 매수/매도 컨트롤
    trade_percent = st.slider("투자 비중 (%)", 10, 100, 50, 10)

    b_col, p_col, s_col = st.columns(3)
    if b_col.button("구 매 📈", use_container_width=True):
        budget = st.session_state.total_cash * (trade_percent / 100.0)
        cnt = int(budget // current_price)
        if cnt > 0:
            st.session_state.holdings_count += cnt
            st.session_state.total_cash -= cnt * current_price
        next_turn()

    if p_col.button("관 망 ☕", use_container_width=True):
        next_turn()

    if s_col.button("판 매 📉", use_container_width=True):
        cnt = int(st.session_state.holdings_count * (trade_percent / 100.0))
        if cnt > 0:
            st.session_state.total_cash += cnt * current_price
            st.session_state.holdings_count -= cnt
        next_turn()


def next_turn():
    st.session_state.turns_left -= 1
    if st.session_state.turns_left <= 0 or st.session_state.current_idx >= len(df) - 1:
        auto_sell_and_end()
    else:
        st.session_state.current_idx += 1
        st.rerun()


def auto_sell_and_end():
    current_price = df.iloc[st.session_state.current_idx]['Adj Close']
    if st.session_state.holdings_count > 0:
        st.session_state.total_cash += st.session_state.holdings_count * current_price
        st.session_state.holdings_count = 0

    is_win = st.session_state.total_cash > st.session_state.initial_cash
    st.session_state.game_history.append({'wins': is_win})
    st.session_state.in_game = False
    st.rerun()


# 메인 실행 조건
if st.session_state.in_game:
    show_game_screen()
else:
    show_start_screen()
