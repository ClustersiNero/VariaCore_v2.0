# platform_pool_and_generate_bet.py

"""
平台水池管理模块：
- 记录平台盈亏累积值（抽水后下注金额流入，中奖金额流出）
- 根据水位线调整目标 RTP（实现动态放水 / 回收策略）
"""

from config import TARGET_RTP, PAYOUT_RATES
from typing import List, Tuple
import random

# 平台公共水池、投注在抽水后流入、开奖从水池流出
class PlatformPool:
    def __init__(self, tax_rate: float = 1.0 - TARGET_RTP):
        rtp_thresholds: List[Tuple[int, float, float]] = [
            # (200,   10_000_000, float("inf")),
            # (140,   8_000_000, 10_000_000),
            # (120,   6_000_000, 8_000_000),
            # (97,    4_000_000, 6_000_000),
            # (80,    2_000_000, 4_000_000),
            # (60,    0,         2_000_000),
            # (0,     -float("inf"), 0),
            (105,   25_000_000, float("inf")),
            (100,   20_000_000, 25_000_000),
            (97,    15_000_000, 20_000_000),
            (90,    10_000_000, 15_000_000),
            (80,    5_000_000, 10_000_000),
            (70,    0,          5_000_000),
            (50,     -float("inf"), 0),
        ]
        self.rtp_thresholds = rtp_thresholds

        middle_entry = self.rtp_thresholds[len(self.rtp_thresholds) // 2]
        middle_low, middle_high = middle_entry[1], middle_entry[2]
        self.pool_value = (middle_low + middle_high) / 2

        self.tax_rate = tax_rate
        self.history = []

    def inflow(self, bet_amount: float):
        taxed = bet_amount * (1 - self.tax_rate)
        self.pool_value += taxed
        self.history.append(("in", taxed))

    def outflow(self, payout_amount: float):
        self.pool_value -= payout_amount
        self.history.append(("out", payout_amount))

    def get_current_rtp_target(self) -> float:
        for rtp_percent, low, high in self.rtp_thresholds:
            if low <= self.pool_value < high:
                return rtp_percent / 100.0
        return 1.00

    def get_pool_value(self) -> float:
        return self.pool_value

    def get_latest_deltas(self, n: int = 10):
        return self.history[-n:]


# 玩家下注模拟：基于频率、区域偏好与金额分布动态生成下注结构
def generate_player_bets(players: dict, round_index: int) -> dict:
    bets = {}

    for pid, player in players.items():
        if round_index == 1:
            player.is_active = random.random() < 1
            if not player.is_active:
                player.consecutive_missed = 1
        
        else:
            if player.is_active:
                if random.random() > 2:
                    player.is_active = False
                    player.consecutive_missed = 1
            else:
                p_restore = min(1.0, 0.1 + 0.05 * player.consecutive_missed)
                if random.random() < p_restore:
                    player.is_active = True
                    player.consecutive_missed = 0
                else:
                    player.consecutive_missed += 1

        if not player.is_active:
            continue

        total_amount = random.randint(int(player.amount_scale * 0.8), int(player.amount_scale * 1.2))
        min_area, max_area = player.area_range
        chosen_num = random.randint(min_area, max_area)
        chosen_areas = random.sample(range(1, 9), chosen_num)

        base_weights = [1 / PAYOUT_RATES[area] for area in chosen_areas]
        total_weight = sum(base_weights)
        norm_weights = [w / total_weight for w in base_weights]

        total_units = total_amount // 500
        unit_allocations = [0] * chosen_num

        for _ in range(total_units):
            r = random.random()
            acc = 0.0
            for i, w in enumerate(norm_weights):
                acc += w
                if r <= acc:
                    unit_allocations[i] += 1
                    break

        final_bets = {}
        for area, units in zip(chosen_areas, unit_allocations):
            if units > 0:
                final_bets[area] = units * 100

        bets[pid] = final_bets

    return bets
