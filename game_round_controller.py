from enum import Enum, auto
from config import PAYOUT_RATES, CONFIDENCE_LEVEL
from player_profiles import Player, PlayerStats
from platform_pool_and_generate_bet import generate_player_bets
from score_engine import SimulationContext, simulate_structure_metrics, compute_attitude_std_for_all_structures
from strategy import select_structure
from db_logger import log_player_detail, log_round_summary
from metrics_engine import (
    compute_rtp, compute_memory_profit, compute_memory_avg_bet, compute_payout, compute_current_rtp, aggregate_area_totals, compute_attitude
)

# 单局游戏流程控制在此实现
class GameRoundController:
    
    def __init__(self, state):
        self.state = state
        self.round_id = 0
        self.sim_players = state["sim_players"]
        self.stat_players = state["stat_players"]
        self.pool = state["platform_pool"]
        self.confidence_level = state.get("confidence_level", CONFIDENCE_LEVEL)

    def initialize_round(self):
        self.round_id += 1
        self.state["round_id"] = self.round_id
        self.state["final_outcome"] = None
        self.state["structure_result_cache"] = None
        self.state["current_bets"] = {}
        self.state["_summary"] = None
        self.state["expected_rtp"] = self.pool.get_current_rtp_target()

    def prepare_round_data(self):
        bets = generate_player_bets(self.sim_players, self.round_id)
        self.state["current_bets"] = bets

    def simulate_structures(self):
        context = SimulationContext(self.stat_players, self.state["current_bets"])
        expected_rtp = self.state["expected_rtp"]

        results, std_bounds, sample_size = simulate_structure_metrics(
            context, self.confidence_level, expected_rtp, current_round_id=self.round_id
        )

        recharge_map = {pid: p.recharge_amount for pid, p in self.sim_players.items()}
        attitude_results = compute_attitude_std_for_all_structures(results, context.get_players(), recharge_map, self.round_id)
        for res in results:
            for att in attitude_results:
                if att["game_areas"] == res["game_areas"]:
                    res["attitude_std"] = att["attitude_std"]
                    break

        self.state["structure_result_cache"] = {
            "all_structures": results,
            "std_bounds": std_bounds,
            "sample_size": sample_size
        }

    def choose_final_structure(self):
        self.state["final_outcome"] = select_structure(self.state["structure_result_cache"]["all_structures"])

    def settle_outcome(self):
        bets = self.state["current_bets"]
        outcome = self.state["final_outcome"]
        winning_areas = outcome["game_areas"]
        total_bet, total_payout = 0, 0

        for pid, bet in bets.items():
            bet_sum = sum(bet.values())
            payout = compute_payout(bet, winning_areas, PAYOUT_RATES)

            self.pool.inflow(bet_sum)
            self.pool.outflow(payout)

            self.stat_players[pid].update(bet_sum, payout)
            self.state["rtp_history"].setdefault(pid, []).append(compute_rtp(self.stat_players[pid]))

            total_bet += bet_sum
            total_payout += payout

        self.state["_summary"] = {
            "total_bet_amount_platform": total_bet,
            "total_payout_amount_platform": total_payout,
            "net_profit_platform": total_bet - total_payout
        }

    def finalize_round(self):
        bets = self.state["current_bets"]
        outcome = self.state["final_outcome"]
        winning_areas = outcome["game_areas"]
        attitudes = {
            pid: compute_attitude(stats)
            for pid, stats in self.stat_players.items()
        }

        for pid, bet in bets.items():
            bet_sum = sum(bet.values())
            payout = compute_payout(bet, winning_areas, PAYOUT_RATES)

            # ✅ 修正：传入真实当局 bet / payout，避免记忆盈亏恒为 0
            mem_profit = compute_memory_profit(bet_sum, payout, list(self.stat_players[pid].recent_bets))
            mem_avg_bet = compute_memory_avg_bet(0, list(self.stat_players[pid].recent_bets))

            log_player_detail(
                round_id=self.round_id,
                player_id=pid,
                area_bets=bet,
                total_bet=bet_sum,
                payout=payout,
                recharge=self.sim_players[pid].recharge_amount,
                attitude=attitudes[pid],
                memory_profit=mem_profit,
                memory_avg_bet=mem_avg_bet,
                rtp=compute_rtp(self.stat_players[pid]),
                current_rtp=compute_current_rtp(bet, payout),
                stat_players=self.stat_players  # ✅ 补上这里
            )

        area_totals = aggregate_area_totals(bets)

        log_round_summary(
            round_id=self.round_id,
            player_bets=bets,
            area_totals=area_totals,
            winning_areas=winning_areas,
            total_bet=self.state["_summary"]["total_bet_amount_platform"],
            total_payout=self.state["_summary"]["total_payout_amount_platform"],
            structures=self.state["structure_result_cache"]["all_structures"],
            pool_value=self.pool.get_pool_value(),
            target_rtp=self.state["expected_rtp"],
            std_bounds=self.state["structure_result_cache"].get("std_bounds")
        )
