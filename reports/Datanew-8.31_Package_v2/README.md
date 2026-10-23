# Datanew-8.31 SHAP 分析报告包 (v2)

本压缩包包含完整的拉曼实验新批次 SHAP 特征归因分析报告及配套数据。

> **v2 相对 v1 的差异**：waterfall 与 global_importance 图的数字统一为 3 位小数；其余图（beeswarm / dependence / interaction / parity）保持 SHAP 默认 2 位小数。所有 docx 重新生成，图片用更新后的版本。其他字段全部相同。

## 数据来源

- 原始数据：`Datanew-8.31.xlsx`（3 sheet：'50'/'30'/'10'，合并后 1023 行）
- 旧数据 `merged_data.xlsx`（1090 行）作为对照基准

## 关键修正

- 新数据原数据 `RSD` 列实为 std（绝对误差棒），已用 `std/signal` 修正为真 RSD
- 分析 #4 改用剔 RSD≥0.30 方案：保留 1011 行（剔 12 行高 RSD 异常点），Test R²=0.73

## 目录索引

| 目录 | 内容 | 优先阅读 |
|---|---|---|
| `01_ExecutiveSummary/` | 项目执行摘要（docx + md）| 甲方首选 |
| `02_ProjectSummary/` | 完整项目方法与结论（docx + md）| 完整版 |
| `03_DataReport/` | 新数据本身的结构与 SHAP 解读 | 数据角度 |
| `04_ComparisonReport/` | 新旧数据逐项对比 | 对比视角 |
| `05_R2Diagnostic/` | R²=0.52 偏低诊断（数据标签错）| 技术细节 |
| `06_PerAnalysisReports/` | 4 个 per-analysis 详细报告（每份含 16 张图）| 详细数据 |
| `07_Scripts/` | Python 分析脚本 | 复现用 |
| `08_RawData/` | 原始数据 xlsx | 数据源 |

## 4 个分析的核心数字

| # | 分析 | Test R² | SHAP 第一驱动 | 文件夹 |
|---|---|---:|---|---|
| 1 | avg_all（全数据 → 信号）| **0.9954** | Concentration (802) | `06_PerAnalysisReports/1_avg_all/` |
| 2 | avg_rsd015（低 RSD 子集 → 信号）| **0.9926** | Concentration (705) | `06_PerAnalysisReports/2_avg_rsd015/` |
| 3 | rsd_all（全数据 → RSD）| **0.6995** | Flow Rate (0.030) | `06_PerAnalysisReports/3_rsd_all/` |
| 4 | rsd_filt030（剔 RSD≥0.30 → RSD）| **0.7282** ⭐ | Flow Rate ≈ Concentration (0.021) | `06_PerAnalysisReports/4_rsd_filt030/` |

## 关键 takeaway（汇报可直接引用）

1. **"新数据 RSD 列被错标为 std，已用 std/signal 修正"** — 数据导出列名错误
2. **"#4 用剔 RSD≥0.30 替代排除 flow=0"** — R² 从 0.59 升到 0.73（4 个分析最高）
3. **"修正后两批数据 SHAP 排序一致"** — 同一物理规律
4. **"浓度是最强信号增强杠杆"**（SHAP 占 41.5%），其次是采集时间（31%）
5. **"实验设计必须保证 flow>0"** — flow=0 时 RSD 平均 22.5%（远高于 flow>0 的 3-7%）

## 关键公式

- 真实 RSD：`RSD_corrected = original_RSD_column / raman_average`
- #4 筛选：`subset = df[df["rsd"] < 0.30]`（剔 12 行高 RSD 异常）

## 复现方法

```bash
python 07_Scripts/raman_shap_new.py   # 重新生成 4 个分析
python 07_Scripts/build_docx.py        # 重新生成 8 份 docx
```

依赖包：numpy, pandas, scikit-learn, matplotlib, shap, python-docx

## 16 张图清单（每分析）

1 张全局重要性 + 1 张 beeswarm + 4 张单特征依赖 + 6 张两两交互 + 3 张局部 waterfall + 1 张 parity plot = 16 张图/分析
