#!/usr/bin/env python3
"""
06_figures.py: main and supplementary figures in GraphPad Prism style.

Thick black left and bottom axes, outward ticks, bold Arial, capped error bars, unboxed legends
outside the axes, colorblind-safe colors, no grid, no frame, no cohort header (single-cohort study).
Exports vector PDF, 600-dpi TIFF, and PNG capped at 1800 px for embedding.
Each figure writes its data audit to logs/figure_audit.txt before plotting.
"""
import json, os, random
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Rectangle

SEED = 42
np.random.seed(SEED); random.seed(SEED)
PROJ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
O = os.path.join(PROJ, "outputs"); F = os.path.join(PROJ, "figures")
EXPECTED_N, EXPECTED_EVENTS = 1339, 349
d = pd.read_csv(os.path.join(PROJ, "data", "analytical_dataset.csv"), low_memory=False)
assert len(d) == EXPECTED_N and d.e_primary.sum() == EXPECTED_EVENTS

AXW = 1.6
plt.rcParams.update({
    "font.family": "sans-serif", "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"], "font.size": 10, "font.weight": "bold",
    "axes.linewidth": AXW, "axes.edgecolor": "black", "axes.labelweight": "bold", "axes.labelsize": 12, "axes.labelcolor": "black",
    "axes.spines.top": False, "axes.spines.right": False, "axes.grid": False, "axes.facecolor": "white",
    "xtick.direction": "out", "ytick.direction": "out", "xtick.major.width": AXW, "ytick.major.width": AXW,
    "xtick.major.size": 6, "ytick.major.size": 6, "xtick.minor.size": 0, "ytick.minor.size": 0,
    "xtick.labelsize": 10, "ytick.labelsize": 10, "xtick.color": "black", "ytick.color": "black",
    "legend.frameon": False, "pdf.fonttype": 42, "ps.fonttype": 42, "savefig.facecolor": "white",
})
BLUE, RED, GREEN, ORANGE, PINK, SKY = "#0072B2", "#D55E00", "#009E73", "#E69F00", "#CC79A7", "#56B4E9"
DOM_COL = {"Gastrointestinal": GREEN, "Urinary": BLUE, "Cardiovascular": RED, "Thermoregulatory": ORANGE, "Pupillomotor": SKY, "Sexual": PINK}
ORDER = [f"SCAU{i}" for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 20, 21, 19, 22, 23, 24, 25]]
EB = dict(elinewidth=1.6, capsize=3.5, capthick=1.6)
audit = open(os.path.join(PROJ, "logs", "figure_audit.txt"), "w")


def save(fig, name):
    fig.savefig(os.path.join(F, name + ".pdf"), bbox_inches="tight", pad_inches=0.08)
    fig.savefig(os.path.join(F, name + ".tiff"), dpi=600, bbox_inches="tight", pad_inches=0.08, pil_kwargs={"compression": "tiff_lzw"})
    w, h = fig.get_size_inches()
    fig.savefig(os.path.join(F, name + ".png"), dpi=int(1760 / max(w, h)), bbox_inches="tight", pad_inches=0.08)
    plt.close(fig)


def letter(ax, s):
    ax.text(-0.02, 1.015, s, transform=ax.transAxes, fontsize=15, fontweight="bold", ha="right", va="bottom")


def forest(ax, x, lo, hi, y, color, filled=True, ms=6.5):
    ax.errorbar(x, y, xerr=[[max(x - lo, 0)], [max(hi - x, 0)]], fmt="o", color=color, mfc=color if filled else "white", mec=color, mew=1.5, ms=ms, zorder=3, **EB)


# Figure 1: flow diagram ---------------------------------------------------------
fl = pd.read_csv(os.path.join(PROJ, "logs", "exclusion_log.csv"))
print(fl[["criterion", "n_after", "excluded"]], file=audit)
det = json.loads(fl.detail[5])
fig, ax = plt.subplots(figsize=(7.4, 9.2)); ax.axis("off"); ax.set_xlim(0, 10); ax.set_ylim(0, 13.2)


def box(xc, y, w, h, txt, n):
    ax.add_patch(Rectangle((xc - w / 2, y - h / 2), w, h, fc="white", ec="black", lw=AXW, zorder=2))
    ax.text(xc, y, f"{txt}\nn = {n:,}", ha="center", va="center", fontsize=9.5, fontweight="bold", zorder=3)


XC, W, H = 3.0, 5.1, 1.2
steps = [("PPMI participants assigned to the PD cohort", fl.n_after[0], ""),
         ("Enrolled", fl.n_after[1], f"Screen failed, excluded, declined,\nor pending: {fl.excluded[1]}"),
         ("Baseline SCOPA-AUT, at most 2 of 21\nnon-sexual items missing", fl.n_after[3], f"No baseline form: {fl.excluded[2]}\nMore than 2 items missing: {fl.excluded[3]}"),
         ("Baseline MoCA available", fl.n_after[4], f"No baseline MoCA: {fl.excluded[4]}"),
         ("Free of all six cognition milestones\nat baseline", fl.n_after[5],
          f"Milestone at baseline: {fl.excluded[5]}\nMoCA<21: {det['m10']}; cognition item: {det['m11']};\napathy: {det['m13']}; hallucinations: {det['m12']};\nclinical dementia: {det['m14']}; composite: {det['m15']}"),
         ("At least one post-baseline\noutcome assessment", fl.n_after[6], f"No post-baseline\nassessment: {fl.excluded[6]}")]
ys = [12.5, 10.5, 8.5, 6.5, 4.5, 2.5]
for (t_, n_, side), y in zip(steps, ys):
    box(XC, y, W, H, t_, n_)
for i, (y0, y1) in enumerate(zip(ys[:-1], ys[1:])):
    ax.annotate("", xy=(XC, y1 + H / 2), xytext=(XC, y0 - H / 2), arrowprops=dict(arrowstyle="-|>", color="black", lw=AXW, shrinkA=0, shrinkB=0), zorder=1)
    m = (y0 + y1) / 2
    ax.plot([XC, 5.85], [m, m], color="black", lw=AXW, zorder=1)
    ax.text(5.95, m, steps[i + 1][2], ha="left", va="center", fontsize=8.5, fontweight="normal")
yb = 0.5; xl, xr = 1.75, 6.75; yk = 1.35
ax.plot([XC, XC], [ys[-1] - H / 2, yk], color="black", lw=AXW, zorder=1)
ax.plot([xl, xr], [yk, yk], color="black", lw=AXW, zorder=1)
for x_ in (xl, xr):
    ax.annotate("", xy=(x_, yb + 0.5), xytext=(x_, yk), arrowprops=dict(arrowstyle="-|>", color="black", lw=AXW, shrinkA=0, shrinkB=0), zorder=1)
e0 = d[d.era2 == 0]; e1 = d[d.era2 == 1]
print("era", len(e0), int(e0.e_primary.sum()), len(e1), int(e1.e_primary.sum()), file=audit)
box(xl, yb, 3.1, 1.0, f"Enrolled before 2020\n{int(e0.e_primary.sum())} events", len(e0))
box(xr, yb, 3.1, 1.0, f"Enrolled 2020 onward\n{int(e1.e_primary.sum())} events", len(e1))
save(fig, "Figure1_flow")

# Figure 2: item forest ------------------------------------------------------------
items = pd.read_csv(os.path.join(O, "cox_items_all.csv"))
pr = items[items.endpoint == "primary"]
print("Figure 2", pr.groupby("model")[["N", "events"]].max(), file=audit)
fig, axes = plt.subplots(1, 2, figsize=(9.6, 9.0), sharey=True)
fig.subplots_adjust(left=0.30, right=0.98, top=0.90, bottom=0.075, wspace=0.12)
for ax, mn, lab, tag in zip(axes, ["M1", "M2"], ["Model 1, HR (95% CI)", "Model 2, HR (95% CI)"], "AB"):
    t = pr[pr.model == mn].set_index("exposure").loc[ORDER]
    y = np.arange(len(ORDER))[::-1]
    for yy, (ex, r) in zip(y, t.iterrows()):
        forest(ax, r.HR, r.lo, min(r.hi, 3.0), yy, DOM_COL[r.domain], filled=r.q < 0.05)
    ax.axvline(1, color="black", lw=1.2, ls="--", zorder=1)
    ax.set_xscale("log"); ax.set_xlim(0.3, 3.0)
    ax.set_xticks([0.5, 1, 1.5, 2, 3]); ax.set_xticklabels(["0.5", "1", "1.5", "2", "3"]); ax.minorticks_off()
    ax.set_xlabel(lab); ax.set_ylim(-0.7, len(ORDER) - 0.3)
    ax.text(1.0, 1.012, f"{int((t.q < 0.05).sum())} of 25 items, q<0.05", transform=ax.transAxes, ha="right", va="bottom", fontsize=10)
    letter(ax, tag)
t = pr[pr.model == "M2"].set_index("exposure").loc[ORDER]
axes[0].set_yticks(np.arange(len(ORDER))[::-1]); axes[0].set_yticklabels(t.label)
axes[1].tick_params(axis="y", left=False)
hd = [Line2D([], [], marker="o", color=c, lw=0, ms=7, label=k) for k, c in DOM_COL.items()]
hd += [Line2D([], [], marker="o", color="black", lw=0, ms=7, label="q<0.05"), Line2D([], [], marker="o", mfc="white", mec="black", mew=1.5, lw=0, ms=7, label="q≥0.05")]
fig.legend(handles=hd, loc="upper center", ncol=4, bbox_to_anchor=(0.56, 1.0), fontsize=10, columnspacing=1.6, handletextpad=0.3)
save(fig, "Figure2_item_forest")

# Figure 3: cumulative incidence --------------------------------------------------
c = pd.read_csv(os.path.join(O, "cif_by_tertile.csv")); r = pd.read_csv(os.path.join(O, "risk_by_tertile.csv"))
sh = pd.read_csv(os.path.join(O, "tertile_shr.csv")).set_index("term"); lg = pd.read_csv(os.path.join(O, "tertile_logrank.csv")).iloc[0]
COL = {"Low": BLUE, "Middle": ORANGE, "High": RED}
cuts = {"Low": "0-6", "Middle": ">6-11", "High": "≥12"}
print("Figure 3", r[r.t == 0].to_dict("records"), file=audit)
fig = plt.figure(figsize=(7.2, 6.0))
ax = fig.add_axes([0.15, 0.335, 0.81, 0.565]); ax2 = fig.add_axes([0.15, 0.03, 0.81, 0.17])
XMAX = 10
for g in COL:
    z = c[(c.tert == g) & (c.t <= XMAX)]
    ax.step(z.t, 100 * z.cif, where="post", color=COL[g], lw=2.6, label=f"{g} ({cuts[g]})")
    ax.fill_between(z.t, 100 * z.lo, 100 * z.hi, step="post", color=COL[g], alpha=0.13, lw=0)
ax.set_ylim(0, 80); ax.set_xlim(0, XMAX); ax.set_xticks(range(0, 11, 2)); ax.set_yticks(range(0, 81, 20))
ax.set_ylabel("Cumulative incidence (%)"); ax.set_xlabel("Years from baseline")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.01), ncol=3, title="SCOPA-AUT total score", title_fontproperties={"weight": "bold", "size": 10}, fontsize=10)
ax.text(0.03, 0.98, f"High vs low: sHR {sh.loc['tertHigh'].sHR:.2f}", transform=ax.transAxes, va="top", fontsize=10)
ax.text(0.03, 0.905, "p<0.001" if lg.p < 0.001 else f"p={lg.p:.3f}", transform=ax.transAxes, va="top", fontsize=10, style="italic")
ax2.axis("off"); ax2.set_xlim(0, XMAX); ax2.set_ylim(0, 1)
ax2.text(-0.05, 1.05, "Number at risk", transform=ax2.transAxes, ha="right", va="center", fontsize=10)
for i, g in enumerate(COL):
    yy = 0.72 - i * 0.3
    ax2.text(-0.05, yy, g, transform=ax2.transAxes, ha="right", va="center", color=COL[g], fontsize=10)
    for t_ in range(0, 11, 2):
        ax2.text(t_, yy, str(int(r[(r.tert == g) & (r.t == t_)].n.iloc[0])), ha="center", va="center", fontsize=10)
save(fig, "Figure3_cumulative_incidence")

# Figure 4: endpoints heat map ---------------------------------------------------
EP = [("primary", "Any cognition milestone"), ("strict", "Strict cognitive"), ("m10", "MoCA < 21"), ("m14", "Clinical dementia"),
      ("m15", "Composite dementia"), ("m11", "Cognition item"), ("neuropsych", "Hallucinations or apathy"), ("m13", "Apathy"), ("m12", "Hallucinations")]
m2 = items[items.model == "M2"]
H_ = m2.pivot(index="exposure", columns="endpoint", values="HR").loc[ORDER, [e for e, _ in EP]]
Q = m2.pivot(index="exposure", columns="endpoint", values="q").loc[ORDER, [e for e, _ in EP]]
W_ = m2.assign(w=m2.hi / m2.lo).pivot(index="exposure", columns="endpoint", values="w").loc[ORDER, [e for e, _ in EP]]
H_ = H_.where(W_ <= 10)  # interval ratio above 10: too sparse to display
evs = {k: int(v) for k, v in m2.groupby("endpoint").events.max().items()}
print("Figure 4 events", evs, file=audit)
fig = plt.figure(figsize=(9.4, 9.4))
ax = fig.add_axes([0.285, 0.02, 0.60, 0.80]); cax = fig.add_axes([0.905, 0.27, 0.018, 0.30])
cm3 = plt.get_cmap("RdBu_r").copy(); cm3.set_bad("#E6E6E6")
im = ax.imshow(np.ma.masked_invalid(np.log2(H_.values)), cmap=cm3, vmin=-1, vmax=1, aspect="auto")
ax.set_xticks(range(len(EP))); ax.set_xticklabels([f"{l} ({evs[e]})" for e, l in EP], rotation=40, ha="left", rotation_mode="anchor", fontsize=9.5)
ax.xaxis.tick_top(); ax.set_yticks(range(len(ORDER))); ax.set_yticklabels(t.label, fontsize=10)
ax.set_xticks(np.arange(-0.5, len(EP)), minor=True); ax.set_yticks(np.arange(-0.5, len(ORDER)), minor=True)
ax.grid(which="minor", color="white", lw=1.2); ax.tick_params(which="both", length=0)
for i in range(H_.shape[0]):
    for j in range(H_.shape[1]):
        v = H_.values[i, j]
        if np.isnan(v):
            ax.text(j, i, "NE", ha="center", va="center", fontsize=8, color="#555555"); continue
        rgb = im.cmap(im.norm(np.log2(v)))[:3]
        col = "white" if np.mean(rgb) * 255 < 128 else "black"
        s_ = Q.values[i, j] < 0.05
        ax.text(j, i, f"{v:.2f}" + ("*" if s_ else ""), ha="center", va="center", fontsize=8.5, color=col, fontweight="bold" if s_ else "normal")
ax.spines[:].set_visible(False)
cb = fig.colorbar(im, cax=cax, ticks=[-1, -0.5, 0, 0.5, 1]); cb.set_ticklabels(["0.5", "0.71", "1", "1.41", "2"])
cb.outline.set_linewidth(AXW); cb.ax.tick_params(length=4, width=AXW); cax.set_title("HR", fontsize=11, fontweight="bold", pad=6)
save(fig, "Figure4_endpoint_heatmap")

# Figure 5: prediction ------------------------------------------------------------
p = pd.read_csv(os.path.join(O, "prediction_C_bootstrap.csv")).set_index("model")
pm = pd.read_csv(os.path.join(O, "prediction_metrics_reps.csv")).groupby("model", sort=False)[["harrell"]].mean()
keep = ["Base + total", "Base + 5 domains", "Base + 21 items (ridge)", "Base + LASSO items (min)", "Base + items selected by FDR", "Base + 3 prior items", "Base + GI domain", "Extended base + total", "Extended base + 5 domains"]
NAMES = {"Base + total": "Total score", "Base + 5 domains": "5 domain scores", "Base + 21 items (ridge)": "21 items, ridge", "Base + LASSO items (min)": "Items, LASSO",
         "Base + items selected by FDR": "Items selected by FDR", "Base + 3 prior items": "3 items of earlier version", "Base + GI domain": "Gastrointestinal domain",
         "Extended base + total": "Total score", "Extended base + 5 domains": "5 domain scores"}
cal = pd.read_csv(os.path.join(O, "calibration_5y.csv"))
print("Figure 5", p.loc[keep, ["dC_base", "dC_lo", "dC_hi"]].round(3).to_dict("index"), file=audit)
fig = plt.figure(figsize=(10.2, 4.9))
ax = fig.add_axes([0.205, 0.135, 0.42, 0.72]); ax3 = fig.add_axes([0.725, 0.135, 0.255, 0.72])
q = p.loc[keep]; y = np.arange(len(q))[::-1]
for yy, (m, r_) in zip(y, q.iterrows()):
    col = RED if m.startswith("Extended") else BLUE
    ref = "Extended base" if m.startswith("Extended") else "Base"
    forest(ax, pm.loc[m].harrell - pm.loc[ref].harrell, r_.dC_lo, r_.dC_hi, yy, col)
ax.axvline(0, color="black", lw=1.2, ls="--", zorder=1)
ax.set_yticks(y); ax.set_yticklabels([NAMES[m] for m in q.index])
ax.set_xlim(-0.01, 0.07); ax.set_xticks([0, 0.02, 0.04, 0.06]); ax.set_xticklabels(["0", "0.02", "0.04", "0.06"]); ax.set_ylim(-0.6, len(q) - 0.4)
ax.set_xlabel("Change in Harrell C (95% CI)")
for m, col, mk in [("Base", "black", "s"), ("Base + total", BLUE, "o"), ("Extended base + total", RED, "^")]:
    z = cal[cal.model == m]
    ax3.errorbar(100 * z.pred, 100 * z.obs, yerr=[100 * (z.obs - z.lo), 100 * (z.hi - z.obs)], fmt=mk, color=col, ms=6, mew=0, elinewidth=1.3, capsize=2.5, capthick=1.3)
lim = 65; ax3.plot([0, lim], [0, lim], color="black", ls="--", lw=1.2, zorder=0); ax3.set_xlim(0, lim); ax3.set_ylim(0, lim)
ax3.set_xticks(range(0, 61, 20)); ax3.set_yticks(range(0, 61, 20))
ax3.set_xlabel("Predicted 5-year risk (%)"); ax3.set_ylabel("Observed 5-year risk (%)")
letter(ax, "A"); letter(ax3, "B")
hd = [Line2D([], [], marker="s", color="black", lw=0, ms=7, label="Base"), Line2D([], [], marker="o", color=BLUE, lw=0, ms=7, label="Base + SCOPA-AUT"),
      Line2D([], [], marker="^", color=RED, lw=0, ms=7, label="Extended base + SCOPA-AUT")]
fig.legend(handles=hd, loc="upper center", ncol=3, bbox_to_anchor=(0.55, 1.0), fontsize=10.5, handletextpad=0.3)
save(fig, "Figure5_prediction")

# Supplementary Figure S1 -----------------------------------------------------------
s = pd.read_csv(os.path.join(O, "sensitivity_all.csv"))
print("S1", s[s.exposure == "SCAU14"][["analysis", "N", "events"]].to_string(), file=audit)
fig, axes = plt.subplots(1, 2, figsize=(10.2, 7.0), sharey=True)
fig.subplots_adjust(left=0.30, right=0.98, top=0.95, bottom=0.095, wspace=0.12)
for ax, ex, nm, xl_, tag in [(axes[0], "SCAU14", "Lightheaded on standing up, HR (95% CI)", (0.9, 2.1), "A"), (axes[1], "scopa_total21", "SCOPA-AUT total, HR per point (95% CI)", (0.98, 1.08), "B")]:
    z = s[s.exposure == ex].iloc[::-1]
    for yy, (_, r_) in enumerate(z.iterrows()):
        forest(ax, r_.HR, r_.lo, r_.hi, yy, BLUE if r_.analysis == "Main analysis" else "black", ms=6)
    ax.axvline(1, color="black", ls="--", lw=1.2, zorder=1); ax.set_xlim(*xl_); ax.set_xlabel(nm); letter(ax, tag)
z = s[s.exposure == "SCAU14"].iloc[::-1]
axes[0].set_yticks(np.arange(len(z))); axes[0].set_yticklabels(z.analysis.str.replace(">=", "≥ ", regex=False))
axes[1].tick_params(axis="y", left=False)
save(fig, "FigureS1_sensitivity")

# Supplementary Figure S2 -----------------------------------------------------------
cm = pd.read_csv(os.path.join(O, "item_spearman.csv")).set_index("item")
lab = t.label; dom = t.domain
fig = plt.figure(figsize=(8.4, 6.9))
ax = fig.add_axes([0.33, 0.03, 0.55, 0.90]); cax = fig.add_axes([0.90, 0.33, 0.02, 0.30])
im = ax.imshow(cm.values, cmap="Reds", vmin=0, vmax=0.7, aspect="auto")
ax.set_xticks(range(21)); ax.set_xticklabels([x.replace("SCAU", "") for x in cm.index], fontsize=9); ax.xaxis.tick_top()
ax.set_yticks(range(21)); ax.set_yticklabels([f"{x.replace('SCAU', '')}. {lab[x]}" for x in cm.index], fontsize=9.5)
ax.spines[:].set_visible(False); ax.tick_params(length=0)
cb = fig.colorbar(im, cax=cax); cb.outline.set_linewidth(AXW); cb.ax.tick_params(length=4, width=AXW); cax.set_title("ρ", fontsize=12, fontweight="bold", pad=6)
save(fig, "FigureS2_item_correlation")

# Supplementary Figure S3 -----------------------------------------------------------
l = pd.read_csv(os.path.join(O, "lasso_selection.csv")).sort_values("lasso_boot_pct")
fig = plt.figure(figsize=(7.4, 6.6))
ax = fig.add_axes([0.35, 0.10, 0.62, 0.80]); y = np.arange(len(l))
cols = [DOM_COL[dom[i]] for i in l["item"]]
ax.hlines(y, 0, l.lasso_boot_pct, color=cols, lw=2.2); ax.scatter(l.lasso_boot_pct, y, c=cols, s=46, linewidths=0, zorder=3)
ax.set_yticks(y); ax.set_yticklabels(l.label); ax.set_xlim(0, 100); ax.set_xticks(range(0, 101, 25)); ax.set_ylim(-0.7, len(l) - 0.3)
ax.set_xlabel("Selected in bootstrap samples (%)")
hd = [Line2D([], [], marker="o", color=c_, lw=0, ms=7, label=k) for k, c_ in DOM_COL.items() if k != "Sexual"]
fig.legend(handles=hd, loc="upper center", ncol=3, bbox_to_anchor=(0.55, 1.0), fontsize=10, handletextpad=0.3)
save(fig, "FigureS3_lasso_selection")

# Supplementary Figure S4 -----------------------------------------------------------
fm = d[d.e_primary == 1].first_ms.str.split("+").explode().value_counts()
NM = {"m10": "MoCA < 21", "m11": "Cognition item ≥ 3", "m12": "Hallucinations ≥ 3", "m13": "Apathy ≥ 3", "m14": "Clinical dementia", "m15": "Composite dementia"}
ev = {k: int(d[f"e_{k}"].sum()) for k in NM}
keys = sorted(NM, key=lambda k: -ev[k]); x = np.arange(len(keys)); w = 0.38
fig = plt.figure(figsize=(7.6, 4.8)); ax = fig.add_axes([0.10, 0.22, 0.88, 0.66])
b1 = ax.bar(x - w / 2, [ev[k] for k in keys], w, color=BLUE, edgecolor="black", lw=1.4, label="Ever reached")
b2 = ax.bar(x + w / 2, [int(fm.get(k, 0)) for k in keys], w, color=ORANGE, edgecolor="black", lw=1.4, label="Part of the first event")
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 3, str(int(b.get_height())), ha="center", va="bottom", fontsize=9.5)
ax.set_xticks(x); ax.set_xticklabels([NM[k] for k in keys], rotation=28, ha="right", rotation_mode="anchor"); ax.set_ylim(0, 200); ax.set_yticks(range(0, 201, 50))
ax.set_ylabel("Participants (n)")
ax.legend(loc="lower center", bbox_to_anchor=(0.5, 1.0), ncol=2, fontsize=10)
save(fig, "FigureS4_milestone_composition")
audit.close()
print("figures done")
