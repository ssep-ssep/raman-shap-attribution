# -*- coding: utf-8 -*-
"""
SHAP Analysis — 新数据 Datanew-8.31
====================================
与 raman_shap.py 完全相同的画图逻辑（含 SHAP waterfall 默认 y 轴格式
"feature_value = feature_label"、默认 2 位小数、f(x)/E[f(X)] baseline 标签），
差异点：
  1. 输入：Datanew-8.31.xlsx，列名为简写 -> 重命名到旧 schema
  2. RSD 在新数据里按 std/mean 修正
  3. 输出目录：Datanew-8.31/ 子目录，避免覆盖旧报告
  4. 图表标题/汇总里标注 "新数据 8.31" 以便与旧报告区分
"""

import os
os.environ.setdefault("MPLCONFIGDIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), ".mplcache"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shap
import warnings
warnings.filterwarnings("ignore")
from sklearn.model_selection import train_test_split
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# ─────────────────────────────────────────────
# 仅对 waterfall 与 global bar 图启用 3 位小数
# SHAP 内部默认 %+0.02f（2 位小数），这里 monkey-patch 成 %.3f（不带 + 号）
# 作用范围：bar 标签 / waterfall bar 标签
# 不影响：y 轴 feature value（如 "0 = Flow Rate"）和 f(x)/E[f(X)] baseline 标签
#       （SHAP 内部用不同路径构造这些文本，不走 format_value）
# 不影响：dependence / interaction / beeswarm（其他图）
# ─────────────────────────────────────────────
import shap.utils
_orig_format_value = shap.utils.format_value
def _patched_format_value(s, format_spec=".3f", **kwargs):
    # 任何形如 .Xf 的格式都统一改成 .3f（不带 + 号）
    if isinstance(format_spec, str) and "f" in format_spec:
        format_spec = "%.3f"
    return _orig_format_value(s, format_spec, **kwargs)
shap.utils.format_value = _patched_format_value
import importlib
for _mod_name in ["shap.plots._bar", "shap.plots._waterfall"]:
    try:
        _m = importlib.import_module(_mod_name)
        if hasattr(_m, "format_value"):
            _m.format_value = _patched_format_value
    except Exception:
        pass

import matplotlib.ticker as mticker
def _force_bar_3decimals(fig):
    """global bar 图：x 轴 tick 统一 3 位小数（0 仍显示为 0）"""
    for _ax in fig.axes:
        try:
            _ax.xaxis.set_major_formatter(
                mticker.FuncFormatter(lambda x, _: "0" if x == 0 else f"{x:.3f}")
            )
        except Exception:
            pass

# ─────────────────────────────────────────────
# 配置
# ─────────────────────────────────────────────
# 路径全部相对于仓库根目录，可移植：
#   <repo>/src/raman_shap_analysis.py
#   <repo>/data/Datanew-8.31.xlsx        (输入)
#   <repo>/reports/Datanew-8.31/          (输出)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA_PATH  = os.environ.get("RAMAN_DATA", os.path.join(REPO_ROOT, "data", "Datanew-8.31.xlsx"))
OUT_ROOT   = os.environ.get("RAMAN_OUT",  os.path.join(REPO_ROOT, "reports", "Datanew-8.31"))

if not os.path.exists(DATA_PATH):
    raise SystemExit(
        "找不到输入数据: %s\n"
        "请把 Datanew-8.31.xlsx 放到 <repo>/data/，或设置环境变量 RAMAN_DATA。" % DATA_PATH
    )
os.makedirs(OUT_ROOT, exist_ok=True)

# 新数据 -> 旧 schema 重命名
RENAME = {
    "laser":    "laser_power",
    "rate":     "flow_rate",
    "C":        "concentration",
    "time":     "acq_time",
    "average":  "raman_average",
    "RSD":      "rsd",
}

FEATURES = ["laser_power", "concentration", "acq_time", "flow_rate"]
LABELS = {
    "laser_power":   "Laser Power (mW)",
    "concentration": "Concentration (pM)",
    "acq_time":      "Acquisition Time (s)",
    "flow_rate":     "Flow Rate (μL/min)",
}

# 修正：原 'RSD' 列实际是 std（误差棒），真实 RSD = std / signal
df_raw = pd.concat(
    [pd.read_excel(DATA_PATH, sheet_name=s) for s in pd.ExcelFile(DATA_PATH).sheet_names],
    ignore_index=True,
)
df = df_raw.rename(columns=RENAME)
df["rsd_original"] = df["rsd"].copy()
df["rsd"] = df["rsd"] / df["raman_average"]

# #4 剔高 RSD 极端点（RSD >= 0.30）
RSD_THRESHOLD_FILTER = 0.30
RSD_THRESHOLD = 0.15  # #2 筛选阈值（与旧数据 0.15 一致）

os.makedirs(OUT_ROOT, exist_ok=True)

subsets = {
    "1_avg_all":     df.copy(),
    "2_avg_rsd015":  df[df["rsd"] < RSD_THRESHOLD].copy(),
    "3_rsd_all":     df.copy(),
    "4_rsd_filt030": df[df["rsd"] < RSD_THRESHOLD_FILTER].copy(),
}
targets = {
    "1_avg_all":     "raman_average",
    "2_avg_rsd015":  "raman_average",
    "3_rsd_all":     "rsd",
    "4_rsd_filt030": "rsd",
}
target_labels = {
    "raman_average": "拉曼强度平均值 (Raman Intensity Average)",
    "rsd":           "相对标准差 (RSD, 无量纲小数 — 修正后)",
}
analysis_descriptions = {
    "1_avg_all":     "平均值 — 全数据（{n}行，新数据 8.31，三档 laser 已合并）",
    "2_avg_rsd015":  "平均值 — 筛选RSD<0.15（{n}行，新数据 8.31，修正后阈值）",
    "3_rsd_all":     "RSD  — 全数据（{n}行，新数据 8.31，RSD 已用 std/mean 修正）",
    "4_rsd_filt030": "RSD — 筛选剔除高RSD（{n}行，新数据 8.31，剔除 RSD>=0.30 的 12 行极端点）",
}
chart_titles = {
    "1_avg_all":     "Raman Average -- Full Data (New 8.31)",
    "2_avg_rsd015":  "Raman Average -- RSD<15% Filtered (New 8.31)",
    "3_rsd_all":     "RSD -- Full Data (New 8.31)",
    "4_rsd_filt030": "RSD -- Filtered RSD<0.30 (New 8.31)",
}

# ─────────────────────────────────────────────
# 训练模型 + SHAP 分析（画图逻辑与 raman_shap.py 完全一致）
# ─────────────────────────────────────────────

def analyze(name, target_col, df_sub, out_prefix):
    print(f"\n{'='*60}")
    print(f"Analyzing: {name} | target={target_col} | rows={len(df_sub)}")
    print(f"{'='*60}")

    X = df_sub[FEATURES].values
    y = df_sub[target_col].values

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = GradientBoostingRegressor(
        n_estimators=300, max_depth=5,
        learning_rate=0.05, subsample=0.8, random_state=42,
    )
    model.fit(X_train, y_train)

    y_pred_train = model.predict(X_train)
    y_pred_test  = model.predict(X_test)

    train_r2 = r2_score(y_train, y_pred_train)
    test_r2  = r2_score(y_test, y_pred_test)
    test_rmse= np.sqrt(mean_squared_error(y_test, y_pred_test))
    test_mae = mean_absolute_error(y_test, y_pred_test)

    print(f"  Train R2  : {train_r2:.4f}")
    print(f"  Test  R2  : {test_r2:.4f}")
    print(f"  Test  RMSE: {test_rmse:.4f}")
    print(f"  Test  MAE : {test_mae:.4f}")

    feature_labels = [LABELS[f] for f in FEATURES]
    explainer = shap.Explainer(
        model, X_train,
        feature_names=feature_labels,
        feature_perturbation="tree_path_dependent",
    )
    shap_values = explainer(X_test)

    def save(fig, fname):
        img_dir = os.path.join(OUT_ROOT, out_prefix + "_report", "images")
        os.makedirs(img_dir, exist_ok=True)
        fpath = os.path.join(img_dir, fname)
        fig.savefig(fpath, dpi=150, bbox_inches="tight")
        plt.close(fig)
        print(f"  Saved -> {fpath}")

    # 1. 全局重要性 bar
    fig, ax = plt.subplots(figsize=(10, 6))
    shap.plots.bar(shap_values, show=False, max_display=len(FEATURES))
    plt.title(f"SHAP Global Feature Importance — {chart_titles[name]}", fontsize=12)
    _force_bar_3decimals(fig)
    plt.tight_layout()
    save(fig, "shap_global_importance.png")

    # 2. Beeswarm
    fig, ax = plt.subplots(figsize=(10, 7))
    shap.plots.beeswarm(
        shap_values, show=False,
        max_display=len(FEATURES),
        order=shap_values.abs.mean(0).argsort[::-1],
    )
    plt.title(f"SHAP Summary (Beeswarm) — {chart_titles[name]}", fontsize=12)
    plt.tight_layout()
    save(fig, "shap_beeswarm.png")

    # 3. 每个特征的 dependence
    for i, (feat, label) in enumerate(zip(FEATURES, feature_labels)):
        fig, ax = plt.subplots(figsize=(8, 5))
        shap.plots.scatter(shap_values[:, i], show=False, ax=ax,
            title=f"SHAP Dependence: {label} — {chart_titles[name]}")
        plt.tight_layout()
        save(fig, f"shap_dependence_{feat}.png")

    # 4. 特征交互（所有 4 个特征的两两组合 = 6 对）
    from itertools import combinations
    for i, j in combinations(range(len(FEATURES)), 2):
        fig, ax = plt.subplots(figsize=(8, 5))
        shap.plots.scatter(
            shap_values[:, i], color=shap_values[:, j],
            show=False, ax=ax,
            title=f"SHAP Interaction: {feature_labels[i]} (colored by {feature_labels[j]}) — {chart_titles[name]}"
        )
        plt.tight_layout()
        fname = f"shap_interaction_{FEATURES[i]}_x_{FEATURES[j]}.png"
        save(fig, fname)

    # 5. 局部解释（与 raman_shap.py 完全相同：默认 y 轴 + 默认小数位 + f(x)/E[f(X)] baseline）
    sorted_idx = np.argsort(y_test)
    labels_ = ["low", "medium", "high"]
    for rank, idx in enumerate([
        sorted_idx[0], sorted_idx[len(sorted_idx)//2], sorted_idx[-1]
    ]):
        fig, ax = plt.subplots(figsize=(9, 4))
        shap.plots.waterfall(shap_values[idx], show=False, max_display=len(FEATURES))
        plt.title(
            f"Local Explanation -- {labels_[rank]} — {chart_titles[name]}\n"
            f"Predicted: {y_pred_test[idx]:.3f}  |  Actual: {y_test[idx]:.3f}",
            fontsize=11
        )
        plt.tight_layout()
        save(fig, f"shap_local_{labels_[rank]}.png")

    # 6. Parity Plot：Predicted vs Actual + y=x 参考线
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(y_test, y_pred_test, s=18, alpha=0.55, color="#1f77b4",
               edgecolors="white", linewidth=0.4, label="Test set samples")
    lo = float(min(y_test.min(), y_pred_test.min()))
    hi = float(max(y_test.max(), y_pred_test.max()))
    pad = (hi - lo) * 0.05
    ax.plot([lo - pad, hi + pad], [lo - pad, hi + pad],
            "r--", lw=1.4, label="Ideal prediction (y = x)")
    ax.set_xlabel("Actual")
    ax.set_ylabel("Predicted")
    ax.set_title(
        f"Parity Plot: Predicted vs Actual — {chart_titles[name]}\n"
        f"Test R² = {test_r2:.4f}  |  RMSE = {test_rmse:.4f}",
        fontsize=11
    )
    ax.legend(loc="upper left", framealpha=0.9, fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.set_xlim(lo - pad, hi + pad)
    ax.set_ylim(lo - pad, hi + pad)
    ax.set_aspect("equal", adjustable="datalim")
    plt.tight_layout()
    save(fig, "shap_parity_plot.png")

    # 数值汇总
    mean_abs = np.abs(shap_values.values).mean(axis=0)
    summary = pd.DataFrame({
        "Feature":     feature_labels,
        "Mean |SHAP|": mean_abs,
    }).sort_values("Mean |SHAP|", ascending=False)
    print("\n  SHAP Mean |Value|:")
    print(summary.to_string(index=False))

    # 保存数值
    report_dir = os.path.join(OUT_ROOT, out_prefix + "_report")
    os.makedirs(report_dir, exist_ok=True)

    metrics = {
        "analysis_name": name,
        "description": analysis_descriptions[name].format(n=len(df_sub)),
        "target": target_col,
        "target_label": target_labels[target_col],
        "n_samples": int(len(df_sub)),
        "features": FEATURES,
        "feature_labels": feature_labels,
        "model": "GradientBoostingRegressor",
        "model_params": {
            "n_estimators": 300, "max_depth": 5,
            "learning_rate": 0.05, "subsample": 0.8, "random_state": 42,
        },
        "rsd_threshold_percent": RSD_THRESHOLD,
        "metrics": {
            "train_r2": round(train_r2, 4),
            "test_r2":  round(test_r2, 4),
            "test_rmse": round(test_rmse, 4),
            "test_mae":  round(test_mae, 4),
        },
        "shap_global_importance": summary.to_dict(orient="records"),
        "feature_values_range": {
            f: {
                "min": float(df_sub[f].min()),
                "max": float(df_sub[f].max()),
                "mean": float(df_sub[f].mean()),
            } for f in FEATURES
        },
        "target_range": {
            "min": float(y.min()),
            "max": float(y.max()),
            "mean": float(y.mean()),
        },
    }
    with open(os.path.join(report_dir, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    summary.to_csv(os.path.join(report_dir, "shap_global_importance.csv"), index=False)

    pd.DataFrame(shap_values.values, columns=feature_labels).assign(
        sample_index=lambda d: d.index
    ).to_csv(os.path.join(report_dir, "shap_values_per_sample.csv"), index=False)

    test_df = pd.DataFrame({
        "sample_index": range(len(y_test)),
        **{f: X_test[:, i] for i, f in enumerate(FEATURES)},
        "actual": y_test,
        "predicted": y_pred_test,
        "error": y_pred_test - y_test,
    })
    test_df.to_csv(os.path.join(report_dir, "test_set_predictions.csv"), index=False)

    origin = test_df.copy()
    for i, (feat, lbl) in enumerate(zip(FEATURES, feature_labels)):
        origin[f"SHAP_{feat}"] = shap_values.values[:, i]
    origin.to_csv(os.path.join(report_dir, "origin_shap_data.csv"), index=False)

    # 图片清单
    img_list = [
        "shap_global_importance.png",
        "shap_beeswarm.png",
    ]
    for feat in FEATURES:
        img_list.append(f"shap_dependence_{feat}.png")
    for i, j in combinations(range(len(FEATURES)), 2):
        img_list.append(f"shap_interaction_{FEATURES[i]}_x_{FEATURES[j]}.png")
    for lbl in labels_:
        img_list.append(f"shap_local_{lbl}.png")
    img_list.append("shap_parity_plot.png")

    with open(os.path.join(report_dir, "images.txt"), "w", encoding="utf-8") as f:
        for img in img_list:
            f.write(img + "\n")

    print(f"\n  报告目录: {report_dir}")
    return summary, metrics


all_results = {}
all_metrics = {}
for key in ["1_avg_all", "2_avg_rsd015", "3_rsd_all", "4_rsd_filt030"]:
    summary, metrics = analyze(key, targets[key], subsets[key], key)
    all_results[key] = summary
    all_metrics[key] = metrics

# 汇总
summary_txt = os.path.join(OUT_ROOT, "summary_all_analyses.txt")
with open(summary_txt, "w", encoding="utf-8") as f:
    f.write("="*70 + "\n")
    f.write("SHAP分析汇总 — 新数据 Datanew-8.31\n")
    f.write(f"  共 {len(df)} 行（新数据 8.31，三档 laser 已合并）\n")
    f.write(f"  [修正说明] 原 'RSD' 列实际是 std (误差棒)，RSD 已用 std/mean 重新计算\n")
    f.write("="*70 + "\n\n")
    for key in ["1_avg_all", "2_avg_rsd015", "3_rsd_all", "4_rsd_filt030"]:
        m = all_metrics[key]
        f.write(f"\n[{key}]\n")
        f.write(f"  目标变量: {m['target']}\n")
        f.write(f"  数据量  : {m['n_samples']}\n")
        f.write(f"  模型 R² : Train={m['metrics']['train_r2']}  Test={m['metrics']['test_r2']}\n")
        f.write(f"  RMSE    : {m['metrics']['test_rmse']}\n")
        f.write(f"  MAE     : {m['metrics']['test_mae']}\n")
        f.write(f"  特征重要性排序:\n")
        for i, row in enumerate(m['shap_global_importance'], 1):
            f.write(f"    {i}. {row['Feature']}: {row['Mean |SHAP|']:.4f}\n")
    f.write(f"\n\n所有报告保存在 {OUT_ROOT}/ 子目录中\n")

print(f"\n汇总报告: {summary_txt}")
print("\n=== ALL DONE ===")
