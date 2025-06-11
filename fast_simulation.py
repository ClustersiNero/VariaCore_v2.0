import time
import json
import os
from game_round_controller import GameRoundController
from player_profiles import initialize_players, PlayerStats
from platform_pool_and_generate_bet import PlatformPool
from config import TARGET_RTP, CONFIDENCE_LEVEL
from export_engine import export_all_logs, export_debug_inspection_logs
from db_logger import round_log, player_log, rtp_std_log, attitude_std_log, confidence_log
from config import JSON_DIR

ROUNDS = 20
PLAYERS = 2

# 脚本模拟主流程：批量执行 controller，连续模拟指定轮数
def run_simulation(rounds, num_players):
    print(f"\n🚀 快照模拟启动，共 {rounds} 局...")
    start_time = time.time()

    # ✅ 构造最小状态集，仅用于初始化 controller
    state = {
        "sim_players": initialize_players(num_players),
        "stat_players": {},
        "platform_pool": PlatformPool(),
        "rtp_history": {},
        "round_id": 1,
        "confidence_level": CONFIDENCE_LEVEL
    }
    state["stat_players"] = {pid: PlayerStats() for pid in state["sim_players"]}

    controller = GameRoundController(state)

    for _ in range(rounds):
        controller.initialize_round()
        controller.prepare_round_data()
        controller.simulate_structures()
        controller.choose_final_structure()
        controller.settle_outcome()
        controller.finalize_round()

        if state["round_id"] == rounds:
            export_all_logs()  # ✅ 主日志导出（导出至 EXPORT_DIR）
            export_debug_inspection_logs()  # ✅ 精算调试日志导出（导出至 DEBUG_DIR）

            os.makedirs(JSON_DIR, exist_ok=True)
            with open(os.path.join(JSON_DIR, "round_log.json"), "w", encoding="utf-8") as f:
                json.dump(round_log, f, ensure_ascii=False, indent=2)

            with open(os.path.join(JSON_DIR, "player_log.json"), "w", encoding="utf-8") as f:
                json.dump(player_log, f, ensure_ascii=False, indent=2)

            with open(os.path.join(JSON_DIR, "rtp_std_log.json"), "w", encoding="utf-8") as f:
                json.dump(rtp_std_log, f, ensure_ascii=False, indent=2)

            with open(os.path.join(JSON_DIR, "attitude_std_log.json"), "w", encoding="utf-8") as f:
                json.dump(attitude_std_log, f, ensure_ascii=False, indent=2)
                
            with open(os.path.join(JSON_DIR, "confidence_log.json"), "w", encoding="utf-8") as f:
                json.dump(confidence_log, f, ensure_ascii=False, indent=2)


        elapsed = time.time() - start_time
        print(f"\r已完成 {state['round_id']}/{rounds} 局，用时 {elapsed:.1f} 秒", end="", flush=True)

    print("\n✅ 模拟完成，日志已写入")

def main():
    run_simulation(rounds=ROUNDS, num_players=PLAYERS)

if __name__ == "__main__":
    main()
