from typing import Dict, List
from config import MEMORY_DECAY_ALPHA, MEMORY_WINDOW, MINIMUM_BET_THRESHOLD
from player_profiles import PlayerStats
from scipy.stats import norm
import math
from db_logger import log_confidence_bounds_details


# ✅ 动态置信区间：根据置信水平和样本数量调整标准差


def compute_dynamic_std_confidence_interval(
    base_std: float,
    confidence: float,
    sample_size: float,
    round_id: int = -1,
    player_contributions: list = None
) -> tuple[float, float]:
    if sample_size <= 1:
        std_bounds = (0.0, base_std)
    else:
        z = norm.ppf(1 - (1 - confidence) / 2)
        margin = z * base_std / (sample_size ** 0.5)
        std_bounds = (0.0, base_std + margin)

    # ✅ 写入置信区间精算日志（可选 round_id）
    if round_id >= 0 and player_contributions is not None:
        log_confidence_bounds_details(
            round_id=round_id,
            base_std=base_std,
            confidence_level=confidence,
            sample_size=sample_size,
            std_bounds=std_bounds,
            player_contributions=player_contributions
        )

    return std_bounds



# ✅ 窗口期平均投注额（含当前局）

def compute_memory_avg_bet(bet: float, past_bets: List[float], required_count: int = MEMORY_WINDOW) -> float:
    recent_bets = [b for b in past_bets if b > 0]
    if bet > 0:
        recent_bets.append(bet)
    return sum(recent_bets) / len(recent_bets) if recent_bets else 0.0


# ✅ 记忆型盈亏（态势指标）

def compute_memory_profit(bet: float, payout: float, past_bets: List[float]) -> float:
    avg_bet = compute_memory_avg_bet(bet, past_bets)
    if avg_bet <= 0:
        return 0.0
    return (payout - bet) / avg_bet


# ✅ RTP：最近 N 局的返奖率

def compute_rtp(stat: PlayerStats) -> float:
    total = sum(stat.recent_bets)
    return sum(stat.recent_payouts) / total if total > 0 else 0.0


# ✅ 态势值：记忆加权盈亏

def compute_attitude(stat: PlayerStats) -> float:
    attitude = 0.0
    for i, m in enumerate(reversed(stat.memory_profits)):
        weight = math.exp(-MEMORY_DECAY_ALPHA * i)
        attitude += m * weight
    return attitude


# ✅ 当前局返奖金额（根据命中区域）

def compute_payout(bet: Dict[int, float], winning_areas: List[int], payout_rates: Dict[int, float]) -> float:
    return sum(v * payout_rates[a] for a, v in bet.items() if a in winning_areas)


# ✅ 当前局即时 RTP

def compute_current_rtp(bet: Dict[int, float], payout: float) -> float:
    total = sum(bet.values())
    return payout / total if total > 0 else 0.0


# ✅ 汇总所有区域下注额（用于结构模拟图）

def aggregate_area_totals(bets: Dict[str, Dict[int, float]]) -> Dict[int, float]:
    totals = {}
    for player_bets in bets.values():
        for area, amount in player_bets.items():
            totals[area] = totals.get(area, 0) + amount
    return totals


# ✅ RTP 标准差相关函数

def compute_total_weight(players: List[PlayerStats]) -> float:
    return sum(p.total_bet for p in players)

def compute_weighted_variance(diff: float, weight: float) -> float:
    return weight * (diff ** 2)

def compute_weighted_std(values: List[float], weights: List[float]) -> float:
    total_weight = sum(weights)
    if total_weight <= 0:
        return 0.0
    weighted_variance = sum(w * (v ** 2) for v, w in zip(values, weights)) / total_weight
    return math.sqrt(weighted_variance)

def compute_target_diff(value: float, target: float) -> float:
    return value - target

# 用于置信误差的等效样本数量
def compute_equivalent_sample_size(
    current_players: Dict[str, PlayerStats],
    current_bets: Dict[str, Dict[int, float]],
    min_bet_threshold: float = MINIMUM_BET_THRESHOLD
) -> tuple[float, list]:
    numerator = 0.0
    denominator = 0.0
    contributions = []

    for pid, stat in current_players.items():
        current_bet = sum(current_bets.get(pid, {}).values())
        if current_bet < min_bet_threshold:
            continue

        recent_bet = sum(stat.recent_bets) + current_bet  # ✅ 补丁：确保包含本轮投注

        if current_bet > 0 and recent_bet > 0:
            equivalent_rounds = recent_bet / current_bet
            weighted = equivalent_rounds * recent_bet  # ✅ 窗口加权
            numerator += weighted
            denominator += recent_bet

            contributions.append({
                "player_id": pid,
                "total_bet": recent_bet,  # ✅ 明确：现在的“total_bet”指滑动期投注额
                "recent_bet_sum": recent_bet,
                "current_bet": current_bet,
                "equivalent_rounds": equivalent_rounds,
                "weighted_contribution": weighted
            })

    sample_size = numerator / denominator if denominator > 0 else 1.0
    return sample_size, contributions