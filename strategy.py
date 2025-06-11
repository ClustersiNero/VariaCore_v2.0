# strategy.py

from typing import List, Dict
import random
from config import RTP_STD_EXPAND_RATIO, MEMORY_STD_EXPAND_RATIO, ENABLE_STD_FILTER, ENABLE_MEMORY_FILTER

# 策略筛选主逻辑：依次执行三阶段筛选并记录每阶段是否进入
def select_structure(results: List[Dict]) -> Dict:
    # ✅ 初始化阶段标记，确保每一轮的标记都从 False 开始
    for r in results:
        r["entered_phase1"] = False
        r["entered_phase2"] = False
        r["entered_phase3"] = False

    # ✅ 第一阶段：RTP 标准差筛选
    if ENABLE_STD_FILTER:
        phase1_candidates = [r for r in results if r.get("within_confidence")]
        if not phase1_candidates and results:
            min_std = min(r["rtp_std"] for r in results if r.get("rtp_std") is not None)
            std_threshold = min_std * RTP_STD_EXPAND_RATIO / 100
            phase1_candidates = [r for r in results if r.get("rtp_std", float("inf")) <= std_threshold]
    else:
        phase1_candidates = results

    if not phase1_candidates:
        return {}

    # ✅ 标记通过第一阶段筛选的结构
    for r in phase1_candidates:
        r["entered_phase1"] = True

    # ✅ 第二阶段：按态势标准差筛选
    if ENABLE_MEMORY_FILTER:
        memstd_values = [r.get("attitude_std", 0.0) for r in phase1_candidates]
        if memstd_values:
            min_memstd = min(memstd_values)
            mem_threshold = min_memstd * MEMORY_STD_EXPAND_RATIO / 100
            phase2_candidates = [r for r in phase1_candidates if r.get("attitude_std", float("inf")) <= mem_threshold]
    else:
        phase2_candidates = phase1_candidates

    # ✅ 标记通过第二阶段筛选的结构
    for r in phase2_candidates:
        r["entered_phase2"] = True

    if not phase2_candidates:
        return {}

    # ✅ 第三阶段：选择最终结构
    selected = random.choices(
        population=phase2_candidates,
        weights=[r.get("base_weight", 1.0) for r in phase2_candidates],
        k=1
    )[0]

    for r in results:
        r["is_final_outcome"] = (r.get("game_areas") == selected.get("game_areas"))
        if r["is_final_outcome"]:
            r["entered_phase3"] = True

    return selected
