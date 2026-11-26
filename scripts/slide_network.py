"""Njáls saga signed network for the dark slide: transparent background, cream/red colours.
Writes figures/slide_network_njala.png (transparent, 300 dpi) and _nolegend.png."""
import csv
from pathlib import Path
import networkx as nx
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parents[1]
A, FIG = ROOT / "data/analysis", ROOT / "figures"
kill = list(csv.DictReader(open(ROOT / "data/final/killings_all.csv", encoding="utf-8")))
fam = [e for e in csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")) if e["layer"] in ("blood", "affinity", "foster")]
grp = {(r["saga"], r["name"]): r["family_group"] for r in csv.DictReader(open(A / "persons.csv", encoding="utf-8"))}
S = "brennu-njals_saga"
G = nx.Graph()
for e in fam:
    if e["saga"] == S:
        G.add_edge((S, e["a"]), (S, e["b"]), sign=1)
for r in kill:
    if r["saga"] == S and r["killer"] != r["victim"]:
        G.add_edge((S, r["killer"]), (S, r["victim"]), sign=-1)
G = G.subgraph(max(nx.connected_components(G), key=len)).copy()
pos = nx.spring_layout(G, seed=7, k=0.3, iterations=500)

CREAM, KIN, HOST, OTHER = "#F3D9A4", "#F3D9A4", "#E2553C", "#BFA98A"
FAM = [("njálssynir / bergþórshvoll", "Njáll's household", "#6FB3E8"),
       ("sigfússynir / grjótá", "Sigfússynir (Þráinn, Höskuldur)", "#4CC79A"),
       ("svínfellingar (flosi's kin)", "Flosi's kin", "#E79AC8"),
       ("hlíðarendi (gunnar's kin)", "Gunnar's kin", "#F2C14E"),
       ("kirkjubær (otkell's kin)", "Otkell's kin", "#C9A0F0")]
col = {g: c for g, _, c in FAM}
part = {(r["saga"], n) for r in kill for n in (r["killer"], r["victim"])}
deg = dict(G.degree())
for legend in (True, False):
    fig, ax = plt.subplots(figsize=(8, 7))
    fig.patch.set_alpha(0); ax.set_facecolor("none")
    fe = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] > 0]
    he = [(u, v) for u, v, d in G.edges(data=True) if d["sign"] < 0]
    nx.draw_networkx_edges(G, pos, edgelist=fe, edge_color=KIN, alpha=0.30, width=0.6, ax=ax)
    nx.draw_networkx_edges(G, pos, edgelist=he, edge_color=HOST, alpha=0.95, width=1.6, ax=ax)
    nx.draw_networkx_nodes(G, pos, nodelist=[v for v in G if v not in part], node_size=6, node_color=CREAM, alpha=0.55, linewidths=0, ax=ax)
    pv = sorted((v for v in G if v in part), key=lambda v: grp.get(v, "") in col)
    nx.draw_networkx_nodes(G, pos, nodelist=pv, node_size=[14 + 6 * deg[v] for v in pv],
                           node_color=[col.get(grp.get(v, ""), OTHER) for v in pv], edgecolors="#3a2414", linewidths=0.6, ax=ax)
    import numpy as np
    xs = np.array([p[0] for p in pos.values()]); ys = np.array([p[1] for p in pos.values()])
    W, H = xs.max() - xs.min(), ys.max() - ys.min()
    # (name shown, dx, dy) in fractions of the network width/height; leader line when moved far
    LAB = {"Gunnar": ("Gunnar", 0.0, 0.05), "Njáll": ("Njáll", -0.16, -0.06), "Kári": ("Kári", 0.10, -0.06),
           "Flosi": ("Flosi", -0.20, 0.06), "Höskuldur Hvítanesgoði": ("Höskuldur", 0.20, -0.01),
           "Þráinn": ("Þráinn", 0.14, 0.07), "Skarphéðinn": ("Skarphéðinn", -0.24, -0.01)}
    for v in G:
        if v[1] in LAB:
            t, dx, dy = LAB[v[1]]; x, y = pos[v]
            ax.annotate(t, (x, y), xytext=(x + dx * W, y + dy * H), fontsize=10.5, color=CREAM, ha="center", va="center",
                        fontweight="bold", arrowprops=dict(arrowstyle="-", color=CREAM, lw=0.7, alpha=0.8, shrinkA=4, shrinkB=4))
    if legend:
        h = [Line2D([], [], marker="o", ls="", ms=8, color=c, mec="#3a2414", label=l) for _, l, c in FAM]
        h += [Line2D([], [], color=HOST, lw=2.5, label="killing"), Line2D([], [], color=KIN, lw=2, alpha=0.5, label="family tie")]
        ax.legend(handles=h, loc="lower center", bbox_to_anchor=(0.5, -0.08), ncol=4, fontsize=9, frameon=False, labelcolor=CREAM)
    ax.axis("off"); fig.tight_layout()
    name = "slide_network_njala.png" if legend else "slide_network_njala_nolegend.png"
    fig.savefig(FIG / name, dpi=300, transparent=True, bbox_inches="tight")
    print("saved figures/" + name)
