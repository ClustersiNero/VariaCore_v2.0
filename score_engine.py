# scoring_engine.py

"""
结构评分模块：字段精确命名版
- 接收结构及其命中区域信息
- 结合玩家状态与上下文，对结构进行多维打分（如：玩家亏损、追击中、首登场等）
- 输出用于排序与标准差评估的分析值
"""

# ✅ 当前版本将统一日志字段为已更新标准名
# ✅ 将模拟字段名如 total_bet → total_bet_amount_player_simulated
# ✅ 将字段名顺序统一：主体字段在前，修饰信息后置

from typing import Dict, List
from config import PAYOUT_RATES, WINNING_STRUCTURES, STD_THRESHOLD, MINIMUM_BET_THRESHOLD, MAX_STRUCTURE_SIM_THREADS, ATTITUDE_TARGET
from player_profiles import PlayerStats
from metrics_engine import compute_rtp, compute_total_weight, compute_weighted_variance, compute_weighted_std, compute_target_diff, compute_attitude, compute_dynamic_std_confidence_interval, compute_memory_avg_bet, compute_memory_profit, compute_equivalent_sample_size
from db_logger import log_rtp_std_details, log_attitude_std_details
import math
from concurrent.futures import ThreadPoolExecutor


# 计算各个结构在模拟下的基础利润指标：投注、赔付、净盈亏
def calculate_structure_estimates(current_bets: Dict[str, Dict[int, float]], game_areas: List[int]) -> Dict[str, float]:
    related_bet = 0.0
    expected_award = 0.0
    total_bet = 0.0
    for bets in current_bets.values():
        total = sum(bets.values())
        total_bet += total
        for a, v in bets.items():
            if a in game_areas:
                related_bet += v
                expected_award += v * PAYOUT_RATES[a]
    profit_estimate = total_bet - expected_award
    return {
        "related_bet": related_bet,
        "expected_award": expected_award,
        "profit_estimate": profit_estimate
    }


# 对单个结构、计算模拟下的RTP_STD、同时输出日志供细致检查
def compute_rtp_std_for_structure(
    structure: Dict,
    current_players: Dict[str, PlayerStats],
    current_bets: Dict[str, Dict[int, float]],
    expected_rtp: float,
    round_id: int = -1,
    structure_id: int = -1
):
    game_areas = structure.get("areas") or structure.get("game_areas")
    base_weight = structure["base_weight"]

    simulated_players = {
        pid: stats.copy() for pid, stats in current_players.items()
    }

    player_rtp_snapshots = {}
    for player_id, bets in current_bets.items():
        total_bet = sum(bets.values())
        payout = sum(
            amount * PAYOUT_RATES[area]
            for area, amount in bets.items()
            if area in game_areas
        )
        simulated_players[player_id].update(total_bet, payout)
        rtp = compute_rtp(simulated_players[player_id])
        diff = compute_target_diff(rtp, expected_rtp)
        player_rtp_snapshots[player_id] = {
            "player_id": player_id,
            "total_bet_amount_player_simulated": total_bet,
            "rtp_player_simulated": rtp,
            "rtp_diff_player_simulated": diff,
            "rtp_diff_sq_player_simulated": diff ** 2,
            "rtp_var_contrib_player_simulated": total_bet * (diff ** 2),
            "recent_bets_sum": sum(simulated_players[player_id].recent_bets),
            "recent_payouts_sum": sum(simulated_players[player_id].recent_payouts)
        }

    filtered_players = {
        pid: simulated_players[pid]
        for pid, bets in current_bets.items()
        if sum(bets.values()) >= MINIMUM_BET_THRESHOLD
    }

    total_rtp_weight = compute_total_weight(filtered_players.values())
    if total_rtp_weight <= 0:
        std_value = 0.0
    else:
        weighted_var = sum(
            compute_weighted_variance(compute_rtp(p) - expected_rtp, p.total_bet)
            for p in filtered_players.values()
        )
        std_value = math.sqrt(weighted_var / total_rtp_weight)

    estimate = calculate_structure_estimates(current_bets, game_areas)
    structure.update({
        "game_areas": game_areas,
        "rtp_std": std_value,
        "base_weight": base_weight,
        **estimate
    })

    if round_id > 0 and structure_id >= 0:
        log_rtp_std_details(
            round_id=round_id,
            structure_id=structure_id,
            expected_rtp=expected_rtp,
            rtp_std=std_value,
            total_weight=total_rtp_weight,
            total_var=weighted_var if total_rtp_weight > 0 else 0.0,
            player_details=list(player_rtp_snapshots.values()),
            game_areas=game_areas  # ✅ 补充
        )

    structure["simulated_players"] = simulated_players


# 对单个结构、计算模拟下的态势_STD、同时输出日志供细致检查
def compute_attitude_std_for_structure(struct: Dict, structure_id: int, attitude_map_template: Dict[str, float], recharge_map: dict[str, float], round_id: int) -> float:
    simulated_players = struct.get("simulated_players", {})
    values = []
    weights = []
    player_details = []
    for pid in attitude_map_template:
        if pid not in simulated_players:
            continue
        stat = simulated_players[pid]
        if stat.total_bet <= 0:
            continue

        # ✅ 修正点：取出结构模拟前的“纯历史窗口”进行态势计算（排除本轮影响）
        recent_bets = list(stat.recent_bets)
        recent_payouts = list(stat.recent_payouts)
        sim_bet = recent_bets[-1] if recent_bets else 0
        sim_payout = recent_payouts[-1] if recent_payouts else 0
        history_bets = recent_bets[:-1] if len(recent_bets) > 1 else []

        mem_avg_bet = compute_memory_avg_bet(sim_bet, history_bets)
        mem_profit = compute_memory_profit(sim_bet, sim_payout, history_bets)
        influence = compute_attitude(stat)  # 使用 memory_profits，模拟前已独立复制
        diff = compute_target_diff(influence, ATTITUDE_TARGET)
        w = recharge_map.get(pid, 0.0)
        if w > 0:
            values.append(diff)
            weights.append(w)
        player_details.append({
            "player_id": pid,
            "memory_avg_bet_player_simulated": mem_avg_bet,
            "total_bet_amount_player_simulated": stat.total_bet,
            "payout_amount_player_simulated": stat.total_payout,
            "memory_profit_player_simulated": mem_profit,
            "attitude_value_player_simulated": influence,
            "attitude_diff_player_simulated": diff,
            "attitude_diff_sq_player_simulated": diff ** 2,
            "attitude_var_contrib_player_simulated": compute_weighted_variance(diff, w),
            "recharge_weight_player_simulated": w
        })

    std = compute_weighted_std(values, weights) if weights else 0.0
    log_attitude_std_details(
        round_id=round_id,
        structure_id=structure_id,
        attitude_std=std,
        player_details=player_details,
        game_areas=struct["game_areas"]  # ✅ 补充
    )
    struct["attitude_std"] = std
    return std


# 对所有结构、调用上面的方法并行计算 rtp_std
def compute_rtp_std_for_all_structure(
    current_players: Dict[str, PlayerStats],
    current_bets: Dict[str, Dict[int, float]],
    *,
    expected_rtp: float,
    round_id: int
):
    with ThreadPoolExecutor(max_workers=MAX_STRUCTURE_SIM_THREADS) as executor:
        futures = [
            executor.submit(
                compute_rtp_std_for_structure,
                structure,
                current_players,
                current_bets,
                expected_rtp,
                round_id,
                structure_id
            ) for structure_id, structure in enumerate(WINNING_STRUCTURES)
        ]
        for f in futures:
            f.result()

    return WINNING_STRUCTURES


# 对所有结构、调用上面的方法并行计算 态势_std
def compute_attitude_std_for_all_structures(structure_cache: list[Dict], attitude_map_template: Dict[str, float], recharge_map: dict[str, float], round_id: int):
    results = []
    with ThreadPoolExecutor(max_workers=MAX_STRUCTURE_SIM_THREADS) as executor:
        futures = [
            executor.submit(
                compute_attitude_std_for_structure,
                struct,
                sid,
                attitude_map_template,
                recharge_map,
                round_id
            ) for sid, struct in enumerate(structure_cache)
        ]
        for f, struct in zip(futures, structure_cache):
            std = f.result()
            results.append({
                "game_areas": struct["game_areas"],
                "attitude_std": std
            })
    return results


# ✅ 封装结构模拟上下文
class SimulationContext:
    def __init__(self, stat_players: Dict[str, PlayerStats], current_bets: Dict[str, Dict[int, float]]):
        self.stat_players = {
            pid: stats.copy() for pid, stats in stat_players.items()
        }
        from copy import deepcopy
        self.current_bets = deepcopy(current_bets)

    def get_players(self) -> Dict[str, PlayerStats]:
        return self.stat_players

    def get_bets(self) -> Dict[str, Dict[int, float]]:
        return self.current_bets


# 判断结构是否落入置信区间
def mark_confidence_range_flags(structures: List[dict], std_bounds: tuple[float, float]):
    low, high = std_bounds
    for s in structures:
        std = s.get("rtp_std", float("inf"))
        s["within_confidence"] = bool(low <= std <= high)


# ✅ 主流程统一接口
def simulate_structure_metrics(context: SimulationContext, confidence_level, expected_rtp, current_round_id):
    current_players = context.get_players()
    current_bets = context.get_bets()

    # ✅ 一次性计算样本数与贡献
    sample_size, contributions = compute_equivalent_sample_size(current_players, current_bets)

    # ✅ 一次性计算置信区间并写入日志
    std_bounds = compute_dynamic_std_confidence_interval(
        STD_THRESHOLD,
        confidence_level,
        sample_size,
        round_id=current_round_id,
        player_contributions=contributions
    )

    # ✅ 模拟结构 RTP std（结构不含 within_confidence 字段）
    results = compute_rtp_std_for_all_structure(
        current_players=current_players,
        current_bets=current_bets,
        expected_rtp=expected_rtp,
        round_id=current_round_id
    )

    # ✅ 打标结构是否落入置信区间
    mark_confidence_range_flags(results, std_bounds)

    return results, std_bounds, sample_size


