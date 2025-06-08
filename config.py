# config.py

# 赔率配置
PAYOUT_RATES = {
    1: 5,
    2: 5,
    3: 5,
    4: 5,
    5: 10,
    6: 15,
    7: 25,
    8: 45,
}

# 中奖结构（字段重命名：weight → base_weight）
WINNING_STRUCTURES = [
    {"areas": [1], "base_weight": 1930},
    {"areas": [2], "base_weight": 1930},
    {"areas": [3], "base_weight": 1930},
    {"areas": [4], "base_weight": 1930},
    {"areas": [5], "base_weight": 965},
    {"areas": [6], "base_weight": 640},
    {"areas": [7], "base_weight": 390},
    {"areas": [8], "base_weight": 215},
    {"areas": [1, 2, 3, 4], "base_weight": 60},
    {"areas": [5, 6, 7, 8], "base_weight": 10},
]

# 游戏阶段时长（秒）
BETTING_DURATION = 3   # 下注阶段时长
WAITING_DURATION = 1    # 等待开奖阶段时长
ANIMATION_DURATION = 1  # 开奖动画时长
ROUND_TOTAL_DURATION = BETTING_DURATION + WAITING_DURATION + ANIMATION_DURATION # 一局总时长

# 策略相关控制参数
STD_THRESHOLD = 0.10   # 基础标准差
CONFIDENCE_LEVEL = 0.95 # 置信水平
MINIMUM_BET_THRESHOLD = 1    # 最小下注额
TARGET_RTP = 0.97  # 目标 RTP
ATTITUDE_TARGET = 0  # 目标态势

# 盈利态势
MEMORY_WINDOW = 10  # N 局窗口长度
MEMORY_DECAY_ALPHA = 0.3 # 衰减函数参数，控制遗忘速度
# 最近计算RTP的局数
RECENT_RTP_WINDOW = 30  # 默认使用最近100局计算 RTP
MAX_PAYOUT_RATE = 50  # 没有结构落入置信区间时的最大赔率倍率

# ✅ 控制结构筛选策略各阶段的启用状态
ENABLE_STD_FILTER = True             # 第一阶段：RTP标准差是否启用
ENABLE_MEMORY_FILTER = True         # 第二阶段：态势影响是否启用

# 设置最大并行线程数，默认值为物理核心数的一半
import os
MAX_STRUCTURE_SIM_THREADS = os.cpu_count() // 2

# 结构筛选策略容许扩展幅度
RTP_STD_EXPAND_RATIO = 110  # 表示110%
MEMORY_STD_EXPAND_RATIO = 110  # 表示110%

# ✅ 统一日志导出目录定义
BASE_OUTPUT_DIR = "simulation_output"
EXPORT_DIR = os.path.join(BASE_OUTPUT_DIR, "运营导出")
DEBUG_DIR = os.path.join(BASE_OUTPUT_DIR, "研发调试")
MISC_DIR = os.path.join(BASE_OUTPUT_DIR, "其他杂项")
