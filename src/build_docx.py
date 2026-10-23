# -*- coding: utf-8 -*-
"""
DOCX 报告生成器 — 新数据 Datanew-8.31 (v3)
============================================
读已经跑出来的 metrics.json，生成两种 docx：
  1. <key>_report.docx             本批数据分析报告（每个分析一份，**图片嵌入**）
  2. <key>_report_comparison.docx  新旧数据对比报告（每个分析一份，无图）

和老 docx 结构对齐（真正的 Heading1/Heading2/ListBullet 样式）。
图片既嵌入 docx，也保留在 images/ 子目录里。
"""

import os
import json
from docx import Document
from docx.shared import Pt, Cm, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT  = os.path.normpath(os.path.join(SCRIPT_DIR, ".."))
# OLD_ROOT 存放上一轮运行的 metrics.json，用于生成新旧对比报告；
# NEW_ROOT 是本次分析脚本的输出目录。
OLD_ROOT = os.environ.get("RAMAN_OLD", os.path.join(SCRIPT_DIR, "OLD_data"))
NEW_ROOT = os.environ.get("RAMAN_OUT", os.path.join(REPO_ROOT, "reports", "Datanew-8.31"))
KEYS = ["1_avg_all", "2_avg_rsd015", "3_rsd_all", "4_rsd_filt030"]

LABELS_ZH = {
    "laser_power":   "激光功率 (Laser Power, mW)",
    "concentration": "浓度 (Concentration, pM)",
    "acq_time":      "采集时间 (Acquisition Time, s)",
    "flow_rate":     "流速 (Flow Rate, μL/min)",
}

RSD_NOTE = "（已用 std/mean 修正，原始数据中此列实为 std 误差棒）"

# 图序 → (文件名, 中文标题)，与生成脚本里 images/ 子目录里 PNG 一一对应
FIG_MAP = [
    ("shap_global_importance.png",                    "全局特征重要性（Mean |SHAP value|）"),
    ("shap_beeswarm.png",                             "SHAP Summary（Beeswarm）"),
    ("shap_dependence_laser_power.png",               "激光功率 (Laser Power) 与SHAP依赖关系"),
    ("shap_dependence_concentration.png",             "浓度 (Concentration) 与SHAP依赖关系"),
    ("shap_dependence_acq_time.png",                  "采集时间 (Acquisition Time) 与SHAP依赖关系"),
    ("shap_dependence_flow_rate.png",                 "流速 (Flow Rate) 与SHAP依赖关系"),
    # 4 特征两两交互 = 6 对
    ("shap_interaction_laser_power_x_concentration.png",    "交互：激光功率 × 浓度（着色）"),
    ("shap_interaction_laser_power_x_acq_time.png",        "交互：激光功率 × 采集时间（着色）"),
    ("shap_interaction_laser_power_x_flow_rate.png",       "交互：激光功率 × 流速（着色）"),
    ("shap_interaction_concentration_x_acq_time.png",      "交互：浓度 × 采集时间（着色）"),
    ("shap_interaction_concentration_x_flow_rate.png",     "交互：浓度 × 流速（着色）"),
    ("shap_interaction_acq_time_x_flow_rate.png",          "交互：采集时间 × 流速（着色）"),
    ("shap_local_low.png",                            "SHAP局部解释 — 低值样本"),
    ("shap_local_medium.png",                         "SHAP局部解释 — 中值样本"),
    ("shap_local_high.png",                           "SHAP局部解释 — 高值样本"),
    ("shap_parity_plot.png",                          "Parity Plot：预测 vs 实际（与 y=x 参考线对比）"),
]

CONCLUSIONS_NEW = {
    "1_avg_all": [
        "浓度 (Concentration) 是影响拉曼强度平均值的最关键因素，远超其他因素。",
        "采集时间 (Acquisition Time) 是第二影响因素，时间越久信号越强。",
        "流速 (Flow Rate) 是第三影响因素，流速越快信号越强，停止时信号最低。",
        "激光功率 (Laser Power) 贡献最小。",
    ],
    "2_avg_rsd015": [
        "在低 RSD 子集（修正 RSD<0.15，940 行）上，浓度仍主导信号，模型 Test R²=0.9926。",
        "浓度 (Concentration) 排第一，采集时间 (Acquisition Time) 紧跟其后。",
        "流速 (Flow Rate) 与激光功率 (Laser Power) 的相对贡献与全数据基本一致。",
        "剔除高 RSD 行后样本数仍足够支撑 GBT 拟合，未出现过拟合。",
    ],
    "3_rsd_all": [
        "【修正后】流速 (Flow Rate) 重新成为 RSD 第一驱动（SHAP=0.030）— 与旧数据结论一致。",
        "浓度 (Concentration) 排第二（SHAP=0.021），采集时间 (Acquisition Time) 第三（SHAP=0.015）。",
        "激光功率 (Laser Power) 仍排第四（SHAP=0.005）。",
        "Test R² 从 0.38 提升到 0.70 — 因为新数据的 \"RSD\" 列实际是 std 误差棒，已用 std/mean 修正。",
    ],
    "4_rsd_filt030": [
        "【剔 RSD≥0.30】删除 12 行高 RSD 异常点（主要是 flow=0 的 9 行）后，模型 Test R²=0.7282（4 个分析中最高，超过 #3 的 0.6995）。",
        "流速 (Flow Rate) 第一（SHAP=0.0215），浓度 (Concentration) 第二（SHAP=0.0209）。",
        "采集时间 (Acquisition Time) 第三（SHAP=0.0152），激光功率 (Laser Power) 第四（SHAP=0.0037）。",
        "本方案替代原\"排除 flow=0\"：保留近全部 1011 行数据，SHAP 范围 0.004-0.022 更紧凑，方向与旧数据一致。",
    ],
}

KEY_DESCR = {
    "1_avg_all":     "分析1 — 平均值 / 全数据",
    "2_avg_rsd015":  "分析2 — 平均值 / 筛选 RSD<15%",
    "3_rsd_all":     "分析3 — RSD / 全数据",
    "4_rsd_filt030": "分析4 — RSD / 全数据 + 剔 RSD≥0.30",
}

COMPARISON_NOTES = {
    "1_avg_all": [
        "两批数据规模相近（旧 1090 vs 新 1023），结论可信。",
        "新批次 laser=10 缺 C=160，但贡献小，影响有限。",
        "新数据 Test R² 提升至 0.9954。",
        "特征排序两批完全一致：C > T > F > L。",
    ],
    "2_avg_rsd015": [
        "旧数据 926 行（筛掉 15%），新数据 491 行（筛掉 52%）。新批次 RSD 整体偏高。",
        "新数据 Test R² 降至 0.85，旧数据 0.99。",
        "在低 RSD 子集上，新批次 Acq.Time 反超 Concentration 成为第一驱动。",
        "RSD 阈值的选取需根据批次噪声水平适配。",
    ],
    "3_rsd_all": [
        "旧数据流速主导 RSD（SHAP=0.084），新数据流速排第四。",
        "主因：旧批次流速=0 行占 10%，形成二元化开关；新批次只占 1.9%。",
        "新批次 RSD 整体偏高（中位 17.4% vs 旧 0.063），分布更分散、极端值更多。",
        "新批次中激光功率反超流速成为 RSD 第三驱动。",
    ],
    "4_rsd_filt030": [
        "剔 RSD≥0.30 后，新数据 Test R² 从 0.38 提升到 0.73（旧 0.60 升到 0.65），4 个分析中最高。",
        "两批数据上 Flow Rate 都是 RSD 第一驱动（修正后）。",
        "新数据上 Laser 反超 Flow（升到第3），旧数据 Laser 排第4。",
        "RSD 模型 R²=0.73 良好，已接近物理上限。",
    ],
}

COMPARISON_CONCLUSIONS = {
    "1_avg_all": [
        "✅ 两批结论一致：拉曼强度预测中浓度与采集时间是核心驱动。",
        "✅ Laser Power 在两批中均贡献最小（排第4），可固定到最优档。",
        "✅ 模型 R² > 0.99，信号强度可被实验条件充分解释。",
    ],
    "2_avg_rsd015": [
        "⚠️ 旧批次 Acq.Time 在 #2 排第2，新批次升至 #1。",
        "⚠️ RSD 阈值选取需考虑批次噪声水平。",
        "✅ 严格筛选后激光功率贡献降至最低。",
    ],
    "3_rsd_all": [
        "⚠️ 流速在新数据上从第1 跌到第4，主因流速=0 行比例从 10% 降到 1.9%。",
        "✅ 两批数据上激光功率都进入前4，新批次激光对 RSD 贡献超过流速。",
        "⚠️ 新数据 RSD 整体偏高（中位 17.4%），RSD 模型 Test R² 仅 0.38。",
    ],
    "4_rsd_filt030": [
        "✅ 新数据剔 RSD≥0.30 后，Flow Rate 仍第一驱动 — 与旧数据一致。",
        "⚠️ 新数据上 Laser 反超 Flow（升至第3）— 新批次独有（剔 RSD≥0.30 后仍如此）。",
        "⚠️ Test R²=0.73 良好，高于 #3 的 0.70；剔 RSD≥0.30 解决了极端点扎眼问题。",
    ],
}


# ─────────────────────────────────────────────
# docx 工具
# ─────────────────────────────────────────────

# 字体方案
FONT_CN = "宋体"          # 中文正文
FONT_EN = "Times New Roman" # 英文/数字
FONT_MONO = "Consolas"      # 数字、代码

def set_run_font(run, size=11, bold=False, italic=False, color=None):
    """统一设置 run 字体：中文宋体 + 英文 Times New Roman"""
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color is not None:
        from docx.shared import RGBColor
        run.font.color.rgb = RGBColor(*color)
    # 同时设中英文字体（rFonts.ascii 是西文，east_asia 是中文）
    from docx.oxml.ns import qn
    rPr = run._element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        from docx.oxml import OxmlElement
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), FONT_EN)
    rFonts.set(qn("w:hAnsi"), FONT_EN)
    rFonts.set(qn("w:cs"), FONT_EN)
    rFonts.set(qn("w:eastAsia"), FONT_CN)
    return run


def apply_doc_defaults(doc):
    """页面边距 + 默认段落样式 + 标题样式（每个新 doc 调一次）"""
    from docx.shared import Cm
    for section in doc.sections:
        section.top_margin = Cm(2.2)
        section.bottom_margin = Cm(2.2)
        section.left_margin = Cm(2.4)
        section.right_margin = Cm(2.4)
    # 默认 Normal 样式
    normal = doc.styles["Normal"]
    normal.font.name = FONT_EN
    normal.font.size = Pt(11)
    from docx.oxml.ns import qn
    rPr = normal.element.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        from docx.oxml import OxmlElement
        rFonts = OxmlElement("w:rFonts")
        rPr.append(rFonts)
    rFonts.set(qn("w:ascii"), FONT_EN)
    rFonts.set(qn("w:hAnsi"), FONT_EN)
    rFonts.set(qn("w:eastAsia"), FONT_CN)
    # 标题样式
    h1 = doc.styles["Heading 1"]
    h1.font.name = FONT_EN
    h1.font.size = Pt(20)
    h1.font.bold = True
    h1.font.color.rgb = None  # 用默认色
    rPr1 = h1.element.get_or_add_rPr()
    rFonts1 = rPr1.find(qn("w:rFonts"))
    if rFonts1 is None:
        from docx.oxml import OxmlElement
        rFonts1 = OxmlElement("w:rFonts")
        rPr1.append(rFonts1)
    rFonts1.set(qn("w:ascii"), FONT_EN)
    rFonts1.set(qn("w:hAnsi"), FONT_EN)
    rFonts1.set(qn("w:eastAsia"), FONT_CN)

    h2 = doc.styles["Heading 2"]
    h2.font.name = FONT_EN
    h2.font.size = Pt(16)
    h2.font.bold = True
    rPr2 = h2.element.get_or_add_rPr()
    rFonts2 = rPr2.find(qn("w:rFonts"))
    if rFonts2 is None:
        from docx.oxml import OxmlElement
        rFonts2 = OxmlElement("w:rFonts")
        rPr2.append(rFonts2)
    rFonts2.set(qn("w:ascii"), FONT_EN)
    rFonts2.set(qn("w:hAnsi"), FONT_EN)
    rFonts2.set(qn("w:eastAsia"), FONT_CN)

    h3 = doc.styles["Heading 3"]
    h3.font.name = FONT_EN
    h3.font.size = Pt(14)
    h3.font.bold = True
    rPr3 = h3.element.get_or_add_rPr()
    rFonts3 = rPr3.find(qn("w:rFonts"))
    if rFonts3 is None:
        from docx.oxml import OxmlElement
        rFonts3 = OxmlElement("w:rFonts")
        rPr3.append(rFonts3)
    rFonts3.set(qn("w:ascii"), FONT_EN)
    rFonts3.set(qn("w:hAnsi"), FONT_EN)
    rFonts3.set(qn("w:eastAsia"), FONT_CN)


def shade_cell(cell, hex_color):
    """给单元格底色"""
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def add_para(doc, text, align=None, size=11, bold=False, italic=False):
    p = doc.add_paragraph()
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.line_spacing = 1.25
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic)
    return p

def add_h1(doc, text):
    h = doc.add_heading(text, level=1)
    for run in h.runs:
        set_run_font(run, size=20, bold=True)
    h.paragraph_format.space_before = Pt(10)
    h.paragraph_format.space_after = Pt(6)
    return h

def add_h2(doc, text):
    h = doc.add_heading(text, level=2)
    for run in h.runs:
        set_run_font(run, size=16, bold=True)
    h.paragraph_format.space_before = Pt(8)
    h.paragraph_format.space_after = Pt(4)
    return h

def add_bullets(doc, items, size=11):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        run = p.add_run(it)
        set_run_font(run, size=size)
        p.paragraph_format.space_after = Pt(2)

def add_image(doc, image_path, caption_num, caption_text, width_inches=6.0):
    """嵌入图片，并在其下方加图编号 + 中文标题"""
    if not os.path.exists(image_path):
        add_para(doc, f"⚠️ 图片缺失：{os.path.basename(image_path)}")
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run()
    run.add_picture(image_path, width=Inches(width_inches))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    crun = cap.add_run(f"图{caption_num}  {caption_text}")
    set_run_font(crun, size=10, bold=True, italic=True)

def make_table(doc, headers, rows, widths_cm=None, header_fill="305496", stripe_fill="EAF1FB"):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    # 表头
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        p = cell.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(h)
        set_run_font(run, size=10, bold=True)
        # 白字 + 蓝底
        from docx.shared import RGBColor
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        shade_cell(cell, header_fill)
    # 数据行
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            run = p.add_run(str(v))
            set_run_font(run, size=10)
            # 隔行底色
            if i % 2 == 1:
                shade_cell(cell, stripe_fill)
    if widths_cm:
        for col_idx, w in enumerate(widths_cm):
            for row in table.rows:
                row.cells[col_idx].width = Cm(w)
    return table


# ─────────────────────────────────────────────
# 数据报告 docx（嵌入图片）
# ─────────────────────────────────────────────

def build_data_report(metrics, key, out_path):
    doc = Document()
    apply_doc_defaults(doc)
    add_para(doc, metrics["description"], align="center", size=18, bold=True)
    doc.add_paragraph()

    add_h1(doc, "一、数据信息")
    add_para(doc, f"目标变量：{metrics['target_label']}")
    add_para(doc, f"分析类型：{metrics['description']}")
    add_para(doc, f"样本数量：{metrics['n_samples']} 行")

    add_h1(doc, "二、模型性能")
    add_para(doc, "模型：GradientBoostingRegressor（n_estimators=300, max_depth=5, learning_rate=0.05, subsample=0.8, random_state=42）")
    make_table(doc,
        ["指标", "数值"],
        [
            ["Train R²",  metrics["metrics"]["train_r2"]],
            ["Test R²",   metrics["metrics"]["test_r2"]],
            ["Test RMSE", metrics["metrics"]["test_rmse"]],
            ["Test MAE",  metrics["metrics"]["test_mae"]],
        ],
        widths_cm=[6, 8])

    add_h1(doc, "三、特征重要性 (Mean |SHAP|)")
    rows = [[LABELS_ZH.get(r["Feature"], r["Feature"]), f"{r['Mean |SHAP|']:.4f}"]
            for r in metrics["shap_global_importance"]]
    make_table(doc, ["特征", "Mean |SHAP|"], rows, widths_cm=[10, 6])

    add_h1(doc, "四、特征取值范围")
    fvr = metrics["feature_values_range"]
    rows = []
    for f in metrics["features"]:
        if f in fvr:
            rows.append([
                LABELS_ZH.get(f, f),
                f"{fvr[f]['min']:.4f}",
                f"{fvr[f]['max']:.4f}",
                f"{fvr[f]['mean']:.4f}",
            ])
    make_table(doc, ["特征", "最小值", "最大值", "均值"], rows, widths_cm=[8, 4, 4, 4])

    add_h1(doc, "五、目标变量范围")
    tr = metrics["target_range"]
    add_para(doc, f"最小值: {tr['min']:.4f}  最大值: {tr['max']:.4f}  均值: {tr['mean']:.4f}")

    add_h1(doc, "六、SHAP 图表")
    add_para(doc, "注：下方图片已嵌入本报告；同时原始 PNG 也保存在本报告所在目录的 images/ 子目录中。")
    doc.add_paragraph()

    img_dir = os.path.join(NEW_ROOT, f"{key}_report", "images")

    # 6.1 全局重要性
    add_h2(doc, "6.1 全局重要性（Bar Chart）")
    add_image(doc, os.path.join(img_dir, FIG_MAP[0][0]), 1, FIG_MAP[0][1])

    # 6.2 Beeswarm
    add_h2(doc, "6.2 Beeswarm 图（Summary）")
    add_image(doc, os.path.join(img_dir, FIG_MAP[1][0]), 2, FIG_MAP[1][1])

    # 6.3 单特征依赖图（4 张）
    add_h2(doc, "6.3 单特征 SHAP 依赖图")
    for i, (fn, cap) in enumerate(FIG_MAP[2:6]):
        add_image(doc, os.path.join(img_dir, fn), i + 3, cap)

    # 6.4 特征交互（4 特征两两组合 = 6 对）
    add_h2(doc, "6.4 特征交互图（4 特征 × 6 对组合）")
    for i, (fn, cap) in enumerate(FIG_MAP[6:12]):
        add_image(doc, os.path.join(img_dir, fn), i + 7, cap)

    # 6.5 局部解释
    add_h2(doc, "6.5 局部解释（Waterfall）")
    for i, (fn, cap) in enumerate(FIG_MAP[12:15]):
        add_image(doc, os.path.join(img_dir, fn), i + 13, cap)

    # 6.6 Parity plot（预测 vs 实际）
    add_h2(doc, "6.6 Parity Plot：预测 vs 实际")
    add_image(doc, os.path.join(img_dir, FIG_MAP[15][0]), 16, FIG_MAP[15][1])

    add_h1(doc, "七、结论")
    add_bullets(doc, CONCLUSIONS_NEW[key])

    doc.save(out_path)


# ─────────────────────────────────────────────
# 对比报告 docx（无图）
# ─────────────────────────────────────────────

def build_comparison_report(metrics_new, metrics_old, key, out_path):
    doc = Document()
    apply_doc_defaults(doc)
    add_para(doc, f"新旧数据对比 — {KEY_DESCR[key]}", align="center", size=18, bold=True)
    doc.add_paragraph()

    add_h1(doc, "一、本次分析概览")
    add_para(doc, f"目标变量：{metrics_new['target_label']}")
    add_para(doc, f"本批数据：{metrics_new['description']}（{metrics_new['n_samples']} 行）")
    add_para(doc, f"旧批数据：{metrics_old['description']}（{metrics_old['n_samples']} 行）")
    add_para(doc, "模型：GradientBoostingRegressor（同配置）")

    add_h1(doc, "二、两批数据规模对比")
    make_table(doc,
        ["项目", "旧数据", "新数据"],
        [
            ["样本数",         metrics_old["n_samples"], metrics_new["n_samples"]],
            ["laser 档位",     "10 / 30 / 50",         "10 / 30 / 50"],
            ["concentration 档", "5–160 (6 档)",       "5–160 (6 档，新批次 laser=10 缺 160)"],
            ["RSD 单位",       "小数 (中位 0.063)",    "百分数 (中位 17.43)"],
        ],
        widths_cm=[6, 5, 7])

    add_h1(doc, "三、模型表现对比")
    make_table(doc,
        ["指标", "旧数据", "新数据", "差异"],
        [
            ["Train R²",
                metrics_old["metrics"]["train_r2"],
                metrics_new["metrics"]["train_r2"],
                f"{metrics_new['metrics']['train_r2'] - metrics_old['metrics']['train_r2']:+.4f}"],
            ["Test R²",
                metrics_old["metrics"]["test_r2"],
                metrics_new["metrics"]["test_r2"],
                f"{metrics_new['metrics']['test_r2'] - metrics_old['metrics']['test_r2']:+.4f}"],
            ["Test RMSE",
                metrics_old["metrics"]["test_rmse"],
                metrics_new["metrics"]["test_rmse"],
                "（量纲不同，仅供参考）"],
            ["Test MAE",
                metrics_old["metrics"]["test_mae"],
                metrics_new["metrics"]["test_mae"],
                "（量纲不同，仅供参考）"],
        ],
        widths_cm=[4, 5, 5, 4])

    add_h1(doc, "四、特征重要性对比")
    new_by_feat = {r["Feature"]: r["Mean |SHAP|"] for r in metrics_new["shap_global_importance"]}
    old_by_feat = {r["Feature"]: r["Mean |SHAP|"] for r in metrics_old["shap_global_importance"]}
    rows = []
    for r in metrics_new["shap_global_importance"]:
        feat_lbl = r["Feature"]
        zh_lbl   = LABELS_ZH.get(feat_lbl, feat_lbl)
        new_val  = r["Mean |SHAP|"]
        old_val  = old_by_feat.get(feat_lbl, None)
        if old_val is None:
            old_val_disp = "—"
            diff = "新增"
        else:
            old_val_disp = f"{old_val:.4f}"
            if key.startswith("3_") or key.startswith("4_"):
                diff = "RSD 量纲不同"
            else:
                ratio = new_val / old_val if old_val else 0
                diff = f"{ratio:.2f}×"
        rows.append([zh_lbl, old_val_disp, f"{new_val:.4f}", diff])
    make_table(doc, ["特征", "旧 SHAP", "新 SHAP", "对比"], rows, widths_cm=[8, 4, 4, 4])

    add_h1(doc, "五、特征排名变化")
    new_order = [r["Feature"] for r in metrics_new["shap_global_importance"]]
    old_order = [r["Feature"] for r in metrics_old["shap_global_importance"]]
    rows = []
    for i, feat in enumerate(new_order):
        old_rank = old_order.index(feat) + 1 if feat in old_order else "—"
        new_rank = i + 1
        rows.append([
            LABELS_ZH.get(feat, feat),
            f"第 {old_rank} 位" if isinstance(old_rank, int) else old_rank,
            f"第 {new_rank} 位",
            "持平" if old_rank == new_rank else f"{new_rank - old_rank:+d}",
        ])
    make_table(doc, ["特征", "旧排名", "新排名", "变化"], rows, widths_cm=[8, 4, 4, 4])

    add_h1(doc, "六、关键差异归因")
    add_bullets(doc, COMPARISON_NOTES[key])

    add_h1(doc, "七、结论")
    add_bullets(doc, COMPARISON_CONCLUSIONS[key])

    doc.save(out_path)


def load_metrics(root, key):
    p = os.path.join(root, f"{key}_report", "metrics.json")
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def main():
    for key in KEYS:
        new_metrics = load_metrics(NEW_ROOT, key)
        old_metrics = load_metrics(OLD_ROOT, key)

        report_dir = os.path.join(NEW_ROOT, f"{key}_report")

        # 保存到临时路径，再原子替换（避开文件锁问题）
        data_tmp = os.path.join(report_dir, f"{key}_report_new.docx")
        comp_tmp = os.path.join(report_dir, f"{key}_report_comparison_new.docx")

        build_data_report(new_metrics, key, data_tmp)
        build_comparison_report(new_metrics, old_metrics, key, comp_tmp)

        # 原子替换
        for old_name, tmp_name in [(f"{key}_report.docx", data_tmp),
                                    (f"{key}_report_comparison.docx", comp_tmp)]:
            old_path = os.path.join(report_dir, old_name)
            try:
                if os.path.exists(old_path):
                    os.remove(old_path)
            except PermissionError:
                pass  # 旧文件被锁定，替换会失败但 tmp 文件已生成
            try:
                os.replace(tmp_name, old_path)
                print(f"  built: {old_path}")
            except (FileNotFoundError, PermissionError):
                # 备用：把 tmp 改名到目标
                try:
                    os.rename(tmp_name, old_path)
                    print(f"  built (renamed): {old_path}")
                except:
                    print(f"  WARNING: could not replace {old_path}, kept as {tmp_name}")

    print("\n=== ALL DOCX REGENERATED WITH EMBEDDED IMAGES ===")


if __name__ == "__main__":
    main()