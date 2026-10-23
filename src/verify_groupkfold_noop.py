"""
验证：在「每个参数组合只有 1 次测量」的数据上，GroupKFold 的分组到底起了什么作用？
如果分组是 no-op，那么 R² 的差异只来自「随机抽样不同」，而非「防泄露」。
"""
import io, os, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split, GroupShuffleSplit, KFold, GroupKFold
from sklearn.metrics import r2_score

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
DATA = os.environ.get("RAMAN_DATA", os.path.join(REPO_ROOT, "data", "Datanew-8.31.xlsx"))
RENAME = {"laser":"laser_power","rate":"flow_rate","C":"concentration",
          "time":"acq_time","average":"raman_average","RSD":"rsd"}
FEATURES = ["laser_power","concentration","acq_time","flow_rate"]

df = pd.concat([pd.read_excel(DATA, sheet_name=s) for s in pd.ExcelFile(DATA).sheet_names],
               ignore_index=True).rename(columns=RENAME)
df["rsd"] = df["rsd"] / df["raman_average"]
df["_g"] = (df["laser_power"].astype(str)+"_"+df["concentration"].astype(str)+"_"+
           df["acq_time"].astype(str)+"_"+df["flow_rate"].astype(str))

print("="*76)
print("步骤 1：分组变量是否有重复？（若有重复，分组才有意义）")
print("="*76)
vc = df["_g"].value_counts()
print(f"  总行数 n          = {len(df)}")
print(f"  唯一 group 数     = {df['_g'].nunique()}")
print(f"  每组样本数分布    = {vc.value_counts().to_dict()}")
print(f"  最大组内样本数    = {vc.max()}")
dup_groups = (vc > 1).sum()
print(f"  含 >1 样本的组数  = {dup_groups}")
if dup_groups == 0:
    print("\n  >>> 没有任何组含多条样本：GroupKFold 的分组约束在此数据上完全失效（no-op）")

X = df[FEATURES].values
y = df["raman_average"].values
groups = df["_g"].values

def make(seed):
    return GradientBoostingRegressor(
        n_estimators=300, max_depth=5, learning_rate=0.05,
        subsample=0.8, random_state=seed)

print("\n" + "="*76)
print("步骤 2：普通 train_test_split 跑 20 个种子")
print("="*76)
r2_random = []
for seed in range(20):
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=seed)
    r2_random.append(r2_score(yte, make(seed).fit(Xtr, ytr).predict(Xte)))
r2_random = np.array(r2_random)
print(f"  R² mean ± std = {r2_random.mean():.4f} ± {r2_random.std():.4f}")
print(f"  范围          = [{r2_random.min():.4f}, {r2_random.max():.4f}]")

print("\n" + "="*76)
print("步骤 3：GroupShuffleSplit 跑同样 20 个种子")
print("="*76)
r2_group = []
for seed in range(20):
    gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    tr, te = next(gss.split(X, y, groups=groups))
    r2_group.append(r2_score(y[te], make(seed).fit(X[tr], y[tr]).predict(X[te])))
r2_group = np.array(r2_group)
print(f"  R² mean ± std = {r2_group.mean():.4f} ± {r2_group.std():.4f}")
print(f"  范围          = [{r2_group.min():.4f}, {r2_group.max():.4f}]")

print("\n" + "="*76)
print("步骤 4：两者是否在统计上可区分？")
print("="*76)
print(f"  random 均值 = {r2_random.mean():.4f}")
print(f"  group  均值 = {r2_group.mean():.4f}")
print(f"  差值        = {r2_random.mean() - r2_group.mean():+.4f}")
# 双样本 t 检验（手工）
n1, n2 = len(r2_random), len(r2_group)
m1, m2 = r2_random.mean(), r2_group.mean()
s1, s2 = r2_random.std(ddof=1), r2_group.std(ddof=1)
se = np.sqrt(s1**2/n1 + s2**2/n2)
t = (m1 - m2) / se if se > 0 else float("nan")
print(f"  t = {t:.3f}  (|t| < 2.1 即无显著差异)")

# 重叠区间
lo = max(r2_random.min(), r2_group.min())
hi = min(r2_random.max(), r2_group.max())
print(f"  两者 R² 区间重叠 = [{lo:.4f}, {hi:.4f}]  重叠宽度 {hi-lo:.4f}")
if r2_random.min() <= r2_group.max() and r2_group.min() <= r2_random.max():
    print("  >>> 两种划分的 R² 取值范围相互重叠")

print("\n" + "="*76)
print("结论")
print("="*76)
if dup_groups == 0 and abs(t) < 2.1:
    print("  本数据上 GroupKFold 与普通随机划分【没有统计差异】。")
    print("  原因：每个参数组合仅 1 次测量，不存在「同条件重复测量跨集合」的可能，")
    print("        分组约束无从生效。0.995 与 0.981 的差异只是随机抽样波动。")
    print("  结论：R² 高是【数据的物理确定性】所致，与交叉验证方法无关。")
