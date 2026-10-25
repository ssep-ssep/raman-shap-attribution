# Raman / SERS SHAP Attribution Workflow

可解释性归因分析工作流：从拉曼/SERS 实验数据出发，用梯度提升回归建模，再用 SHAP 拆解「哪个参数在起作用、往哪个方向起、有没有交互」。

本仓库只包含**数据分析部分**：可复现代码与一份**合成验证数据集**（不含任何真实实验数据）。
报告生成、docx 排版与汇报材料不在本仓库范围内。

---

## 快速开始

```bash
git clone https://github.com/ssep-ssep/raman-shap-attribution.git
cd raman-shap-workflow
pip install -r requirements.txt

# 0. 生成合成数据集（可选，仓库里已带一份）
python src/generate_synthetic_data.py --out data/Datanew-8.31.xlsx

# 1. 跑 4 个分析子集，产出图 + 指标 + CSV（输出到 reports/Datanew-8.31/）
python src/raman_shap_analysis.py

```

路径全部相对于仓库根目录，也可通过环境变量覆盖：

| 变量 | 默认值 | 说明 |
|---|---|---|
| `RAMAN_DATA` | `data/Datanew-8.31.xlsx` | 输入数据 |
| `RAMAN_OUT`  | `reports/Datanew-8.31` | 分析输出目录 |
| `RAMAN_OLD`  | `src/OLD_data` | 上一轮 metrics（用于对比报告） |

---

## 数据

> ⚠️ **本仓库不含任何真实实验数据。** `data/Datanew-8.31.xlsx` 是由
> `src/generate_synthetic_data.py` 生成的**合成数据集**，仅用于让读者完整跑通流水线。

```bash
python src/generate_synthetic_data.py --out data/Datanew-8.31.xlsx
```

合成数据保持与真实数据**完全相同的结构**：

- 3 个 sheet（laser = 10 / 30 / 50 mW），每 sheet 341 行，合计 1023 行
- 相同的列名与列顺序：`laser, C, time, rate, average, RSD`
- 相同的参数档位：

| 列 | 含义 | 单位 | 档位 |
|---|---|---|---|
| `laser` | 激光功率 | mW | 10 / 30 / 50 |
| `C` | 浓度 | pM | 5 / 10 / 20 / 40 / 80 / 160 |
| `time` | 采集时间 | s | 0.1 / 0.3 / 1 / 2 / 3 / 4 / 5 |
| `rate` | 流速 | μL/min | 0 / 40 / 80 / 320 / 640 / 1280 |
| `average` | 拉曼信号强度 | counts | 连续 |
| `RSD` | ⚠️ 实际是**标准差**，不是相对标准差 | — | 连续 |

- 物理上说得通的响应面：信号强度随 浓度↑ / 时间↑ / 流速↑ 单调上升，
  高浓度+低流速区出现饱和与轻微抑制，激光功率贡献很弱；噪声留有真实比例的
  不可解释成分（R² ≈ 0.95），不会像真实数据那样 R²≈0.995 显得"过于完美"。

> **数据陷阱（与真实数据相同）**：`RSD` 列保存的是重复计数的**标准差**，
> 不是相对标准差。脚本统一用 `rsd_corrected = RSD / average` 修正为无量纲小数。
> 所有以 RSD 为目标的分析都建立在这个修正之上。

---

## 四个分析子集

| Key | 目标变量 | 筛选 | n |
|---|---|---|---:|
| `1_avg_all` | 信号强度 | 全数据 | 1023 |
| `2_avg_rsd015` | 信号强度 | rsd < 0.15（低噪子集）| 940 |
| `3_rsd_all` | RSD | 全数据 | 1023 |
| `4_rsd_filt030` | RSD | rsd < 0.30（剔高 RSD 异常）| 1011 |

---

## 方法要点

- **模型**：`GradientBoostingRegressor(n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8, random_state=42)`，四个子集配置统一。
- **划分**：`train_test_split(test_size=0.2, random_state=42)` → 818 训练 / 205 测试。
- **SHAP**：`TreeSHAP`（`feature_perturbation="tree_path_dependent"`），产出 bar / beeswarm / dependence / interaction / waterfall 五类图。
- **所有 SHAP 图与 Parity Plot 都基于 205 条测试集**，即模型未见过的样本。

### 已验证的两个关键结论

**1. 高 R² 来自数据的物理确定性，不是数据泄露。**

本数据集 1023 行对应 **1023 个唯一参数组合**（每组仅 1 次测量），因此按四元组分组的 `GroupKFold` 在此数据上是 no-op：普通随机划分与分组划分在 20 个随机种子下无统计差异（R² = 0.9936 ± 0.0027 vs 0.9939 ± 0.0037，t = −0.25）。

复现：`python src/verify_groupkfold_noop.py`

**2. 表格与图表的对应关系可逐列验证。**

`origin_shap_data.csv`（205 行 × 12 列）完整支撑全部图表：

| 表列 | 支撑的图 |
|---|---|
| `sample_index` | 样本索引 |
| `laser_power` / `concentration` / `acq_time` / `flow_rate` | 所有图的横轴与色标 |
| `actual` / `predicted` | Parity Plot |
| `SHAP_*`（4 列）| Beeswarm、Dependence、Interaction、Waterfall |

复现：`python src/verify_table_mapping.py`（会重新训练并逐列断言 `match = True`）

---

## 目录结构

```
├── src/
│   ├── raman_shap_analysis.py     # 主分析：训练 + SHAP + 出图 + 指标导出
│   ├── build_docx.py              # 由 metrics.json 生成 docx 报告
│   ├── generate_synthetic_data.py  # 生成合成验证数据集（无真实数据）
│   ├── verify_groupkfold_noop.py  # 验证分组划分在本数据上是否有效
│   └── verify_table_mapping.py    # 验证表格列与图表的对应关系
├── data/
│   └── Datanew-8.31.xlsx          # 合成测试数据包（1023 行）
├── LICENSE                        # MIT
├── .gitattributes
└── .gitignore
```

---

## 运行环境

Python 3.14.6 · scikit-learn 1.9.0 · SHAP 0.52.0 · numpy 2.5.2 · pandas 3.0.5 · matplotlib 3.11.1

（脚本本身兼容较旧版本；`format_value` 的 monkey-patch 依赖 SHAP ≥ 0.39）

---

## 引用

若使用本工作流或其中的分析结果，请引用：

- Pedregosa, F., et al. *Scikit-learn: Machine Learning in Python.* J. Mach. Learn. Res. **12**, 2825–2830 (2011).
- Lundberg, S. M. & Lee, S.-I. *A Unified Approach to Interpreting Model Predictions.* Adv. Neural Inf. Process. Syst. **30**, 4765–4774 (2017).
- Lundberg, S. M., et al. *From local explanations to global understanding with explainable AI for trees.* Nat. Mach. Intell. **2**, 56–67 (2020).
