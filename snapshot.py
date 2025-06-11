import streamlit as st
import pandas as pd
import altair as alt
from data_loader import load_logs_by_round

# ✅ 页面基本配置
st.set_page_config(layout="wide", page_title="🎯 控奖结构快照仪表盘")

# ✅ 加载本地日志数据（每次刷新从 JSON 读取）
round_log, player_log, round_ids = load_logs_by_round()
if not round_log or not player_log:
    st.stop()

# ✅ 初始化 session_state：记录当前轮次索引（用于按钮切换）
if "selected_round_idx" not in st.session_state:
    st.session_state.selected_round_idx = len(round_ids) - 1  # 默认显示最后一局

# ✅ 侧边栏：轮次导航按钮 + 下拉栏组合区域
st.sidebar.title("📂 快照轮次选择")

col1, col2, col3 = st.sidebar.columns([1, 2, 1])
with col1:
    if st.button("⬅️", key="prev_round_btn"):
        st.session_state.selected_round_idx = max(0, st.session_state.selected_round_idx - 1)
with col3:
    if st.button("➡️", key="next_round_btn"):
        st.session_state.selected_round_idx = min(len(round_ids) - 1, st.session_state.selected_round_idx + 1)
with col2:
    st.markdown(
        f"<div style='text-align:center; font-weight:bold; font-size:18px;'>第 {round_ids[st.session_state.selected_round_idx]} 局</div>",
        unsafe_allow_html=True
    )

selected_round = st.sidebar.selectbox(
    "🔍 直接跳转至指定轮次",
    round_ids,
    index=st.session_state.selected_round_idx,
    key="select_round_dropdown"
)

if selected_round != round_ids[st.session_state.selected_round_idx]:
    st.session_state.selected_round_idx = round_ids.index(selected_round)
selected_round = round_ids[st.session_state.selected_round_idx]

# ✅ 获取当前轮数据
round_data = round_log.get(selected_round)
player_data = player_log.get(selected_round, [])
if not round_data:
    st.error(f"未找到轮次 {selected_round} 的结构信息")
    st.stop()

# ✅ 侧边栏：平台与本轮信息总览
sidebar_info = round_data.get("_sidebar_info", {})
st.sidebar.header("📋 本轮概览")
st.sidebar.text(f"游戏名：{sidebar_info.get('游戏名', '')}")
st.sidebar.text(f"轮次编号：{sidebar_info.get('轮次', '')}")
st.sidebar.text(f"参与人数：{sidebar_info.get('参与人数', '')}")
st.sidebar.text(f"当前水池值：{sidebar_info.get('当前水池值', 0):,.2f}")
st.sidebar.text(f"目标 RTP：{sidebar_info.get('目标RTP', 0):.2%}")
st.sidebar.text(f"置信度：{sidebar_info.get('置信度', 0):.2%}")
low, high = sidebar_info.get("置信区间", (0, 0))
st.sidebar.text(f"置信区间：{low:.4f} ~ {high:.4f}")

st.sidebar.markdown("---")
st.sidebar.subheader("📊 平台指标")
total_bet = round_data.get("total_bet_amount_platform", 0)
total_payout = round_data.get("total_payout_amount_platform", 0)
net = total_bet - total_payout
st.sidebar.metric("总投注", f"{int(total_bet):,}")
st.sidebar.metric("总返奖", f"{int(total_payout):,}")
st.sidebar.metric("平台盈亏", f"{int(net):,}", delta_color="inverse")

# ✅ 主区：结构模拟结果 + 区域投注柱状图（并列两栏）
st.subheader("🎯 控奖结构模拟结果与投注分布")
col_left, col_right = st.columns([2, 1])

with col_left:
    def format_large_numbers(df):
        money_cols = ["相关投注", "预计赔付", "系统盈亏"]
        for col in money_cols:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{round(x):,}") if col == "记忆均注" else df[col].apply(lambda x: f"{x:,}")
        return df

    structure_df = round_data.get("_structure_df")
    if structure_df is not None:
        formatted_df = format_large_numbers(structure_df.drop(columns=["轮次"]))
        st.dataframe(formatted_df, use_container_width=True, hide_index=True)

with col_right:
    area_bets = round_data.get("area_total_bets_platform", {})
    filtered = [(str(i), area_bets.get(i, 0)) for i in range(1, 9) if area_bets.get(i, 0) > 0]

    if filtered:
        df_area = pd.DataFrame(filtered, columns=["区域", "投注额"])

        chart = alt.Chart(df_area).mark_bar().encode(
            x=alt.X("区域:N", title="区域编号"),
            y=alt.Y("投注额:Q", title="投注总额"),
            tooltip=["区域", "投注额"]
        ).properties(
            title="区域投注柱状图",
            width=300,
            height=250
        )

        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("暂无有效投注数据，未生成柱状图")

# ✅ 主区：玩家明细表格
player_df = round_data.get("_player_df")
if player_df is not None:
    st.subheader("👤 玩家明细概览")

    def format_player_df(df):
        money_cols = ["总投注", "返奖", "净盈亏", "充值", "记忆均注"]
        percent_cols = ["历史RTP", "当局RTP", "记忆盈亏", "态势"]

        for col in money_cols:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x:,}")

        for col in percent_cols:
            if col in df.columns:
                df[col] = df[col].apply(lambda x: f"{x * 100:.1f}%")

        return df

    formatted_player_df = format_player_df(player_df.copy())
    st.dataframe(formatted_player_df, use_container_width=True, hide_index=True)
