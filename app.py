import streamlit as st
import pandas as pd
import copy
import os
import plotly.graph_objects as go

# 📦 모듈 임포트 (수정된 items.py, characters.py)
from items import ITEMS
from characters import CHARACTERS


# 버전 호환성 대응 리런 함수
def safe_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# 페이지 기본 설정
st.set_page_config(page_title="턴제 주식 게임", page_icon="📈", layout="centered")

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

    # 📝 인게임 상태 변수들
    st.session_state.invested_amount = 0.0  # 매수 원금
    st.session_state.history_snapshots = []  # 아차차 아이템용 히스토리
    st.session_state.last_sell_profit = 0.0  # 아이템/캐릭터 패시브용 직전 매도 수익
    st.session_state.trade_history = {'buys': [], 'sells': []}  # 차트 표시용 매매 기록


@st.cache_data
def load_data():
    csv_path = os.path.join(os.path.dirname(__file__), '11114.csv') if '__file__' in globals() else '11114.csv'
    df = pd.read_csv(csv_path)
    df['index'] = pd.to_datetime(df['index'])

    price_cols = ['Open', 'High', 'Low', 'Close', 'Adj Close']
    for col in price_cols:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].astype(str).str.replace(',', '')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    df.ffill(inplace=True)
    df.bfill(inplace=True)
    return df


try:
    df = load_data()
except Exception as e:
    st.error(f"11114.csv 파일을 찾을 수 없습니다: {e}")
    st.stop()


# ==========================================
# 2. 메인 화면 (상점 및 시작)
# ==========================================
def show_start_screen():
    st.title("🏛️ 턴제 트레이딩 게임 🏛️")

    st.subheader("📊 통산 성적판")
    total_games = len(st.session_state.game_history)
    wins = sum(1 for g in st.session_state.game_history if g['wins'])
    losses = total_games - wins
    win_rate = (wins / total_games * 100) if total_games > 0 else 0.0
    st.info(f"전적: **{wins}승 {losses}패** (승률 **{win_rate:.1f}%**)")

    st.subheader("🎭 캐릭터 선택")
    unlocked_chars = [n for n, u in st.session_state.unlocked_characters.items() if u]
    if not unlocked_chars: unlocked_chars = ["평범"]
    default_idx = unlocked_chars.index(
        st.session_state.selected_character) if st.session_state.selected_character in unlocked_chars else 0
    st.session_state.selected_character = st.selectbox("플레이할 캐릭터", unlocked_chars, index=default_idx)

    cur_char = CHARACTERS.get(st.session_state.selected_character, CHARACTERS["평범"])
    st.write(f"👉 **현재 캐릭터:** {cur_char.emoji} **{cur_char.name}** - {cur_char.description}")

    st.success(f"💰 현재 총자산: **{int(st.session_state.total_cash):,}원**")
    if st.session_state.total_cash <= 1_000_000:
        if st.button("💥 자산 초기화 (1,000만원 복구)", use_container_width=True):
            st.session_state.total_cash = 10_000_000.0
            safe_rerun()

    st.subheader("🛒 아이템 상점")
    for item in ITEMS:
        c1, c2 = st.columns([3, 1])
        qty = st.session_state.inventory[item.name]
        cost = int(st.session_state.total_cash * item.cost_ratio)
        c1.write(f"**{item.name}** (비용: {int(item.cost_ratio * 100)}% / 보유: {qty}개)\n_{item.description}_")
        if c2.button(f"구매 ({cost:,}원)", key=f"buy_{item.name}"):
            if st.session_state.total_cash >= cost and st.session_state.total_cash > 0:
                st.session_state.total_cash -= cost
                st.session_state.inventory[item.name] += 1
                safe_rerun()
            else:
                st.warning("자산이 부족합니다!")

    st.divider()
    if st.button("🎮 게임 시작 🎮", use_container_width=True, type="primary"):
        target_matches = df[df['index'] == '2017-12-01']
        st.session_state.start_idx = target_matches.index[0] if not target_matches.empty else 30
        st.session_state.current_idx = st.session_state.start_idx
        st.session_state.turns_left = 100
        st.session_state.holdings_count = 0
        st.session_state.invested_amount = 0.0
        st.session_state.initial_cash = st.session_state.total_cash

        st.session_state.history_snapshots = []
        st.session_state.last_sell_profit = 0.0
        st.session_state.trade_history = {'buys': [], 'sells': []}
        st.session_state.in_game = True

        # 🎭 게임 시작 캐릭터 패시브 발동
        CHARACTERS.get(st.session_state.selected_character).on_game_start(st.session_state)
        safe_rerun()


def save_snapshot():
    # 턴 넘어가기 전 아차차 아이템용 백업 저장
    snap = {
        'idx': st.session_state.current_idx,
        'cash': st.session_state.total_cash,
        'holdings': st.session_state.holdings_count,
        'invested': st.session_state.invested_amount,
        'turns': st.session_state.turns_left,
        'last_profit': st.session_state.last_sell_profit,
        'trades': copy.deepcopy(st.session_state.trade_history)
    }
    st.session_state.history_snapshots.append(snap)
    if len(st.session_state.history_snapshots) > 10:
        st.session_state.history_snapshots.pop(0)


# ==========================================
# 3. 인게임 화면
# ==========================================
def show_game_screen():
    row = df.iloc[st.session_state.current_idx]
    current_price = float(row['Adj Close'])

    # 상단 헤더
    col1, col2, col3 = st.columns([2, 1, 1])
    cur_char = CHARACTERS.get(st.session_state.selected_character, CHARACTERS["평범"])
    col1.markdown(f"**🎭 {cur_char.emoji} {cur_char.name}**")
    col2.metric("남은 턴", f"{st.session_state.turns_left}턴")
    if col3.button("🛑 종료", use_container_width=True):
        auto_sell_and_end()

    # 인게임 아이템 사용
    st.write("🎒 **보유 아이템:**")
    item_cols = st.columns(len(ITEMS))
    for idx, item in enumerate(ITEMS):
        qty = st.session_state.inventory[item.name]
        if item_cols[idx].button(f"{item.name}\n({qty}개)", key=f"use_{item.name}"):
            if qty > 0:
                success = item.use(st.session_state, df)
                if success:
                    st.session_state.inventory[item.name] -= 1
                    safe_rerun()
            else:
                st.warning("수량 부족")

    # 🕯️ 최근 30일 Plotly 캔들 차트 + 현재가 + 매매 내역
    start_idx = max(0, st.session_state.current_idx - 30)
    view_df = df.iloc[start_idx: st.session_state.current_idx + 1].copy()

    open_col = 'Open' if 'Open' in view_df.columns else 'Adj Close'
    high_col = 'High' if 'High' in view_df.columns else 'Adj Close'
    low_col = 'Low' if 'Low' in view_df.columns else 'Adj Close'
    close_col = 'Adj Close' if 'Adj Close' in view_df.columns else 'Close'

    date_labels = view_df['index'].dt.strftime('%m-%d')
    fig = go.Figure(data=[go.Candlestick(
        x=date_labels, open=view_df[open_col], high=view_df[high_col], low=view_df[low_col], close=view_df[close_col],
        increasing_line_color='red', decreasing_line_color='blue', name="캔들"
    )])

    # [수정 1] 차트 마지막 캔들에 현재가 표시
    fig.add_trace(go.Scatter(
        x=[date_labels.iloc[-1]], y=[current_price],
        mode='markers+text',
        marker=dict(color='orange', size=10),
        text=[f"{int(current_price):,}원"],
        textposition="middle right",
        name="현재가", showlegend=False
    ))

    # [수정 2] 매수/매도 타이밍 마커 표시
    buy_x, buy_y = [], []
    for b in st.session_state.trade_history['buys']:
        if b['idx'] in view_df.index:
            pos = view_df.index.get_loc(b['idx'])
            buy_x.append(date_labels.iloc[pos])
            buy_y.append(b['price'])

    sell_x, sell_y = [], []
    for s in st.session_state.trade_history['sells']:
        if s['idx'] in view_df.index:
            pos = view_df.index.get_loc(s['idx'])
            sell_x.append(date_labels.iloc[pos])
            sell_y.append(s['price'])

    if buy_x:
        fig.add_trace(go.Scatter(x=buy_x, y=buy_y, mode='markers', name="매수",
                                 marker=dict(symbol='triangle-up', color='red', size=14,
                                             line=dict(width=1, color='darkred'))))
    if sell_x:
        fig.add_trace(go.Scatter(x=sell_x, y=sell_y, mode='markers', name="매도",
                                 marker=dict(symbol='triangle-down', color='blue', size=14,
                                             line=dict(width=1, color='darkblue'))))

    fig.update_layout(
        title="🕯️ 최근 30일 주가 추이", xaxis_rangeslider_visible=False, xaxis=dict(type='category'),
        margin=dict(l=10, r=40, t=40, b=10), height=350, template="plotly_white"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 자산 현황
    stock_value = st.session_state.holdings_count * current_price
    profit_loss = stock_value - st.session_state.invested_amount
    profit_rate = (
                profit_loss / st.session_state.invested_amount * 100) if st.session_state.invested_amount > 0 else 0.0

    c1, c2, c3 = st.columns(3)
    c1.metric("현재 주가", f"{int(current_price):,}원")
    c2.metric("총자산 (보유 현금)", f"{int(st.session_state.total_cash):,}원")
    c3.metric("보유주식 전체가치", f"{int(stock_value):,}원", delta=f"{int(profit_loss):,}원 ({profit_rate:.2f}%)")

    st.write(f"💼 **주식 보유 수량**: {st.session_state.holdings_count}주")

    # 매수/매도 컨트롤
    trade_percent = st.slider("거래 비중 (%)", 10, 100, 50, 10)
    b_col, p_col, s_col = st.columns(3)

    if b_col.button("매 수 📈", use_container_width=True, type="primary"):
        budget = st.session_state.total_cash * (trade_percent / 100.0)
        cnt = int(budget // current_price)
        if cnt > 0:
            st.session_state.holdings_count += cnt
            st.session_state.total_cash -= cnt * current_price
            st.session_state.invested_amount += cnt * current_price
            st.session_state.trade_history['buys'].append({'idx': st.session_state.current_idx, 'price': current_price})
        next_turn()

    if p_col.button("관 망 ☕", use_container_width=True):
        next_turn()

    if s_col.button("매 도 📉", use_container_width=True):
        cnt = int(st.session_state.holdings_count * (trade_percent / 100.0))
        if cnt > 0:
            avg_price = st.session_state.invested_amount / st.session_state.holdings_count
            raw_cost = cnt * avg_price
            raw_revenue = cnt * current_price
            raw_profit = raw_revenue - raw_cost

            # 🎭 캐릭터 패시브 적용 (수익률 변경)
            final_profit = cur_char.modify_sell_profit(raw_profit)
            final_revenue = raw_cost + final_profit

            st.session_state.invested_amount -= raw_cost
            st.session_state.total_cash += final_revenue
            st.session_state.holdings_count -= cnt
            st.session_state.last_sell_profit = final_profit

            st.session_state.trade_history['sells'].append(
                {'idx': st.session_state.current_idx, 'price': current_price})

            if st.session_state.holdings_count == 0:
                st.session_state.invested_amount = 0.0
        next_turn()


def next_turn():
    save_snapshot()
    st.session_state.turns_left -= 1
    if st.session_state.turns_left <= 0 or st.session_state.current_idx >= len(df) - 1:
        auto_sell_and_end()
    else:
        st.session_state.current_idx += 1
        safe_rerun()


def auto_sell_and_end():
    current_price = float(df.iloc[st.session_state.current_idx]['Adj Close'])
    if st.session_state.holdings_count > 0:
        st.session_state.total_cash += st.session_state.holdings_count * current_price
        st.session_state.holdings_count = 0
        st.session_state.invested_amount = 0.0

    is_win = st.session_state.total_cash > st.session_state.initial_cash
    st.session_state.game_history.append({'wins': is_win})
    st.session_state.in_game = False
    safe_rerun()


if st.session_state.in_game:
    show_game_screen()
else:
    show_start_screen()
