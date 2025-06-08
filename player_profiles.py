import random
import numpy as np
from typing import List, Dict
from collections import deque
import math
from config import RECENT_RTP_WINDOW, MEMORY_WINDOW


class Player:
    AMOUNT_SCALE_MAP = {'超R': 5_000_000, '大R': 500_000, '中R': 100_000, '小R': 10_000}
    AREA_RANGE_MAP = {'海投': (6, 8), '保守': (3, 5), '谨慎': (1, 2)}
    BET_FREQUENCY = {'高频': 10, '中频': 3, '低频': 1}
    REBET_PROBABILITY = {'高概率': 0.8, '低概率': 0.3, '零概率': 0.0}

    def __init__(self, uid, force_super=False):
        self.uid = uid

        if force_super:
            self.bet_amount_class = '超R'
        else:
            self.bet_amount_class = random.choices(
                ['大R', '中R', '小R'], weights=[2, 3, 4], k=1
            )[0]

        self.bet_area_style = random.choices(list(self.AREA_RANGE_MAP.keys()), weights=[0, 6, 2], k=1)[0]
        self.bet_freq_class = random.choices(list(self.BET_FREQUENCY.keys()), weights=[3, 3, 1], k=1)[0]
        self.rebet_prob_class = random.choices(list(self.REBET_PROBABILITY.keys()), weights=[5, 3, 2], k=1)[0]

        self.amount_scale = self.AMOUNT_SCALE_MAP[self.bet_amount_class]
        self.area_range = self.AREA_RANGE_MAP[self.bet_area_style]
        self.bet_freq_value = self.BET_FREQUENCY[self.bet_freq_class]
        self.rebet_prob = self.REBET_PROBABILITY[self.rebet_prob_class]

        self.recharge_amount = self._generate_recharge_amount()
        self.consecutive_missed = 0
        self.is_active = False

    def _generate_recharge_amount(self):
        if self.bet_amount_class == "超R":
            val = int(np.random.lognormal(mean=5, sigma=0.6))
            val = min(max(val, 1000), 100000)
            return val // 1000 * 1000
        elif self.bet_amount_class == "大R":
            val = int(np.random.lognormal(mean=4, sigma=0.5))
            val = min(max(val, 100), 5000)
            return val // 100 * 100
        elif self.bet_amount_class == "中R":
            val = int(np.random.lognormal(mean=3, sigma=0.4))
            val = min(max(val, 30), 100)
            return val // 10 * 10
        else:
            val = int(np.random.lognormal(mean=2, sigma=0.3))
            val = min(max(val, 0), 30)
            return val // 5 * 5


class PlayerStats:
    def __init__(self):
        self.total_bet: float = 0.0
        self.total_payout: float = 0.0
        self.history: List[dict] = []
        self.recent_bets = deque(maxlen=RECENT_RTP_WINDOW)
        self.recent_payouts = deque(maxlen=RECENT_RTP_WINDOW)
        self.memory_profits = deque(maxlen=MEMORY_WINDOW)

    def update(self, bet: float, payout: float):
        from metrics_engine import compute_memory_profit
        self.total_bet += bet
        self.total_payout += payout
        self.history.append({"bet": bet, "payout": payout})

        if bet > 0:
            self.recent_bets.append(bet)
            self.recent_payouts.append(payout)

            memory_profit = compute_memory_profit(bet, payout, list(self.recent_bets))
            self.memory_profits.append(memory_profit)

    def copy(self):
        new = PlayerStats()
        new.total_bet = self.total_bet
        new.total_payout = self.total_payout
        new.history = self.history.copy()
        new.recent_bets = self.recent_bets.copy()
        new.recent_payouts = self.recent_payouts.copy()
        new.memory_profits = self.memory_profits.copy()
        return new

    def to_dict(self):
        return {
            "total_bet": self.total_bet,
            "total_payout": self.total_payout,
            "history": self.history.copy(),
            "recent_bets": list(self.recent_bets),
            "recent_payouts": list(self.recent_payouts),
            "memory_profits": list(self.memory_profits)
        }

    @staticmethod
    def from_dict(data):
        obj = PlayerStats()
        obj.total_bet = data.get("total_bet", 0.0)
        obj.total_payout = data.get("total_payout", 0.0)
        obj.history = data.get("history", [])
        obj.recent_bets = deque(data.get("recent_bets", []), maxlen=RECENT_RTP_WINDOW)
        obj.recent_payouts = deque(data.get("recent_payouts", []), maxlen=RECENT_RTP_WINDOW)
        obj.memory_profits = deque(data.get("memory_profits", []), maxlen=MEMORY_WINDOW)
        return obj


# ✅ 初始化玩家列表

def initialize_players(num_players=10, super_r_count=1) -> Dict[str, Player]:
    players = {}
    for i in range(1, super_r_count + 1):
        pid = f'player_{i}'
        players[pid] = Player(uid=pid, force_super=True)
    for i in range(super_r_count + 1, num_players + 1):
        pid = f'player_{i}'
        players[pid] = Player(uid=pid, force_super=False)
    return players
