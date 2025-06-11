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

# ✅ 控制结构筛选策略各阶段的启用状态
ENABLE_STD_FILTER = True             # 第一阶段：RTP标准差是否启用
ENABLE_MEMORY_FILTER = True         # 第二阶段：态势影响是否启用

# 设置最大并行线程数，默认值为物理核心数的一半
import os
MAX_STRUCTURE_SIM_THREADS = os.cpu_count() // 2

# 结构筛选策略容许扩展幅度
RTP_STD_EXPAND_RATIO = 110  # 表示110%
MEMORY_STD_EXPAND_RATIO = 110  # 表示110%



BASE_OUTPUT_DIR = "simulation_output"

JSON_DIR = os.path.join(BASE_OUTPUT_DIR, "json")         # ✅ 主日志输出
EXCEL_DIR = os.path.join(BASE_OUTPUT_DIR, "excel")       # ✅ 表格导出
DEBUG_DIR = os.path.join(BASE_OUTPUT_DIR, "debug")       # ✅ 精算调试
SNAPSHOT_DIR = os.path.join(BASE_OUTPUT_DIR, "snapshot_dashboard")  # ✅ 仪表盘展示输出