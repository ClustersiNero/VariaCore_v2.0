# VariaCore - 控奖引擎核心模块

VariaCore 是一个用于高可控博彩/抽奖系统的核心引擎，支持实时 RTP 控制、玩家态势评估、多结构模拟与策略筛选。该项目由 Nero Cluster 发起，旨在构建可调优、可验证、可部署的控奖系统原型。

---

## 📦 项目模块结构

- `player_profiles.py` - 玩家行为与状态建模（含充值层级、下注习惯）
- `score_engine.py` - 核心结构模拟与 RTP/态势标准差评估
- `strategy.py` - 控奖策略筛选逻辑（多阶段筛选 + 加权选中）
- `game_round_controller.py` - 每局完整流程控制器（下注→控奖→开奖→结算）
- `platform_pool_and_generate_bet.py` - 平台水池 + 玩家下注生成逻辑
- `metrics_engine.py` - RTP、态势、记忆指标等计算工具集
- `export_engine.py` - 数据导出与日志转 Excel 表格
- `fast_simulation.py` - 高速模拟入口（支持日志导出与调试追踪）

---

## 📈 项目目标

- 控制玩家 RTP 曲线波动；
- 支持 3 阶段结构筛选（置信区间 + 态势标准差）；
- 记录详细调试日志（结构模拟日志、置信区间样本、玩家窗口态势）；
- 支持 Streamlit 仪表盘接入（开发中）；

---

## 🧠 模型原理

- ✅ 控奖结构模拟：对每种结构进行 RTP/态势评估
- ✅ 样本权重推导：基于投注窗口回推等效样本数
- ✅ 策略决策逻辑：3 阶段筛选 + 动态放水/回收策略
- ✅ 玩家态势追踪：窗口记忆 + 衰减记忆值

---

## 🛠 快速启动

```bash
# 安装依赖
pip install -r requirements.txt

# 启动快速模拟（生成日志）
python fast_simulation.py
```

---

## 📁 日志与输出

输出日志将保存在以下目录：
- `simulation_output/运营导出/` - 玩家汇总、结构表、平台参数等主视图；
- `simulation_output/研发调试/` - rtp_std、attitude_std、confidence_log 明细；
- `simulation_output/其他杂项/` - 原始 JSON 格式日志。

---

## 👤 作者信息

> Author: Nero Cluster  
> Project: 控奖策略实验平台 / Project ONE  
> License: (自定义或 MIT/GPL，如未设置请留空)
