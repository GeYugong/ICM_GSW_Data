# ICM 2026 Problem D: Golden State Warriors Data Engine 🏀

本项目为 **2026 ICM 数学建模竞赛 (Problem D)** 专用数据工程仓库。
核心目标是构建金州勇士队 (Golden State Warriors, GSW) 过去 5 年（2021-2025）的全维度商业与竞技数据集，用于训练 （盈利模型）和 （估值模型）。

## 📂 Project Structure (仓库结构)

```text
ICM_GSW_Data/
├── data/                         # [核心产出] 清洗后的 CSV 数据集
│   ├── gsw_draft_history.csv     # 历史选秀记录 (Source: B-Ref)
│   ├── gsw_financing_5years.csv  # 融资结构与估值 (Source: Forbes)
│   ├── gsw_player_value.csv      # 球员高阶身价 PER/WS (Source: B-Ref)
│   ├── gsw_future_assets.csv     # 未来选秀权资产 (Source: RealGM)
│   ├── gsw_salaries_5years.csv   # 薪资支出 Cap Hit (Source: Spotrac)
│   ├── gsw_schedule_5years.csv   # 每日赛程与胜率 (Source: B-Ref)
│
├── scripts/                      # [工程源码] 数据爬虫与清洗脚本
│   ├── get_finance_structure.py  # 生成债权/股权融资数据
│   ├── get_player_value.py       # 爬取球员效率值 (破解 HTML 注释)
│   ├── get_salaries.py           # 爬取薪资数据 (含死磕模式 + 自动重试)
│   ├── get_schedule.py           # 爬取赛程并计算 Rolling Win Rate
│   └── get_transactions_and_draft.py # 爬取选秀与交易记录
│
├── requirements.txt              # Python 依赖库
└── README.md                     # 项目说明文档

```

---

## 🛠️ Technical Principles (技术原理与策略)

针对体育商业数据分散、格式不统一以及反爬虫严格的特点，本项目采用了 **"Hybrid Data Engineering" (混合数据工程)** 策略。

### 1. 动态爬取与特征工程 (Scraping & Feature Engineering)

针对比赛数据和实时变化的数据，我们使用 `requests` + `pandas` 进行高频抓取。

* **赛程数据 (`get_schedule.py`):**
* **原理:** 遍历 Basketball-Reference 赛季页面。
* **特征工程:** 自动计算 **“近10场胜率” (Rolling Win Rate)**，用于量化球队的竞技状态 () 波动。
* **技术点:** 使用代理池 (Proxy) 解决高频访问限制。


* **球员身价 (`get_player_value.py`):**
* **原理:** 抓取高阶数据表 (Advanced Stats)。
* **攻防对抗:** 针对 B-Ref 将数据隐藏在 HTML 注释 (``) 中的反爬机制，脚本内置了解析器自动去除注释符号，提取 `PER` (效率值) 和 `WS` (胜利贡献值)。


* **薪资数据 (`get_salaries.py`):**
* **原理:** 针对 Spotrac 的 SSL 指纹识别，采用了 `verify=False` 和 User-Agent 轮询机制（"死磕模式"），确保拿到真实的 Cap Hit 数据。



### 2. 权威数据重构 (Authoritative Reconstruction)

针对财务数据（非上市公司不公开）和非结构化数据，我们采用基于权威报告的重构方法。

* **融资与估值 (`get_finance_structure.py`):**
* **原理:** 既然无法爬取 PDF 年报，我们基于 **Forbes (福布斯)** 历年发布的 "NBA Team Valuations" 榜单，手动录入基准数据，并通过 Python 自动计算衍生指标（如 `Debt_Amount` = Valuation * Debt%）。
* **价值:** 保证了  (债权) 和  (股权) 的金融准确性。


* **未来资产 (`get_transactions_and_draft.py`):**
* **原理:** 历史选秀权可以爬取，但未来的选秀权（资产）存在于复杂的交易文本中。我们通过硬编码 (Hardcoding) 勇士队当前的资产状态（如 2030 年受保护首轮签），将其量化为数值。



### 3. 保底机制 (Fail-safe Mechanism)

为了应对比赛期间网络不稳定的情况，所有脚本均内置了 **Backup Data (保底数据)**。

* **逻辑:** 如果爬虫因为网络原因 (`ConnectionError`) 或 网站结构变更 (`ValueError`) 失败，脚本会自动加载预置的、经人工核实的真实历史数据。
* **结果:** 确保无论网络环境如何，`data/` 目录下永远有可用的 CSV 文件，不阻塞建模进度。

---

## 📊 Data Dictionary (数据字典与建模映射)

| 文件名 | 核心变量 (Variables) | 建模对应 (Model Mapping) |
| --- | --- | --- |
| **gsw_schedule_5years.csv** | `Win_Flag`, `Recent_Win_Rate_10` | ** (竞技状态)**: 衡量球队即时战绩 |
| **gsw_player_value.csv** | `Avg_PER` (平均能力), `Top_Player_PER` (球星成色) | ** & **: 竞技基础与球星号召力 |
| **gsw_salaries_5years.csv** | `Total_Salary_Expense` | ** (薪资管理)**: 球队最大的运营成本 |
| **gsw_financing_5years.csv** | `Debt_Amount_M`, `Equity_Value_M`, `Leverage` | ** (资本结构)**: 债权/股权融资与杠杆率 |
| **gsw_future_assets.csv** | `First_Round_Pick` (0/1) | ** (资产储备)**: 用于交易或未来的潜在价值 |

---

## 🚀 Usage (使用方法)

1. **安装依赖:**
```bash
pip install -r requirements.txt

```


2. **设置代理 (可选):**
如果在中国大陆地区运行，请确保本地代理端口为 `7897` (脚本默认配置)，或在脚本中修改 `PROXIES` 变量。
3. **运行数据管线:**
```bash
# 1. 抓取基础数据
python scripts/get_schedule.py
python scripts/get_salaries.py
python scripts/get_player_value.py

# 2. 生成财务与资产数据
python scripts/get_finance_structure.py
python scripts/get_ticket_revenue.py
python scripts/get_transactions_and_draft.py

```


4. **数据产出:**
运行结束后，所有清洗好的 CSV 文件将保存在 `data/` 目录下，可直接导入 MATLAB / Python 进行建模。

---

## 🔗 Data Sources (数据来源)

* **Game Stats:** [Basketball-Reference](https://www.basketball-reference.com/)
* **Financials:** [Forbes NBA Valuations](https://www.forbes.com/lists/nba-valuations/)
* **Salaries:** [Spotrac NBA Cap Tracker](https://www.spotrac.com/nba/)
* **Attendance:** [ESPN NBA Attendance](http://www.espn.com/nba/attendance)

---

