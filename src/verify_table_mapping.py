"""
核对甲方表格与图表的对应关系：
  1. 表格是否就是 test set（205 行）
  2. beeswarm / dependence / interaction / waterfall 各自用的是哪批数据
  3. 交互图的着色到底是「原始特征值」还是「SHAP 值」—— 甲方图②色标是 0-5 / 0-160
"""
import io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(REPO_ROOT, ".mplcache"))
os.makedirs(os.environ["MPLCONFIGDIR"], exist_ok=True)

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split

BASE = os.environ.get("RAMAN_OUT",  os.path.join(REPO_ROOT, "reports", "Datanew-8.31"))
DATA = os.environ.get("RAMAN_DATA", os.path.join(REPO_ROOT, "data", "Datanew-8.31.xlsx"))
RENAME = {"laser":"laser_power","rate":"flow_rate","C":"concentration",
          "time":"acq_time","average":"raman_average","RSD":"rsd"}
FEATURES = ["laser_power","concentration","acq_time","flow_rate"]

df = pd.concat([pd.read_excel(DATA, sheet_name=s) for s in pd.ExcelFile(DATA).sheet_names],
               ignore_index=True).rename(columns=RENAME)
df["rsd"] = df["rsd"] / df["raman_average"]

# === 复现 1_avg_all 的 train/test split ===
X = df[FEATURES].values
y = df["raman_average"].values
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
print("="*78)
print("[1] 划分核对")
print("="*78)
print(f"  全部数据 n      = {len(df)}")
print(f"  train n         = {len(X_train)}")
print(f"  test  n         = {len(X_test)}   <- 甲方 Excel 的行数")
print(f"  205 / 1023      = {205/1023:.4f}  (test_size=0.2 → {int(1023*0.2)})")

# === 加载导出的 CSV ===
pred_csv = pd.read_csv(os.path.join(BASE, "1_avg_all_report", "test_set_predictions.csv"))
orig_csv = pd.read_csv(os.path.join(BASE, "1_avg_all_report", "origin_shap_data.csv"))
print(f"\n  test_set_predictions.csv 行数 = {len(pred_csv)}")
print(f"  origin_shap_data.csv     行数 = {len(orig_csv)}")
print(f"  origin 列 = {list(orig_csv.columns)}")

# === 重建模型 + SHAP（与脚本完全相同） ===
model = GradientBoostingRegressor(n_estimators=300, max_depth=5, learning_rate=0.05,
                                  subsample=0.8, random_state=42).fit(X_train, y_train)
explainer = shap.Explainer(model, X_train, feature_names=FEATURES,
                           feature_perturbation="tree_path_dependent")
sv = explainer(X_test)

print("\n" + "="*78)
print("[2] 逐列核对：CSV 里的值 vs 重新算出来的值")
print("="*78)
checks = [
    ("laser_power",  X_test[:, 0],  orig_csv["laser_power"].values),
    ("concentration",X_test[:, 1],  orig_csv["concentration"].values),
    ("acq_time",     X_test[:, 2],  orig_csv["acq_time"].values),
    ("flow_rate",    X_test[:, 3],  orig_csv["flow_rate"].values),
    ("actual",       y_test,        orig_csv["actual"].values),
    ("predicted",    model.predict(X_test), orig_csv["predicted"].values),
]
for name, mine, theirs in checks:
    ok = np.allclose(mine, theirs, rtol=1e-9, atol=1e-9)
    print(f"  {name:16s} match = {ok}")
    if not ok:
        print(f"      mine[:3]   = {mine[:3]}")
        print(f"      theirs[:3] = {theirs[:3]}")

shap_cols = {"laser_power":0, "concentration":1, "acq_time":2, "flow_rate":3}
for f, idx in shap_cols.items():
    col = f"SHAP_{f}"
    ok = np.allclose(sv.values[:, idx], orig_csv[col].values, rtol=1e-9, atol=1e-9)
    print(f"  {col:22s} match = {ok}")
    if not ok:
        print(f"      mine[:3]   = {sv.values[:3, idx]}")
        print(f"      theirs[:3] = {orig_csv[col].values[:3]}")

# === [3] 各图吃的是哪批数据 ===
print("\n" + "="*78)
print("[3] 各类图实际使用的数据范围")
print("="*78)
print(f"  beeswarm      : shap.plots.beeswarm(shap_values)         → {len(X_test)} 行（测试集）")
print(f"  dependence    : shap.plots.scatter(shap_values[:, i])    → {len(X_test)} 行（测试集）")
print(f"  interaction   : shap_values[:, i], color=shap_values[:, j] → {len(X_test)} 行（测试集）")
print(f"  waterfall     : shap_values[idx]                          → 3 个样本（测试集内）")
print(f"  parity plot   : ax.scatter(y_test, y_pred_test)          → {len(X_test)} 个点（测试集）")

# === [4] 交互图着色到底是 SHAP 值还是原始值？ ===
print("\n" + "="*78)
print("[4] 关键：交互图的着色（甲方图②色标是 0-5 / 0-160 的原始值）")
print("="*78)
i_flow, i_conc, i_time = 3, 1, 2
for nm, j in [("acq_time", i_time), ("concentration", i_conc), ("flow_rate", i_flow)]:
    raw = X_test[:, j]
    shapv = sv.values[:, j]
    print(f"  着色源 = shap_values[:, {nm}]")
    print(f"      若为 SHAP 值 → 范围 [{shapv.min():.4f}, {shapv.max():.4f}]")
    print(f"      若为原始值   → 范围 [{raw.min():.4f}, {raw.max():.4f}]")
    print(f"      甲方图②色标  → 0-5 (acq_time) / 0-160 (concentration)  ← 匹配【原始值】")

# === [5] beeswarm 的横轴范围能否由 SHAP 列复现 ===
print("\n" + "="*78)
print("[5] beeswarm 横轴范围 vs CSV 的 SHAP 列范围（子集 1）")
print("="*78)
for f, idx in shap_cols.items():
    col = orig_csv[f"SHAP_{f}"].values
    print(f"  SHAP_{f:16s} CSV 范围 [{col.min():9.2f}, {col.max():9.2f}]")
print(f"  （甲方图①横轴 -2000 ~ 4000，与 SHAP_concentration 的范围一致）")

# === [6] waterfall 的三个样本 ===
print("\n" + "="*78)
print("[6] waterfall 用的三个样本（low / medium / high actual）")
print("="*78)
sorted_idx = np.argsort(y_test)
for rank, idx in enumerate([sorted_idx[0], sorted_idx[len(sorted_idx)//2], sorted_idx[-1]]):
    lbl = ["low","medium","high"][rank]
    r = orig_csv.iloc[idx]
    print(f"  {lbl:7s} sample_index={int(r['sample_index']):4d}  "
          f"laser={int(r['laser_power']):3d} C={int(r['concentration']):3d} "
          f"t={r['acq_time']:4} flow={int(r['flow_rate']):5d}  actual={r['actual']:.3f}")
