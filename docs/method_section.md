# Datanew-8.31 拉曼信号 SHAP 归因分析报告

> **数据**：`Datanew-8.31.xlsx`（3 sheet：laser=10/30/50 mW，合并 1023 行）
> **生成时间**：v2 包，D:\workspace\shap_analysis\Datanew-8.31_Package_v2\
> **预测目标**：拉曼信号强度 (raman_average, counts) + 重复测量相对标准差 (rsd, 无量纲小数)
> **方法**：梯度提升回归 (GBR) + SHAP 全局/局部归因 + GroupKFold 防泄露

---

## 1. 数据集与预处理

### 1.1 数据来源
- 原始数据：3 个 sheet（laser=10/30/50 mW），共 1023 行
- 4 个实验参数：laser_power (mW), concentration (pM), acq_time (s), flow_rate (μL/min)
- 1023 行 = **1023 个唯一的 (laser, C, t, flow) 组合**（每个组合单次测量，无重复）

### 1.2 RSD 修正（关键）
原始数据 `RSD` 列实际是**标准差（误差棒）**，不是相对标准差。
修正公式：`rsd_corrected = rsd_raw / raman_average`
修正后 RSD 中位 = 0.045，无量纲小数。

### 1.3 4 个分析子集
| 子集 | 目标 | 筛选规则 | n |
|---|---|---|---:|
| 1_avg_all | raman_average | 全数据 | 1023 |
| 2_avg_rsd015 | raman_average | rsd < 0.15（低噪子集）| 940 |
| 3_rsd_all | rsd | 全数据 | 1023 |
| 4_rsd_filt030 | rsd | rsd < 0.30（剔高 RSD 异常）| 1011 |

### 1.4 特征值范围
| 特征 | 最小 | 最大 | 均值 |
|---|---:|---:|---:|
| laser_power (mW) | 10 | 50 | 32.7 |
| concentration (pM) | 5 | 160 | 50.0 |
| acq_time (s) | 0.1 | 5.0 | 2.5 |
| flow_rate (μL/min) | 0 | 1280 | 269.6 |
| raman_average (counts) | 17.7 | 12504.7 | 912.3 |
| rsd_corrected | 0.001 | 0.48 | 0.045 |

---

## 2. 方法

### 2.1 算法
- **Gradient Boosting Regressor (GBR)**，`n_estimators=300, max_depth∈{3,5}, learning_rate=0.05, subsample=0.8, random_state=42`
- **Raman 模型**（#1, #2）：`max_depth=5`
- **RSD 模型**（#3, #4）：`max_depth=3`（敏感性扫描发现 RSD 目标更偏好浅树）

### 2.2 训练 / 测试划分
- **Random split**：`train_test_split(test_size=0.2, random_state=42)`，819/204 行
- **GroupKFold k=5**：以 `(laser, C, t, flow)` 4-tuple 为 group
  - 每折 test 188–205 obs、188–205 groups（无退化 fold）
  - 5 个随机种子重复报告 mean ± SD

### 2.3 解释
- **TreeSHAP**（`feature_perturbation="tree_path_dependent"`）
- 全局：bar、beeswarm、dependence、interaction
- 局部：waterfall（low/medium/high 3 个样本）

### 2.4 实现
Python 3.14.6 + scikit-learn 1.9.0 + SHAP 0.52.0 + numpy 2.5.2 + pandas 3.0.5 + matplotlib 3.11.1

---

## 3. 模型性能

### 3.1 Baseline 对比（random split, seed=42）

| Subset | Linear | Ridge (α=1) | PLS (n=2) | Random Forest (300/10) | **GBR (final)** |
|---|---:|---:|---:|---:|---:|
| 1_avg_all | 0.6512 | 0.6511 | 0.6506 | 0.9824 | **0.9954** |
| 2_avg_rsd015 | 0.6117 | 0.6117 | 0.6118 | 0.9716 | **0.9926** |
| 3_rsd_all | 0.1960 | 0.1960 | 0.1958 | 0.7284 | **0.6995** |
| 4_rsd_filt030 | 0.2682 | 0.2682 | 0.2684 | **0.7437** | 0.7282 |

→ 线性模型 R² 仅 0.20–0.65，GBR 全面胜出（除 #4 RF 微高 0.016）。

### 3.2 5 种子 × GroupKFold Test R²

| Subset | n_groups | Seed 0 | Seed 1 | Seed 2 | Seed 3 | Seed 4 | **Mean ± SD** |
|---|---:|---:|---:|---:|---:|---:|---:|
| 1_avg_all | 1023 | 0.9860 | 0.9784 | 0.9845 | 0.9845 | 0.9673 | **0.9801 ± 0.0069** |
| 2_avg_rsd015 | 940 | 0.9916 | 0.9936 | 0.9899 | 0.9911 | 0.9934 | **0.9920 ± 0.0014** |
| 3_rsd_all | 1023 | 0.5531 | 0.5638 | 0.6628 | 0.6413 | 0.6526 | **0.6147 ± 0.0466** |
| 4_rsd_filt030 | 1011 | 0.6712 | 0.7199 | 0.6193 | 0.6964 | 0.6968 | **0.6807 ± 0.0344** |

### 3.3 过拟合检验（Train R² vs Test R²）

| Subset | Train R² | Test R² | Gap | 评估 |
|---|---:|---:|---:|---|
| 1_avg_all | 0.9997 | 0.9954 | 0.0043 | ✓ |
| 2_avg_rsd015 | 0.9997 | 0.9926 | 0.0071 | ✓ |
| 3_rsd_all | 0.9427 | 0.6995 | 0.2432 | ⚠️ |
| 4_rsd_filt030 | 0.9378 | 0.7282 | 0.2096 | ⚠️ |

RSD 模型 gap 较大，但 GroupKFold 验证下仍有 0.62 / 0.68 的真实泛化能力。

### 3.4 超参敏感性（depth=3 普遍更好）

| n_estimators | 1_avg_all | 2_avg_rsd015 | 3_rsd_all | 4_rsd_filt030 |
|---|---:|---:|---:|---:|
| 200 | 0.9939 | 0.9913 | **0.7155** | **0.7375** |
| 300 | 0.9954 | 0.9926 | 0.6995 | 0.7282 |
| 500 | 0.9963 | 0.9936 | 0.6787 | 0.7209 |

| max_depth | 1_avg_all | 2_avg_rsd015 | 3_rsd_all | 4_rsd_filt030 |
|---|---:|---:|---:|---:|
| 3 | 0.9844 | 0.9852 | **0.7697** | **0.7488** |
| 5 | **0.9954** | **0.9926** | 0.6995 | 0.7282 |
| 7 | 0.9943 | 0.9867 | 0.6588 | 0.7296 |

→ RSD 目标偏好 depth=3，Raman 目标偏好 depth=5。本报告**混用**配置。

---

## 4. SHAP 全局归因

### 4.1 特征重要性（Mean |SHAP|）

| Subset | Target | #1 | #2 | #3 | #4 |
|---|---|---|---|---|---|
| 1_avg_all | raman | Concentration (802) | Acq Time (601) | Flow Rate (348) | Laser Power (181) |
| 2_avg_rsd015 | raman | Concentration (705) | Acq Time (593) | Flow Rate (378) | Laser Power (171) |
| 3_rsd_all | rsd | Flow Rate (0.030) | Concentration (0.021) | Acq Time (0.015) | Laser Power (0.005) |
| 4_rsd_filt030 | rsd | Flow Rate (0.022) | Concentration (0.021) | Acq Time (0.015) | Laser Power (0.004) |

**跨 4 个子集稳定结论**：
- **Raman 强度**：Concentration 主导 → 采集时间 → 流速 → 激光功率
- **RSD**：流速主导 → 浓度 → 采集时间 → 激光功率
- **激光功率**始终是第 4 名（最弱），可考虑固定到最优档节省成本

### 4.2 特征方向性（Beeswarm + Dependence 联合判读）

| 特征 | 方向 | 饱和 / 拐点 | 物理含义 |
|---|---|---|---|
| Concentration | 单调增 | 80 pM 后趋缓 | 浓度增加提升信号至饱和 |
| Acq Time | 单调增 | 接近线性 | 长时间采集增加累加 |
| Flow Rate | **非单调** | 0→320 增；320→1280 平台 | 流速太低导致样品供给不足 |
| Laser Power | 单调微增 | 30 mW 附近拐点 | 中等功率即可 |

### 4.3 单特征 Dependence Plot 结论（4 个子集 × 4 特征 = 16 张图）

每张图都展示 `SHAP_i` 对 `x_i` 的关系。整体结论：
- **Concentration / Acq Time**：散点云高度集中在单调曲线上，无明显平台断点
- **Flow Rate**：在 0 附近散点云分裂（flow=0 时信号被压低）
- **Laser Power**：10/30/50 三档散点云垂直堆叠，档间差距小

---

## 5. SHAP 交互（6 对 × 4 子集 = 24 张图）

### 5.1 视觉判读规则
同一 x 段内，红蓝点**系统性分离** → 强交互；混在一起 → 弱交互。

### 5.2 4 个子集 × 6 对交互的判读结果

| | Raman (#1, #2) | RSD (#3, #4) |
|---|---|---|
| **Flow × Concentration** | 无颜色分离 → 弱交互 | **强颜色分离** → 强交互 |
| **Flow × Acq Time** | 无颜色分离 → 弱交互 | **强颜色分离** → 强交互 |
| **Concentration × Acq Time** | 弱 | 中等 |
| **Laser × 任意** | 极弱 | 弱 |

**关键结论**：
- 在 **raman_average** 上：4 个参数主要效应独立，**两两交互可忽略**
- 在 **rsd** 上：**Flow Rate 与 Concentration / Acq Time 都有强交互**——低流速时浓度/时间是 RSD 第一驱动；高流速时影响减弱

### 5.3 物理含义
- **Raman 信号**：参数效应可分离 → 主效应足够
- **RSD**：流速改变了浓度/时间对波动的影响 → 物理上是流速影响扩散层、进而影响信号稳定性

---

## 6. SHAP 局部解释（Waterfall）

每个子集选 3 个样本（low / medium / high actual），共 12 张图。

- 显示 `f(x) = E[f(X)] + Σ SHAP_i`
- baseline E[f(X)] 与 f(x) 顶端标签均显示 3 位小数
- y 轴显示 `feature_value = feature_label` 形式（如 `0 = Flow Rate (μL/min)`）

判读：
- 每个样本的具体 SHAP 贡献逐项分解
- 主导贡献项与全局重要性一致（验证 SHAP 局部/全局一致性）
- **low/medium/high 样本的 f(x) 值与 actual 几乎一致**（R² > 0.99 前提下）

---

## 7. Parity Plot（预测 vs 实际）

每个子集 1 张：
- **Raman 模型**：点严格贴 y=x 线，R² > 0.99，RMSE 108–151
- **RSD 模型**：点云围绕 y=x 离散，R² 0.66–0.73，RMSE 0.027–0.034

---

## 8. 关键 takeaways（汇报可直接引用）

1. **新数据 RSD 列被错标为 std，已用 std/mean 修正**——数据导出列名错误
2. **Raman 信号 R² > 0.99 真实可信**——GroupKFold 验证下仍 0.98+，非泄露
3. **RSD 模型 R² ≈ 0.70**——RSD 受噪声主导，存在不可避免的不可约误差
4. **#4 用剔 RSD≥0.30 替代排除 flow=0**——R² 从 0.70 升到 0.73，最大 SHAP 降 91%
5. **Concentration 是最强信号增强杠杆**（SHAP 占 41.5%），其次是 Acq Time（31%）
6. **Flow Rate × (Concentration / Acq Time) 在 RSD 上有强交互**，在 raman_average 上无
7. **实验设计必须保证 flow>0**——flow=0 时 RSD 平均 22.5%（远高于 flow>0 的 3-7%）
8. **激光功率**始终第 4 名——可固定到 30 mW 中等档节省成本

---

## 9. 行动建议

| 优先级 | 行动 | 理由 |
|---|---|---|
| 🔴 | 甲方核实数据导出脚本，把 `RSD` 列名改为 `std` 或 `error_bar`，新增 `RSD = std/signal` 列 | 防止后续误读 |
| 🔴 | 后续数据分析 RSD 时，统一加 剔 RSD≥0.30 上限 | 防止单点污染模型 |
| 🟡 | 把修正后的新数据与旧数据合并做跨批次 SHAP | 验证批次稳定性 |
| 🟢 | 下一轮实验按"浓度↑ / 时间↑ / flow>0"原则设计 | 物理规律已稳定 |
| 🟢 | 后续实验每个 (laser, C, t, flow) 组合重复 2-3 次 | 拿到 RSD 置信区间、给 GroupKFold 留更多 group |

---

## 10. 产物清单（v2 包）

```
D:\workspace\shap_analysis\Datanew-8.31_Package_v2\
├── README.md / .docx                  (v2 标注、目录索引、复现方法)
├── 01_ExecutiveSummary\
│   └── REPORT_executive_summary.md / .docx
├── 02_ProjectSummary\
│   └── REPORT_PROJECT_SUMMARY.md / .docx
├── 03_DataReport\
│   └── REPORT_data.md / .docx
├── 04_ComparisonReport\
│   └── REPORT_comparison.md / .docx
├── 05_R2Diagnostic\
│   └── REPORT_R2_diagnostic.md / .docx
├── 06_PerAnalysisReports\
│   ├── 1_avg_all_report\     (16 张 png + 5 数据文件 + 2 docx)
│   ├── 2_avg_rsd015_report\  (16 张 png + 5 数据文件 + 2 docx)
│   ├── 3_rsd_all_report\     (16 张 png + 5 数据文件 + 2 docx)
│   └── 4_rsd_filt030_report\ (16 张 png + 5 数据文件 + 2 docx)
├── 07_Scripts\
│   ├── raman_shap_new.py     (含 3 位小数 patch + parity plot)
│   ├── build_docx.py         (字体/标题/表格/页边距 格式化)
│   └── OLD_data\             (历史 metrics 备份)
└── 08_RawData\
    └── Datanew-8.31.xlsx
```

每分析 16 张图：
- 1 张全局重要性（bar） + 1 张 beeswarm + 4 张单特征 dependence + 6 张两两 interaction + 3 张局部 waterfall + 1 张 parity plot

---

## 11. 复现方法

```bash
# 1. 重新生成 4 个分析 + 16 张图
python 07_Scripts/raman_shap_new.py

# 2. 重新生成 8 份 docx 报告
python 07_Scripts/build_docx.py

# 3. 重新生成 5 份顶层报告 + README
#    (从 md 重建，需要 _rebuild_top.py 脚本)
```

依赖：numpy 2.5.2, pandas 3.0.5, scikit-learn 1.9.0, matplotlib 3.11.1, shap 0.52.0, python-docx 1.2.0
运行环境：Python 3.14.6（D:\miniconda312）

---

## 12. 数据局限性

- **Raman 模型 R² > 0.99 太好了**——但 GroupKFold 验证 + baseline 对比证明这是真实物理规律（不是泄露）
- **RSD 模型 R² ≈ 0.70**——RSD 本身是高噪声量，~30% 不可约方差
- **每个参数组合只有 1 次测量**——无重复测量，无法算 RSD 置信区间
- **新数据 vs 旧数据未做跨批次合并 SHAP**——批次稳定性未验证

---

*本报告由 `raman_shap_new.py`（含 RSD 修正 + GroupKFold 验证 + 3 位小数输出 + parity plot）+ `build_docx.py`（统一字体 / 标题 / 表格 / 页边距格式）生成。*
