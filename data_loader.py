import os
import json
import pandas as pd
from config import JSON_DIR
from metrics_engine import aggregate_area_totals

# ✅ 仪表盘专用：按轮次构建快照数据
def load_logs_by_round():
    # === 1. 读取 JSON 文件 ===
    round_json = os.path.join(JSON_DIR, "round_log.json")
    player_json = os.path.join(JSON_DIR, "player_log.json")
    rtp_json = os.path.join(JSON_DIR, "rtp_std_log.json")
    attitude_json = os.path.join(JSON_DIR, "attitude_std_log.json")

    round_log = []
    player_log = []
    rtp_std_log = []
    attitude_std_log = []

    if os.path.exists(round_json):
        with open(round_json, "r", encoding="utf-8") as f:
            round_log = json.load(f)

    if os.path.exists(player_json):
        with open(player_json, "r", encoding="utf-8") as f:
            player_log = json.load(f)

    if os.path.exists(rtp_json):
        with open(rtp_json, "r", encoding="utf-8") as f:
            rtp_std_log = json.load(f)

    if os.path.exists(attitude_json):
        with open(attitude_json, "r", encoding="utf-8") as f:
            attitude_std_log = json.load(f)

    # === 2. 构造结构模拟结果 DataFrame ===
    structure_df_rows = []
    rtp_map = {(e["round_id"], e["structure_id"]): e for e in rtp_std_log}
    att_map = {(e["round_id"], e["structure_id"]): e for e in attitude_std_log}

    for entry in round_log:
        rid = entry["round_id"]
        final_areas = entry.get("winning_areas_final_result", [])
        structures = entry.get("structure_results_simulation_output", [])

        for sid, s in enumerate(structures):
            rtp_std = round(rtp_map.get((rid, sid), {}).get("rtp_std_structure_after_simulation", 0), 6)
            att_std = round(att_map.get((rid, sid), {}).get("attitude_std_structure_after_simulation", 0), 6)

            structure_df_rows.append({
                "轮次": str(rid),
                "结构": s.get("game_areas") or s.get("areas"),
                "RTP_STD": rtp_std,
                "态势STD": att_std,
                "相关投注": int(s.get("related_bet", 0)),
                "预计赔付": int(s.get("expected_award", 0)),
                "系统盈亏": int(s.get("profit_estimate", 0)),
                "第一轮": int(s.get("entered_phase1", False)),
                "第二轮": int(s.get("entered_phase2", False)),
                "第三轮": int(s.get("entered_phase3", False)),
            })

    df_structure = pd.DataFrame(structure_df_rows)[:25000][[
        "轮次", "结构", "RTP_STD", "态势STD", "相关投注", "预计赔付", "系统盈亏",
        "第一轮", "第二轮", "第三轮",
    ]]

    # === 3. 构造玩家明细 DataFrame ===
    player_df_rows = []
    round_final_map = {e["round_id"]: e.get("winning_areas_final_result", []) for e in round_log}

    for entry in player_log:
        rid = entry["round_id"]
        pid = entry["player_id"]
        bet_map = entry.get("bet_area_distribution_player_real", {})

        row = {
            "轮次": str(rid),
            "玩家ID": pid,
            "总投注": entry.get("total_bet_amount_player_real", 0),
            "返奖": entry.get("total_payout_amount_player_real", 0),
            "净盈亏": entry.get("net_profit_player_real", 0),
            "充值": entry.get("recharge_amount_player_initial", 0),
            "态势": round(entry.get("attitude_value_player_real", 0), 6),
            "记忆盈亏": round(entry.get("memory_profit_player_real", 0), 2),
            "记忆均注": round(entry.get("memory_avg_bet_player_real", 0)),
            "历史RTP": round(entry.get("rtp_historical_player_real", 0), 6),
            "当局RTP": round(entry.get("rtp_current_round_player_real", 0), 6),
        }
        for i in range(1, 9):
            row[f"区域{i}"] = bet_map.get(str(i), 0)

        player_df_rows.append(row)

    col_order = [
        "轮次", "玩家ID", "总投注", "返奖", "净盈亏", "充值", "态势",
        "记忆盈亏", "记忆均注", "历史RTP", "当局RTP"
    ] + [f"区域{i}" for i in range(1, 9)]
    df_player = pd.DataFrame(player_df_rows)[col_order]

    # === 4. 构造返回结构 ===
    round_dict = {}
    for r in round_log:
        rid = r["round_id"]
        r["_structure_df"] = df_structure[df_structure["轮次"] == str(rid)]
        r["_sidebar_info"] = {
            "游戏名": "PROJECT ONE",
            "轮次": rid,
            "参与人数": len(r.get("all_player_bets_map_platform", {})),
            "当前水池值": r.get("pool_value_platform", 0),
            "目标RTP": r.get("target_rtp_platform_dynamic", 0),
            "置信度": 0.95,
            "置信区间": r.get("rtp_confidence_bounds_active", (0, 0))
        }

        # ✅ 新增：将区域总投注额显式写入 round_data，用于柱状图展示
        area_totals = {i: 0 for i in range(1, 9)}
        for struct in r.get("structure_results_simulation_output", [])[:8]:
            areas = struct.get("game_areas", [])
            bet = struct.get("related_bet", 0)
            for a in areas:
                if a in area_totals:
                    area_totals[a] += bet
        r["area_total_bets_platform"] = area_totals
        round_dict[rid] = r

    player_dict = {}
    for p in player_log:
        rid = p["round_id"]
        if rid not in player_dict:
            player_dict[rid] = []
        player_dict[rid].append(p)

    for rid, df in df_player.groupby("轮次"):
        # ✅ 填充区域投注列（区域1~8）
        for i in range(1, 9):
            col_name = f"区域{i}"
            df[col_name] = df.apply(
                lambda row: row.get(f"区域{i}", 0) if f"区域{i}" in row else 0,
                axis=1
            )
        round_dict[int(rid)]["_player_df"] = df.drop(columns=["轮次"])
        
    return round_dict, player_dict, sorted(round_dict.keys())
