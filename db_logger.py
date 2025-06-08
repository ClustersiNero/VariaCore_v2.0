### db_logger.py

"""
统一日志记录模块（字段标准化版 + 全语义精确命名）：
- 所有字段命名需表达唯一含义与归属职责
"""

# ✅ 全局日志容器（运行时内存存储）
round_log = []          # 每局结构&开奖信息（平台维度）
player_log = []         # 每局玩家结算明细（玩家真实）
rtp_std_log = []        # 每局结构RTP标准差分析（结构模拟）
attitude_std_log = []   # 每局结构态势标准差分析（结构模拟）
confidence_log = []  # ✅ 每局置信区间计算的详细日志

# ✅ 精算日志：置信区间计算明细
def log_confidence_bounds_details(
    round_id: int,
    base_std: float,
    confidence_level: float,
    sample_size: float,
    std_bounds: tuple,
    player_contributions: list  # 仅包含 player_id, equivalent_rounds, weighted_contribution
):
    # ✅ 从已有 player_log 中提取 recent_bet_sum 和 current_bet，确保数据一致性
    player_data_map = {
        (x["round_id"], x["player_id"]): x for x in player_log
    }

    enriched_contributions = []
    for contrib in player_contributions:
        pid = contrib["player_id"]
        pdata = player_data_map.get((round_id, pid), {})
        enriched_contributions.append({
            "player_id": pid,
            "equivalent_rounds": contrib.get("equivalent_rounds"),
            "weighted_contribution": contrib.get("weighted_contribution")
        })

    confidence_log.append({
        "round_id": round_id,
        "base_std_input": base_std,
        "confidence_level_input": confidence_level,
        "sample_size_equivalent": sample_size,
        "std_bounds_low": std_bounds[0],
        "std_bounds_high": std_bounds[1],
        "player_contributions": enriched_contributions
    })


# ✅ 主日志：平台汇总 & 玩家明细（仅由 controller 写入）
def log_round_summary(
    round_id: int,
    player_bets: dict,
    area_totals: dict,
    winning_areas: list,
    total_bet: float,
    total_payout: float,
    structures: list = None,
    pool_value: float = None,
    target_rtp: float = None,
    std_bounds: tuple = None
):
    EXCLUDE_KEYS = {"simulated_players"}
    clean_structures = []
    for s in structures or []:
        s_clean = s.copy()
        for k in EXCLUDE_KEYS:
            s_clean.pop(k, None)
        clean_structures.append(s_clean)

    entry = {
        "round_id": round_id,
        "all_player_bets_map_platform": player_bets,
        "area_total_bets_platform": area_totals,
        "winning_areas_final_result": winning_areas,
        "total_bet_amount_platform": total_bet,
        "total_payout_amount_platform": total_payout,
        "net_profit_platform": total_bet - total_payout,
        "structure_results_simulation_output": clean_structures,
        "pool_value_platform": pool_value,
        "target_rtp_platform_dynamic": target_rtp,
        "rtp_confidence_bounds_active": std_bounds
    }
    round_log.append(entry)


def log_player_detail(
    round_id: int,
    player_id: str,
    area_bets: dict,
    total_bet: float,
    payout: float,
    recharge: float,
    attitude: float,
    memory_profit: float,
    memory_avg_bet: float,
    rtp: float,
    current_rtp: float,
    stat_players: dict  # ✅ 新增参数
):
    recent_bets_list = list(stat_players[player_id].recent_bets)
    entry = {
        "round_id": round_id,
        "player_id": player_id,
        "bet_area_distribution_player_real": area_bets,
        "total_bet_amount_player_real": total_bet,
        "total_payout_amount_player_real": payout,
        "net_profit_player_real": payout - total_bet,
        "recharge_amount_player_initial": recharge,
        "attitude_value_player_real": attitude,
        "memory_profit_player_real": memory_profit,
        "memory_avg_bet_player_real": memory_avg_bet,
        "rtp_historical_player_real": rtp,
        "rtp_current_round_player_real": current_rtp,
        "recent_bet_sum": sum(recent_bets_list),
        "past_bet_sum": sum(recent_bets_list[:-1]) if len(recent_bets_list) > 1 else 0
    }
    player_log.append(entry)


# ✅ 精算日志：结构RTP分析

def log_rtp_std_details(
    round_id: int,
    structure_id: int,
    expected_rtp: float,
    rtp_std: float,
    total_weight: float,
    total_var: float,
    player_details: list,
    game_areas: list  # ✅ 新增
):
    rtp_std_log.append({
        "round_id": round_id,
        "structure_id": structure_id,
        "game_areas": game_areas,  # ✅ 修复字段缺失
        "expected_rtp_structure_simulation": expected_rtp,
        "rtp_std_structure_after_simulation": rtp_std,
        "rtp_total_weight_structure_simulated": total_weight,
        "rtp_total_variance_structure_simulated": total_var,
        "rtp_effects_per_player_simulated": [
            {
                **p,
                "total_bet_amount_player_simulated": p["total_bet_amount_player_simulated"]
            } for p in player_details
        ]
    })

def log_attitude_std_details(
    round_id: int,
    structure_id: int,
    attitude_std: float,
    player_details: list,
    game_areas: list  # ✅ 新增
):
    attitude_std_log.append({
        "round_id": round_id,
        "structure_id": structure_id,
        "game_areas": game_areas,  # ✅ 修复字段缺失
        "attitude_std_structure_after_simulation": attitude_std,
        "attitude_effects_per_player_simulated": [
            {
                **p,
                "total_bet_amount_player_simulated": p["total_bet_amount_player_simulated"]
            } for p in player_details
        ]
    })

# ---------------------
# ✅ [日志字段校验区：用于导出前清理]
# ---------------------
REQUIRED_CONFIDENCE_LOG_FIELDS = [
    "round_id", "base_std_input", "confidence_level_input",
    "sample_size_equivalent", "std_bounds_low", "std_bounds_high", "player_contributions"
]

REQUIRED_PLAYER_LOG_FIELDS = [
    "round_id", "player_id", "bet_area_distribution_player_real", "total_bet_amount_player_real", "total_payout_amount_player_real", "net_profit_player_real",
    "memory_profit_player_real", "attitude_value_player_real", "rtp_historical_player_real", "recharge_amount_player_initial", "rtp_current_round_player_real", "memory_avg_bet_player_real"
]

REQUIRED_ROUND_LOG_FIELDS = [
    "round_id", "all_player_bets_map_platform", "area_total_bets_platform", "winning_areas_final_result",
    "total_bet_amount_platform", "total_payout_amount_platform", "net_profit_platform", "structure_results_simulation_output",
    "pool_value_platform", "target_rtp_platform_dynamic", "rtp_confidence_bounds_active"
]

REQUIRED_RTP_STD_LOG_FIELDS = [
    "round_id", "structure_id", "game_areas", "expected_rtp_structure_simulation",
    "rtp_std_structure_after_simulation", "rtp_total_weight_structure_simulated", "rtp_total_variance_structure_simulated", "rtp_effects_per_player_simulated"
]

REQUIRED_ATTITUDE_STD_LOG_FIELDS = [
    "round_id", "structure_id", "game_areas", "attitude_std_structure_after_simulation", "attitude_effects_per_player_simulated"
]

def sanitize_logs():
    for entry in confidence_log:
        for k in list(entry):
            if k not in REQUIRED_CONFIDENCE_LOG_FIELDS:
                del entry[k]
                
    for entry in player_log:
        for k in list(entry):
            if k not in REQUIRED_PLAYER_LOG_FIELDS:
                del entry[k]

    for entry in round_log:
        for k in list(entry):
            if k not in REQUIRED_ROUND_LOG_FIELDS:
                del entry[k]

    for entry in rtp_std_log:
        for k in list(entry):
            if k not in REQUIRED_RTP_STD_LOG_FIELDS:
                del entry[k]

    for entry in attitude_std_log:
        for k in list(entry):
            if k not in REQUIRED_ATTITUDE_STD_LOG_FIELDS:
                del entry[k]
