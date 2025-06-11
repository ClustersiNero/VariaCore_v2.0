import os
import pandas as pd
import math
from collections import deque, defaultdict
from db_logger import round_log, player_log, rtp_std_log, attitude_std_log
from config import EXCEL_DIR, DEBUG_DIR, RECENT_RTP_WINDOW



# 平台结构模拟明细
def build_structure_results_df_from_log():
    if not round_log:
        return pd.DataFrame([])

    rows = []
    rtp_map = {(e["round_id"], e["structure_id"]): e for e in rtp_std_log}
    attitude_map = {(e["round_id"], e["structure_id"]): e for e in attitude_std_log}

    for entry in round_log:
        round_id = entry.get("round_id")
        structures = entry.get("structure_results_simulation_output", [])
        final_areas = entry.get("winning_areas_final_result", [])

        # ✅ 每轮添加分隔行：标注中奖结构
        rows.append({"轮次": f"本次中奖结构: {final_areas}"})

        for sid, s in enumerate(structures):
            rid_sid = (round_id, sid)
            rtp_std = round(rtp_map.get(rid_sid, {}).get("rtp_std_structure_after_simulation", 0), 6)
            attitude_std = round(attitude_map.get(rid_sid, {}).get("attitude_std_structure_after_simulation", 0), 6)

            rows.append({
                "轮次": round_id,
                "结构": s.get("game_areas"),
                "RTP_STD": rtp_std,
                "态势STD": attitude_std,
                "相关投注": int(s.get("related_bet", 0)),
                "预计赔付": int(s.get("expected_award", 0)),
                "系统盈亏": int(s.get("profit_estimate", 0)),
                "是否选中": int(bool(s.get("is_final_outcome", False))),
                "第一轮": int(s.get("entered_phase1", False)),
                "第二轮": int(s.get("entered_phase2", False)),
                "第三轮": int(s.get("entered_phase3", False)),
                "本轮中奖结构": str(final_areas)
            })

    return pd.DataFrame(rows)[:25000][[
        "轮次", "结构", "RTP_STD", "态势STD", "相关投注", "预计赔付", "系统盈亏",
        "是否选中", "第一轮", "第二轮", "第三轮", "本轮中奖结构"
    ]]
    
# 玩家下注记录明细
def build_player_summary_df_from_log():
    if not player_log:
        return pd.DataFrame([])

    round_final_map = {
        entry["round_id"]: entry.get("winning_areas_final_result", [])
        for entry in round_log
    }

    rows = []
    current_round = None

    for entry in player_log:
        round_id = entry["round_id"]

        if current_round != round_id:
            final_areas = round_final_map.get(round_id, [])
            rows.append({"轮次": f"本次中奖结构: {final_areas}"})
            current_round = round_id

        base_data = {
            "轮次": round_id,
            "玩家ID": entry["player_id"],
            "总投注": entry["total_bet_amount_player_real"],
            "返奖": entry["total_payout_amount_player_real"],
            "净盈亏": entry["net_profit_player_real"],
            "充值": entry["recharge_amount_player_initial"],
            "态势": round(entry["attitude_value_player_real"], 6),
            "记忆盈亏": round(entry["memory_profit_player_real"], 2),
            "记忆均注": round(entry["memory_avg_bet_player_real"], 2),
            "历史RTP": round(entry["rtp_historical_player_real"], 6),
            "当局RTP": round(entry["rtp_current_round_player_real"], 6),
        }

        area_bets = entry.get("bet_area_distribution_player_real", {})
        for area in range(1, 9):
            base_data[f"区域{area}"] = area_bets.get(area, 0)

        rows.append(base_data)

    columns_order = [
        "轮次", "玩家ID", "总投注", "返奖", "净盈亏", "充值",
        "态势", "记忆盈亏", "记忆均注", "历史RTP", "当局RTP"
    ] + [f"区域{i}" for i in range(1, 9)] 

    return pd.DataFrame(rows)[columns_order]

# 平台指标走势：水池、期望RTP
def build_platform_context_df_from_log():
    if not round_log:
        return pd.DataFrame([])

    rows = []
    for entry in round_log:
        rows.append({
            "轮次": entry["round_id"],
            "总投注": entry.get("total_bet_amount_platform", 0),
            "总返奖": entry.get("total_payout_amount_platform", 0),
            "平台盈利": entry.get("net_profit_platform", 0),
            "目标RTP": round(entry.get("target_rtp_platform_dynamic", 0), 4),
            "当前奖池": round(entry.get("pool_value_platform", 0), 2),
            "置信区间下限": round(entry.get("rtp_confidence_bounds_active", (0, 0))[0], 6),
            "置信区间上限": round(entry.get("rtp_confidence_bounds_active", (0, 0))[1], 6),
            "本轮中奖结构": str(entry.get("winning_areas_final_result", []))
        })

    return pd.DataFrame(rows)[[
        "轮次", "总投注", "总返奖", "平台盈利", "目标RTP",
        "当前奖池", "置信区间下限", "置信区间上限", "本轮中奖结构"
    ]]

# 玩家指标走势：RTP、态势、净输赢、累计净输赢
def build_player_metrics_log_from_log():
    data_by_round = {}
    player_profit_window = {}  # ⬅️ 维护每位玩家的窗口内净盈亏（最多 N 局）

    for entry in player_log:
        round_id = entry["round_id"]
        pid = entry["player_id"]
        rtp = round(entry["rtp_historical_player_real"], 6)
        attitude = round(entry["attitude_value_player_real"], 6)
        net_profit = entry["net_profit_player_real"]

        # ✅ 滑动窗口机制：默认窗口长度与 RTP 保持一致（config 中定义）
        profit_window = player_profit_window.setdefault(pid, deque(maxlen=RECENT_RTP_WINDOW))
        profit_window.append(net_profit)
        cumulative_profit = sum(profit_window)

        if round_id not in data_by_round:
            data_by_round[round_id] = {}
        data_by_round[round_id][pid] = {
            "RTP": rtp,
            "态势": attitude,
            "净盈亏": net_profit,
            "累计盈亏窗口": cumulative_profit  # ✅ 新字段
        }

    rows = []
    for round_id, players in sorted(data_by_round.items()):
        row = {"轮次": round_id}
        for pid, metrics in players.items():
            row[f"{pid}_RTP"] = metrics["RTP"]
            row[f"{pid}_态势"] = metrics["态势"]
            row[f"{pid}_净盈亏"] = metrics["净盈亏"]
            row[f"{pid}_累计盈亏窗口"] = metrics["累计盈亏窗口"]  # ✅ 新字段输出
        rows.append(row)

    return pd.DataFrame(rows)
        
# RTP_STD明细、用于debug
def build_rtp_std_debug_df():
    rows = []
    last_round_id = None
    for entry in rtp_std_log:
        rid = entry.get("round_id")
        sid = entry.get("structure_id")
        areas = entry.get("game_areas")
        rtp_std = entry.get("rtp_std_structure_after_simulation")

        if last_round_id is not None and rid != last_round_id:
            rows.append({"轮次": last_round_id, "结构区域": "----------", "玩家ID": f"✅ 第 {last_round_id} 局结束"})
        last_round_id = rid

        for p in entry.get("rtp_effects_per_player_simulated", []):
            rows.append({
                "轮次": rid,
                "结构ID": sid,
                "结构区域": str(areas),
                "玩家ID": p["player_id"],
                "投注额": p["total_bet_amount_player_simulated"],
                "累计投注": p.get("recent_bets_sum", 0),
                "累计返奖": p.get("recent_payouts_sum", 0),
                "RTP": round(p["rtp_player_simulated"], 6),
                "偏差": round(p["rtp_diff_player_simulated"], 6),
                "偏差平方": round(p["rtp_diff_sq_player_simulated"], 6),
                "方差贡献": round(p["rtp_var_contrib_player_simulated"], 1),
                "权重": p["total_bet_amount_player_simulated"],
                "结构STD": round(rtp_std, 6),
            })
    if last_round_id is not None:
        rows.append({"轮次": last_round_id, "结构区域": "----------", "玩家ID": f"✅ 第 {last_round_id} 局结束"})
    return pd.DataFrame(rows)

# 态势_STD明细、用于debug
def build_attitude_std_debug_df():
    rows = []
    last_round_id = None
    for entry in attitude_std_log:
        rid = entry.get("round_id")
        sid = entry.get("structure_id")
        areas = entry.get("game_areas")
        std = entry.get("attitude_std_structure_after_simulation")

        if last_round_id is not None and rid != last_round_id:
            rows.append({"轮次": last_round_id, "结构区域": "----------", "玩家ID": f"✅ 第 {last_round_id} 局结束"})
        last_round_id = rid

        for p in entry.get("attitude_effects_per_player_simulated", []):
            history_bets = p.get("recent_bets", [])
            round_bet = history_bets[-1] if history_bets else 0

            rows.append({
                "轮次": rid,
                "结构ID": sid,
                "结构区域": str(areas),
                "玩家ID": p.get("player_id"),
                "投注": round_bet,
                "返奖": p.get("payout_amount_player_simulated", 0),
                "平均投注": p.get("memory_avg_bet_player_simulated", 0),
                "记忆值": p.get("memory_profit_player_simulated", 0),
                "影响值": p.get("attitude_value_player_simulated", 0),
                "偏差": p.get("attitude_diff_player_simulated", 0),
                "偏差平方": p.get("attitude_diff_sq_player_simulated", 0),
                "方差贡献": p.get("attitude_var_contrib_player_simulated", 0),
                "权重": p.get("recharge_weight_player_simulated", 0),
                "态势STD": round(std, 6)
            })
    if last_round_id is not None:
        rows.append({"轮次": last_round_id, "结构区域": "----------", "玩家ID": f"✅ 第 {last_round_id} 局结束"})
    return pd.DataFrame(rows)[:25000]


# 玩家信息综合汇总
def build_player_lifetime_summary_df():
    if not player_log:
        return pd.DataFrame([])

    player_stats = {}
    player_rounds = defaultdict(list)  # ⬅️ 每个玩家的局序列（含原始条目）

    for entry in player_log:
        pid = entry["player_id"]
        player_rounds[pid].append(entry)

    for pid, rounds in player_rounds.items():
        stat = {
            "累计投注": 0.0,
            "累计返奖": 0.0,
            "投注次数": 0,
            "赢钱次数": 0,
            "最高RTP": float("-inf"),
            "最低RTP": float("inf"),
            "单局最高RTP": float("-inf"),
            "最高赢钱": float("-inf"),
            "最低亏钱": float("inf"),
            "单局最高净盈利": float("-inf"),
            "单局最高净亏损": float("inf"),
            "最高态势": float("-inf"),
            "最低态势": float("inf"),
            "_累计盈亏": 0.0
        }

        for i, entry in enumerate(rounds):
            bet = entry["total_bet_amount_player_real"]
            payout = entry["total_payout_amount_player_real"]
            net = payout - bet
            rtp = payout / bet if bet > 0 else 0.0  # ⬅️ 单局 RTP
            attitude = entry["attitude_value_player_real"]

            # ✅ 累计值
            stat["累计投注"] += bet
            stat["累计返奖"] += payout
            stat["_累计盈亏"] += net

            stat["投注次数"] += 1 if bet > 0 else 0
            stat["赢钱次数"] += 1 if payout > bet else 0

            # ✅ 单局指标
            stat["单局最高RTP"] = max(stat["单局最高RTP"], rtp)
            stat["单局最高净盈利"] = max(stat["单局最高净盈利"], net)
            stat["单局最高净亏损"] = min(stat["单局最高净亏损"], net)
            stat["最高态势"] = max(stat["最高态势"], attitude)
            stat["最低态势"] = min(stat["最低态势"], attitude)

            # ✅ 累计盈亏过程中的峰值（不限制前几局）
            stat["最高赢钱"] = max(stat["最高赢钱"], stat["_累计盈亏"])
            stat["最低亏钱"] = min(stat["最低亏钱"], stat["_累计盈亏"])

            # ✅ RTP极值（从第11局开始）
            if i >= 10:
                stat["最高RTP"] = max(stat["最高RTP"], entry["rtp_historical_player_real"])
                stat["最低RTP"] = min(stat["最低RTP"], entry["rtp_historical_player_real"])

        # ✅ 补充输出字段
        rtp_total = stat["累计返奖"] / stat["累计投注"] if stat["累计投注"] > 0 else 0.0

        player_stats[pid] = {
            "玩家ID": pid,
            **stat,
            "净输赢": stat["累计返奖"] - stat["累计投注"],
            "RTP": rtp_total
        }

    # ✅ 输出字段顺序
    return pd.DataFrame(player_stats.values())[[
        "玩家ID", "累计投注", "累计返奖", "净输赢", "RTP",
        "投注次数", "赢钱次数", "最高RTP", "最低RTP",
        "最高赢钱", "最低亏钱", "单局最高净盈利", "单局最高RTP", "单局最高净亏损",
        "最高态势", "最低态势"
    ]]


# ✅ 写入（首次清空）
def export_all_logs():
    os.makedirs(EXCEL_DIR, exist_ok=True)

    if not round_log:
        print("⚠️ 无有效对局日志，跳过导出")
        return

    latest_round = round_log[-1]["round_id"]

    df1 = build_player_summary_df_from_log()
    df2 = build_structure_results_df_from_log()
    df3 = build_platform_context_df_from_log()
    df4 = build_player_metrics_log_from_log()
    df5 = build_player_lifetime_summary_df()

    df1.to_excel(os.path.join(EXCEL_DIR, "player_summary_log.xlsx"), index=False, engine='xlsxwriter')
    df2.to_excel(os.path.join(EXCEL_DIR, "structure_result_log.xlsx"), index=False, engine='xlsxwriter')
    df3.to_excel(os.path.join(EXCEL_DIR, "platform_context_log.xlsx"), index=False, engine='xlsxwriter')
    df4.to_excel(os.path.join(EXCEL_DIR, "player_metrics_log.xlsx"), index=False, engine='xlsxwriter')
    df5.to_excel(os.path.join(EXCEL_DIR, "player_lifetime_summary.xlsx"), index=False, engine='xlsxwriter')


# ✅ 写入 Excel 文件：用于所有精算级 debug 日志导出
def export_debug_inspection_logs():
    os.makedirs(DEBUG_DIR, exist_ok=True)
    df1 = build_rtp_std_debug_df()
    df2 = build_attitude_std_debug_df()
    path1 = os.path.join(DEBUG_DIR, "rtp_std_log.xlsx")
    path2 = os.path.join(DEBUG_DIR, "attitude_std_log.xlsx")
    df1.to_excel(path1, index=False, engine="xlsxwriter")
    df2.to_excel(path2, index=False, engine="xlsxwriter")