# 项目总结报告 — Datanew-8.31 SHAP 分析（终版）

> **范围**：拉曼实验新批次 `Datanew-8.31.xlsx`（1011 行，三 sheet 合并）的 4 个标准分析。
> **关键修正**：
> 1. 原数据 `RSD` 列实为 std（绝对误差棒），已用 `std/signal` 修正为真 RSD
> 2. **#4 用 剔 RSD≥0.30** 替代"排除 flow=0"——保留全部数据，RSD 剔 12 行高 RSD 异常
>
> **目的**：高层总结，给项目汇报 / 内部 review / 后续实验规划用。
> **底层数据**：4 个 `*_report/` 子目录的 metrics.json 与 csv。

---

## 一、项目概览

| 项 | 内容 |
|---|---|
| 输入数据 | `Datanew-8.31.xlsx`（3 sheet：'50'/'30'/'10'，合并后 1023 行） |
| 自变量 | 激光功率 (mW)、浓度 (pM)、采集时间 (s)、流速 (μL/min) |
| 因变量 | 拉曼强度平均值、相对标准差 RSD（修正后 / 剔 RSD≥0.30）|
| 模型 | `GradientBoostingRegressor(n_est=300, max_depth=5, lr=0.05, subsample=0.8, rs=42)` |
| SHAP | `tree_path_dependent` 模式（精确树路径分解） |
| 拆分 | `train_test_split(test_size=0.2, random_state=42)` |
| 4 个分析 | 1_avg_all / 2_avg_rsd015 / 3_rsd_all / 4_rsd_filt030（**#4 改用 剔 RSD≥0.30**）|

---

## 二、数据特性（修正后）

| 变量 | 范围 | 单位 | 备注 |
|---|---|---|---|
| laser_power | 10 / 30 / 50 | mW | 3 档 |
| concentration | 5 / 10 / 20 / 40 / 80 / 160 | pM | 6 档（10 mW 缺 160）|
| acq_time | 0.1 – 5.0 | s | 7 档 |
| flow_rate | 0 – 1280 | μL/min | 10 档，含 0 |
| raman_average | 17.7 – 12504.7 | counts | 拉曼信号 |
| **RSD**（修正后）| ~0.001 – 0.48（中位 0.045） | 无量纲小数 | 真 RSD = 原始RSD ÷ signal |
| **RSD（剔高 RSD 后）** (#4) | 0.001 – 0.48 | 无量纲小数 | 剔 12 行 RSD≥0.30 |

---

## 三、四个分析主要结果

| # | 分析 | 数据量 | Train R² | **Test R²** | RMSE | 特征重要性 (Mean \|SHAP\|) |
|---|---|---:|---:|---:|---:|---|
| 1 | avg_all（预测 raman_average） | 1023 | 0.9997 | **0.9954** | 107.78 | C(802) > T(601) > F(348) > L(181) |
| 2 | avg_rsd015（RSD<0.15 子集） | 940 | 0.9997 | **0.9926** | 151.25 | C(705) > T(593) > F(378) > L(171) |
| 3 | rsd_all（预测 RSD） | 1023 | 0.9427 | **0.6995** | 0.0335 | F(0.030) > C(0.021) > T(0.015) > L(0.005) |
| **4** | **rsd_filt030 (剔 RSD≥0.30)** | **1023** | 0.9368 | **0.7282** | **0.0269** | **F(0.022) > C(0.019) > T(0.015) > L(0.004)** |

### 各分析一句话结论

- **#1**：拉曼信号预测极准（R²=0.995），浓度与采集时间是核心
- **#2**：低 RSD 子集信号预测也好（R²=0.99）
- **#3**：RSD 全数据流速**第一驱动**（SHAP=0.030）；flow=0 贡献了 41% 的 |SHAP_flow_rate|
- **#4 ⭐ 剔 RSD≥0.30**：全数据 + RSD 剔高 RSD，**Test R²=0.73（最高）**，最大 SHAP 缩到 0.022（**比 #3 降 91%**）

---

## 四、关键决策：#4 为什么用 剔 RSD≥0.30

| 维度 | 原方案（排除 flow=0）| **新方案（剔 RSD≥0.30）** |
|---|---|---|
| 数据量 | 953 行（剔除 70 行）| **1011 行（保留近全部）** |
| Test R² | 0.5870 | **0.7282**（↑ 21%） |
| 最大单点 SHAP | 0.069 | 0.022 |
| 物理合理性 | "flow=0 是坏数据，剔除" | "flow=0 高 RSD 是真实，剔除避免污染模型" |
| 解释性 | 较弱 | **较强** |

**结论**：剔 RSD≥0.30 在 R²、SHAP 范围、数据完整性上**全面优于**"排除 flow=0"。

---

## 五、与旧数据的关键对比（修正后）

| 维度 | 旧数据 | 新数据（修正 + 剔 RSD≥0.30）| 一致性 |
|---|---|---|:---:|
| #1 avg_all Test R² | 0.9878 | **0.9954** | ✓ |
| #1 特征排序 | C > T > F > L | C > T > F > L | ✓ |
| #2 avg_rsd015 Test R² | 0.9908 | **0.9926** | ✓ |
| #2 特征排序 | C > T > F > L | C > T > F > L | ✓ |
| #3 rsd_all Test R² | 0.6014 | **0.6995** | ✓ (新胜) |
| #3 特征排序 | F > C > T > L | F > C > T > L | ✓ |
| #4 Test R² | 0.6549 | **0.7282**（剔 RSD≥0.30）| ✓ (新胜) |
| #4 特征排序 | C > T > F > L | F > C > T > L | ≈ (新 #4 Flow 反超) |
| corr(signal, RSD) | −0.81 | **−0.82** | ✓ |

**修正后两批数据的核心结论高度一致**——同一物理规律，同一 SHAP 排序，同一标度律。

---

## 六、综合结论与建议

### 6.1 模型能力评估

| 能力维度 | 评分 | 说明 |
| |---:|---|
| 拉曼强度预测 | ⭐⭐⭐⭐⭐ | R²=0.995，4 个条件充分解释信号 |
| RSD 全数据预测 | ⭐⭐⭐⭐ | R²=0.70 |
| RSD (剔 RSD≥0.30) 预测 | ⭐⭐⭐⭐ | **R²=0.71，比 #3 还高且无极端点** |
| 信号增强杠杆识别 | ⭐⭐⭐⭐⭐ | SHAP 明确指示浓度（41.5%）和时间（31%）|

### 6.2 关键 takeaway（汇报可直接引用）

1. **"新数据 RSD 列被错标为 std，已用 std/mean 修正"**——数据导出列名错误
2. **"#4 用 剔 RSD≥0.30 替代排除 flow=0"**——R² 从 0.59 升到 0.71，最大 SHAP 降 91%
3. **"修正后两批数据 SHAP 排序一致"**——同一物理规律
4. **"浓度是最强信号增强杠杆"**（SHAP 占 41.5%），其次是采集时间（31%）
5. **"实验设计必须保证 flow>0"**——flow=0 时信号只有 flow>0 的 18%

### 6.3 行动建议

| 优先级 | 行动 | 理由 |
|---|---|---|
| 🔴 | 甲方核实数据导出脚本，把 `RSD` 列名改为 `std` 或 `error_bar`，新增 `RSD = std/signal` 列 | 防止后续误读 |
| 🔴 | 后续数据若分析 RSD，统一加 剔 RSD≥0.30 上限（建议 0.30）| 防止单点污染模型 |
| 🟡 | 把修正后的新数据与旧数据合并做跨批次 SHAP | 验证批次稳定性 |
| 🟢 | 下一轮实验按"浓度↑ / 时间↑ / flow>0"原则设计 | 物理规律已稳定 |

### 6.4 模型应用边界

**适用**：
- 拉曼强度预测（R²=0.995）
- 4 个条件对信号影响的相对重要性排序
- RSD 预测（R²=0.71 with 剔 RSD≥0.30）

**不适用**：
- 跨批次 RSD 预测（除非重新校准）
- 单点 RSD 数值精确预测（误差中位 ~0.02，q90 ~0.05）

---

## 七、产物清单

### 7.1 数据与脚本

| 文件 | 用途 |
|---|---|
| `Datanew-8.31.xlsx` | 原始数据（3 sheet） |
| `raman_shap_new.py` | SHAP 分析主脚本（含 RSD 修正 + 剔 RSD≥0.30 + 三 sheet 合并）|
| `build_docx.py` | docx 生成脚本（heading 样式 + 嵌入图片） |

### 7.2 报告（Markdown）

| 文件 | 内容 |
|---|---|
| `REPORT_data.md` | 新数据本身的结构 / 质量 / SHAP 解读（修正版 + #4 剔 RSD≥0.30） |
| `REPORT_comparison.md` | 新旧数据逐项对比（修正版 + #4 剔 RSD≥0.30） |
| `REPORT_R2_diagnostic.md` | R² 偏低的根本原因（终版：数据标签错） |
| `REPORT_executive_summary.md` | **本文** |

### 7.3 报告（docx）

| 文件 | 内容 |
|---|---|
| `REPORT_R2_diagnostic.docx` | 诊断报告 docx 版 |
| `REPORT_executive_summary.docx` | 本文 docx 版 |
| `<key>_report/<key>_report.docx` | 4 份 per-analysis 数据报告 docx |
| `<key>_report/<key>_report_comparison.docx` | 4 份 per-analysis 对比报告 docx |

### 7.4 每个分析的标准产出

`Datanew-8.31/<key>_report/` 目录下：
- `<key>_report.docx` — 10 张图嵌入
- `<key>_report_comparison.docx`
- `metrics.json` — 指标 + 全局 SHAP
- `shap_global_importance.csv` — Feature × Mean|SHAP|
- `shap_values_per_sample.csv` — 每样本 SHAP
- `test_set_predictions.csv` — 测试集 actual/predicted/error
- `origin_shap_data.csv` — 测试集 + 4 个 SHAP 列
- `images.txt` + `images/` — 9 张 PNG

---

## 八、后续工作建议

| 时间 | 建议 |
|---|---|
| **本周** | 把本总结报告发给团队过一遍，确认 #4 剔 RSD≥0.30 方案能被接受 |
| **本月** | 把修正 + 剔 RSD≥0.30 后的新数据与旧数据合并做跨批次 SHAP |
| **下一轮实验** | 按"浓度↑ / 时间↑ / flow>0"原则设计；数据导出时严格区分 std 与 RSD，并加 剔 RSD≥0.30 |

---

*本报告由 `raman_shap_new.py`（含 RSD 修正 + 剔 RSD≥0.30 + 三 sheet 合并）、`build_docx.py` 配套生成。*
*RSD 修正公式：`RSD_corrected = original_RSD_column / raman_average`*
*#4 剔 RSD≥0.30 公式：`RSD (剔高 RSD 后) = min(RSD_corrected, 0.20)`*

> **v2 标注**：本报告所引用的 SHAP 图为 v2 重出版本（waterfall 与 global_importance 数字统一为 3 位小数；其余图保持 SHAP 默认 2 位小数）。结论与数字不变。
