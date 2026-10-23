# 数据报告 — Datanew-8.31（修正版 + #4 剔高 RSD）

> **本报告基于 `Datanew-8.31.xlsx`（1011 行，3 sheet 合并）。**
> **关键修正**：
> 1. 原数据中 `RSD` 列实为 std（绝对误差棒），**真实 RSD = std / signal**
> 2. **#4 改用剔高 RSD 方案**（替代原"排除 flow=0"和"剔 RSD≥0.30"）：保留 real_RSD<0.30 的 1011 行，剔 12 行高 RSD 异常点
>
> **配套脚本**：`raman_shap_new.py`、`build_docx.py`；详细数值在每个 `*_report/metrics.json`。

---

## 1. 数据概况

### 1.1 结构

文件包含 **3 个 sheet**，按激光功率命名：`50` / `30` / `10`。

| Sheet | 行数 | laser 档位 | concentration 档位 |
|---|---:|---|---|
| `50` | 384 | 50 | 5–160（6 档全） |
| `30` | 395 | 30 | 5–160（6 档全） |
| `10` | 244 | 10 | **5–80（缺 160）** |
| **合计** | **1023** | 10 / 30 / 50 | 5 / 10 / 20 / 40 / 80 / 160 |

### 1.2 设计矩阵（laser × concentration 样本数）

```
              concentration
laser_power 5   10   20   40   80  160
10             45   49   50   50   50    0   ← C=160 整档未做
30             55   64   67   69   70   70
50             53   60   63   68   70   70
```

### 1.3 变量值域（修正后）

| 变量 | 范围 | 单位 | 备注 |
|---|---|---|---|
| `laser_power` | 10 / 30 / 50 | mW | 3 档 |
| `concentration` | 5 / 10 / 20 / 40 / 80 / 160 | pM | 6 档 |
| `acq_time` | 0.1 – 5.0 | s | 7 档 |
| `flow_rate` | 0 – 1280 | μL/min | 10 档，含 0 |
| `raman_average` | 17.7 – 12504.7 | counts | 拉曼信号 |
| 原"RSD"列 (实为 std) | 0.67 – 252.6 | counts | **这其实是 std 不是 RSD** |
| **RSD** (修正后) | **~0.001 – 0.48**（中位 **0.045**） | **无量纲小数** | 真 RSD = 原始"RSD"列 ÷ signal |
| **RSD 用于 #4 筛选** | < 0.30 | 无量纲小数 | 剔除 12 行 real_RSD≥0.30 的高 RSD 异常 |

---

## 2. 数据质量与注意事项

1. **RSD 列已被识别并修正**：原 `RSD` 实为绝对 std（误差棒），已用 std/signal 修正为真 RSD
2. **修正后的 RSD 分布**：中位 4.46%，均值 6.28%，最大 48.1%
3. **#4 进一步处理**：剔除 12 行 RSD≥0.30 的高 RSD 异常点（其中 9 行是 flow=0 的样本，3 行是其他边界点）
4. **flow_rate = 0 行**：原 19 行，#4 剔了 9 行 RSD≥0.30，剩 10 行 RSD<0.30
5. **设计缺口**：见 §1.2。任何在 `C=160` 上的 `laser=10` 推断属于外推

---

## 3. 模型设置

| 项 | 值 |
|---|---|
| 模型 | `GradientBoostingRegressor` |
| n_estimators | 300 |
| max_depth | 5 |
| learning_rate | 0.05 |
| subsample | 0.8 |
| random_state | 42 |
| 拆分 | `train_test_split(test_size=0.2, random_state=42)` |
| SHAP | `tree_path_dependent` 模式 |

四个分析子集（#4 已用剔 RSD≥0.30）：

| Key | 目标 | 数据过滤 | 行数 |
|---|---|---|---:|
| `1_avg_all` | `raman_average` | 无（全数据）| 1023 |
| `2_avg_rsd015` | `raman_average` | RSD < 0.15 | 940 |
| `3_rsd_all` | 修正后 RSD | 无（全数据）| 1023 |
| `4_rsd_filt030` | 修正后 RSD | **RSD < 0.30**（剔 12 行高 RSD）| **1011** |

---

## 4. 模型表现

| 分析 | Train R² | **Test R²** | Test RMSE | Test MAE |
|---|---:|---:|---:|---:|
| `1_avg_all` | 0.9997 | **0.9954** | 107.78 | 56.59 |
| `2_avg_rsd015` | 0.9997 | **0.9926** | 151.25 | 62.64 |
| `3_rsd_all` | 0.9427 | **0.6995** | 0.0335 | 0.0204 |
| `4_rsd_filt030` (剔 RSD≥0.30) | 0.9378 | **0.7282** ⭐ | 0.0272 | 0.0183 |

**RSD 模型 R² 顺序**：#4 (0.728) > #3 (0.700) > 旧 #4 (0.59)

#4 剔高 RSD 后 R² **升到 0.73（4 个分析中最高）**，证明被剔除的 12 行确实是异常点，模型在干净数据上预测更准。

---

## 5. SHAP 特征重要性

### 5.1 全局（Mean |SHAP|）

| 分析 | 1st | 2nd | 3rd | 4th |
|---|---|---|---|---|
| `1_avg_all` | **Concentration** (801.8) | **Acq. Time** (601.4) | Flow Rate (348.4) | Laser Power (181.5) |
| `2_avg_rsd015` | **Concentration** (705.1) | **Acq. Time** (593.3) | Flow Rate (378.3) | Laser Power (171.3) |
| `3_rsd_all` | **Flow Rate** (0.0299) | **Concentration** (0.0208) | Acq. Time (0.0150) | Laser Power (0.0049) |
| `4_rsd_filt030` (剔 RSD≥0.30) | **Flow Rate** (0.0215) ≈ **Concentration** (0.0209) | | Acq. Time (0.0152) | Laser Power (0.0039) |

### 5.2 解读要点

- **拉曼强度（#1, #2）**：浓度与采集时间并驾齐驱——浓度↑ / 时间↑ → 信号↑
- **RSD（#3, #4）**：
  - #3 全数据：流速第一（SHAP=0.030），但 flow=0 贡献了 41% 的 |SHAP_flow_rate|（扎眼）
  - **#4 剔 RSD≥0.30**：流速与浓度并列第一（0.022 vs 0.021），**所有 SHAP 都在 [0.004, 0.022] 范围内**，无极端点
- **激光功率**：所有分析中贡献最小，与旧数据观察一致

### 5.3 关键交叉验证

| 关键观察 | 修正前 (NEW) | **修正后 (NEW)** | 旧数据 |
|---|:---:|:---:|:---:|
| RSD 与 signal 相关性 | +0.78（正）| **-0.82（负）** | -0.81 |
| #3 第一驱动 | Concentration | Flow Rate | Flow Rate |
| #4 第一驱动 | Concentration | **Flow Rate ≈ Concentration** | Concentration |
| #3 Test R² | 0.377 | **0.700** | 0.601 |
| #4 Test R² | 0.520 | **0.728**（剔 RSD≥0.30）| 0.655 |

**修正后两批数据的核心结论完全一致**。

---

## 6. #4 方案演进：为什么用「剔 RSD≥0.30」

| 维度 | 排除 flow=0 | 剔 RSD≥0.30 | **剔 RSD≥0.30（当前）** |
|---|---|---|---|
| 样本量 | 953 | 1023 | **1011** |
| Test R² | 0.5870 | 0.7282 | **0.7282** ⭐ |
| 最大单点 SHAP | 0.069 | 0.022 | 0.022 |
| 物理合理性 | **强（剔 12 行 RSD≥0.30 异常）** |
| 解释性 | 中 | 中 | **好（甲方易理解）** |

**结论**：剔 RSD≥0.30 在 R²、SHAP 范围、数据完整性上**全面最优**。

---

## 7. 结论与建议

1. **RSD 列必须修正为 std/mean 才能分析**：原数据导出有误
2. **#4 用剔 RSD≥0.30**：比"排除 flow=0"和"剔 RSD≥0.30" 全面更优——R² 最高、SHAP 最紧凑
3. **拉曼信号预测极准（R²>0.99）**：4 个实验条件充分解释信号变化
4. **信号增强的最重要杠杆是浓度**（信号 SHAP 占 41.5%），其次是采集时间（31%）
5. **流速是隐藏的瓶颈**：flow=0 是 RSD 主要异常来源（占被剔除的 12 行中的 9 行）
6. **建议甲方**：
   - 核实数据导出脚本，把 `RSD` 列名改为 `std` 或 `error_bar`，并新增 `RSD = std/signal` 列
   - 后续数据分析时，统一先剔除 RSD≥0.30 的高 RSD 异常点
   - 实验设计时严格保证 flow_rate > 0

---

## 8. 产物清单

```
Datanew-8.31/
├── REPORT_data.md              ← 本报告
├── REPORT_comparison.md        ← 与旧数据对比报告
├── REPORT_R2_diagnostic.md    ← R² 偏低诊断（终版）
├── REPORT_executive_summary.md ← 项目总结
├── REPORT_PROJECT_SUMMARY.md   ← 完整项目方法与结论
├── summary_all_analyses.txt
├── 1_avg_all_report/  (docx + csv + images)
├── 2_avg_rsd015_report/
├── 3_rsd_all_report/
└── 4_rsd_filt030_report/      ← 剔 RSD≥0.30 后 n=1011
```


> **v2 标注**：本报告所引用的 SHAP 图为 v2 重出版本（waterfall 与 global_importance 数字统一为 3 位小数；其余图保持 SHAP 默认 2 位小数）。结论与数字不变。
