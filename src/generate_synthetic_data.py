"""
生成与 Datanew-8.31.xlsx **同格式**的合成验证数据集。

用途：让公开仓库的读者能完整跑通整条流水线，而无需接触真实实验数据。

设计要点
--------
1. 同样的 3 个 sheet（laser = 10 / 30 / 50 mW）与同样的列名/列顺序
   （laser, C, time, rate, average, RSD）。
2. 同样的参数档位：
   laser  ∈ {10, 30, 50} mW
   C      ∈ {5, 10, 20, 40, 80, 160} pM
   time   ∈ {0.1, 0.3, 1, 2, 3, 4, 5} s
   rate   ∈ {0, 40, 80, 320, 640, 1280} μL/min
3. 物理上说得通的响应：信号强度随 浓度↑ / 时间↑ / 流速↑ 单调上升，
   在高浓度+低流速区出现饱和与轻微抑制，激光功率贡献很弱。
4. 噪声水平刻意留出真实的不可解释成分（R² 落在 0.90–0.98 区间），
   让合成数据不会像真实数据那样 R²≈0.995 而给读者「过于完美」的错觉。
5. RSD 列同样保存的是**标准差**（不是相对标准差），以复现真实数据里
   那个必须先修正的数据陷阱。

用法
----
    python src/generate_synthetic_data.py --out data/Datanew-8.31.xlsx
    python src/generate_synthetic_data.py --out data/Datanew-8.31.xlsx --seed 20260909
"""
import argparse
import os

import numpy as np
import pandas as pd

LASERS = [10, 30, 50]
CONCS = [5, 10, 20, 40, 80, 160]
TIMES = [0.1, 0.3, 1, 2, 3, 4, 5]
RATES = [0, 40, 80, 320, 640, 1280]

N_ROWS_PER_LASER = 341  # 合计 1023 行，与真实数据集规模一致


def synth_response(laser, conc, t, rate, rng):
    """合成的"拉曼信号强度"响应面（counts 量级）。"""
    c = np.asarray(conc, dtype=float)
    tt = np.asarray(t, dtype=float)
    fl = np.asarray(rate, dtype=float)
    lp = np.asarray(laser, dtype=float)

    # 浓度：次线性 + 80 pM 附近饱和（真实数据中浓度是第一驱动因子）
    f_c = 62.0 * np.power(c, 0.72) * (1.0 / (1.0 + c / 220.0))

    # 采集时间：近似线性累积（第二驱动因子）
    f_t = 520.0 * tt

    # 流速：0 附近急剧上升，320 之后饱和（第三驱动因子，贡献小于浓度与时间）
    f_f = 190.0 * np.log1p(fl / 45.0)
    crowding = (1.0 - 0.35 * np.tanh((c - 60.0) / 60.0) * np.tanh((45.0 - fl) / 60.0))

    # 激光功率：贡献很弱，30 mW 附近略有拐点（始终排第 4）
    f_l = 22.0 * np.sqrt(lp) * (0.92 + 0.08 * (lp / 50.0))

    base = (f_c * crowding + f_t * (0.55 + 0.45 * f_c / (f_c + 1200.0)) + f_f + f_l) * 1.0
    base = np.clip(base, 8.0, None)

    # 乘性噪声 + 加性噪声
    noise = rng.normal(1.0, 0.075, size=base.shape)
    signal = base * noise + rng.normal(0.0, 40.0, size=base.shape)
    return np.clip(signal, 5.0, None)


def synth_rsd(signal, flow_rate, conc, rng):
    """
    合成的重复测量标准差（counts 量级）：
    相对标准差 RSD_std/signal 随信号增大而下降，并保留一部分**可被参数解释**的成分
    （例如低流速时相对波动更大），使 RSD 目标也能被模型部分解释。
    数值落在 0.02 – 0.35 区间，以便 rsd<0.15 / rsd<0.30 两个阈值都能切出不同子集。
    """
    rel = 0.30 / (1.0 + np.power(signal / 250.0, 0.45)) + 0.02
    rel = np.clip(rel, 0.02, 0.35)
    # 低流速 / 高浓度 → 相对波动更大（与真实实验的"流速不足导致不稳定"一致）
    strain = 1.0 + 0.55 * np.tanh((45.0 - flow_rate) / 60.0) * np.tanh((conc - 60.0) / 60.0)
    rel = np.clip(rel * strain, 0.02, 0.45)
    return np.clip(signal * rel * rng.normal(1.0, 0.18, size=signal.shape), 1e-4, None)


def build(seed=20260909, rows_per_laser=N_ROWS_PER_LASER):
    rng = np.random.default_rng(seed)

    # 构造参数组合：优先覆盖高流速与高浓度（与真实数据设计意图一致）
    combos = []
    for lp in LASERS:
        pool = [(lp, c, t, r)
                for c in CONCS for t in TIMES for r in RATES]
        # 去掉 (10mW, 160pM) 这一档，与真实数据一致
        pool = [x for x in pool if not (x[0] == 10 and x[1] == 160)]
        # 组合数可能少于目标行数：此时重复采样（不同行=不同重复测量）
        need = rows_per_laser
        if len(pool) >= need:
            idx = rng.permutation(len(pool))[:need]
            combos.extend(pool[i] for i in idx)
        else:
            combos.extend(pool[i] for i in rng.integers(0, len(pool), size=need))

    laser = np.array([x[0] for x in combos], dtype=float)
    conc = np.array([x[1] for x in combos], dtype=float)
    t = np.array([x[2] for x in combos], dtype=float)
    rate = np.array([x[3] for x in combos], dtype=float)

    average = synth_response(laser, conc, t, rate, rng)
    rsd_std = synth_rsd(average, rate, conc, rng)

    frames = []
    for lp in LASERS:
        m = laser == lp
        # 按 (C, time, rate) 排序，让每个 sheet 读起来跟真实数据一样有序
        order = np.lexsort((rate[m], t[m], conc[m]))
        sl = slice(None)
        s_laser, s_c, s_t, s_r = laser[m][order], conc[m][order], t[m][order], rate[m][order]
        s_avg, s_rsd = average[m][order], rsd_std[m][order]
        frames.append(pd.DataFrame({
            "laser": s_laser,
            "C": s_c,
            "time": s_t,
            "rate": s_r,
            "average": s_avg,
            "RSD": s_rsd,
        }))

    return frames


def main():
    ap = argparse.ArgumentParser(description="生成合成验证数据集")
    ap.add_argument("--out", default="data/Datanew-8.31.xlsx")
    ap.add_argument("--seed", type=int, default=20260909)
    args = ap.parse_args()

    frames = build(seed=args.seed)
    out = os.path.abspath(args.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with pd.ExcelWriter(out, engine="openpyxl") as xw:
        for lp, df in zip(LASERS, frames):
            df.to_excel(xw, sheet_name=str(lp), index=False)

    total = sum(len(f) for f in frames)
    print("写出 %s" % out)
    print("  sheets : %s" % ", ".join(str(lp) for lp in LASERS))
    print("  rows   : %d" % total)
    for lp, df in zip(LASERS, frames):
        print("    laser=%-3d rows=%d  average[%.1f .. %.1f]  RSD[%.4f .. %.4f]"
              % (lp, len(df), df["average"].min(), df["average"].max(),
                 df["RSD"].min(), df["RSD"].max()))


if __name__ == "__main__":
    main()
