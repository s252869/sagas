"""Feud and revenge analysis from the text-based annotation (data/feuds/feud_output_*.json).

- merges the annotation into data/feuds/killings_feuds.csv and data/feuds/feuds.csv
- share of killings that are revenge (explicit / implied), motives
- avenger's relation to the avenged person (blood / foster / affinity / sworn / household / none)
- whom revenge strikes (the killer himself / his kin / household or ally)
- feud sizes and how feuds end
- agreement with the network-based measure (data/analysis/revenge_killings_depth1.csv)
- makes a check sheet of revenge links for manual validation (data/review/manual_check_revenge.xlsx)
"""
import csv, json, collections, random, math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import os
KILLINGS = os.environ.get("KILLINGS", "killings_all.csv")   # killings_final.csv = original keyword set only

F, A, FIG = ROOT / "data/feuds", ROOT / "data/analysis", ROOT / "figures"
base = {r["kid"]: r for r in csv.DictReader(open(ROOT / "data/final" / KILLINGS, encoding="utf-8"))}
ann, feuds = {}, []
for f in sorted(F.glob("feud_output_*.json")):
    if f.name == "feud_output_ext.json" and KILLINGS != "killings_all.csv":
        continue
    d = json.loads(f.read_text(encoding="utf-8"))
    ann.update({k["kid"]: k for k in d["killings"]}); feuds += d.get("feuds", [])
missing = set(base) - set(ann)
print(f"annotated {len(set(ann)&set(base))}/{len(base)} killings, {len(feuds)} feuds" + (f"; MISSING {sorted(missing)}" if missing else ""))

low = lambda x: str(x or "").strip().lower()
# manual check corrections (data/feuds/manual_feud_corrections.csv)
for c in csv.DictReader(open(F / "manual_feud_corrections.csv", encoding="utf-8")):
    a = ann.setdefault(c["kid"], {})
    if c["field"] == "note":
        a["note"] = (str(a.get("note") or "") + " | manual check: " + c["new_value"]).strip(" |")
    else:
        a[c["field"]] = c["new_value"]
        a["note"] = (str(a.get("note") or "") + f" | manual correction: {c['field']} -> {c['new_value']} ({c['reason']})").strip(" |")
    if c["field"] == "motive" and c["new_value"] == "revenge" and not a.get("revenge_basis"):
        a["revenge_basis"] = "implied"
KEYS = ["feud_id", "feud_name", "feud_type", "killer_side", "victim_side", "motive", "avenges_kid", "avenges_person",
        "revenge_basis", "avenger_relation", "relation_category", "target", "evidence", "settled_after", "confidence", "note"]
rows = []
for kid, b in base.items():
    a = ann.get(kid, {})
    rows.append({"kid": kid, "saga": b["saga"], "chapter": b["chapter"], "killer": b["killer"], "victim": b["victim"],
                 **{k: (json.dumps(a.get(k), ensure_ascii=False) if isinstance(a.get(k), (list, dict)) else a.get(k, "")) for k in KEYS}})
with open(F / "killings_feuds.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(rows[0])); w.writeheader(); w.writerows(rows)
# feud sizes from the CURRENT killings (dropped killings no longer count)
size = collections.Counter(r["feud_id"] for r in rows)
for x in feuds:
    x["n_killings_annotated"] = x.get("n_killings"); x["n_killings"] = size.get(x["feud_id"], 0)
feuds = [x for x in feuds if x["n_killings"] > 0]
with open(F / "feuds.csv", "w", newline="", encoding="utf-8") as f:
    keys = sorted({k for x in feuds for k in x})
    w = csv.DictWriter(f, keys); w.writeheader()
    w.writerows({k: (json.dumps(x.get(k), ensure_ascii=False) if isinstance(x.get(k), list) else x.get(k, "")) for k in keys} for x in feuds)

rev = [r for r in rows if low(r["revenge_basis"]) in ("explicit", "implied")]
print(f"\nrevenge killings: {len(rev)}/{len(rows)} ({len(rev)/len(rows):.0%}); "
      f"explicit {sum(low(r['revenge_basis'])=='explicit' for r in rev)}, implied {sum(low(r['revenge_basis'])=='implied' for r in rev)}; "
      f"linked to a listed killing {sum(1 for r in rev if r['avenges_kid'])}")
print("motives:", collections.Counter(low(r["motive"]) for r in rows).most_common())
print("avenger's relation to the avenged:", collections.Counter(low(r["relation_category"]) for r in rev).most_common())
print("revenge strikes:", collections.Counter(low(r["target"]) for r in rev).most_common())
real = [x for x in feuds if low(x.get("feud_type", "feud")) != "isolated" and int(x.get("n_killings") or 0) >= 2]
print(f"\nfeuds with 2+ killings: {len(real)}; killings in them: {sum(int(x['n_killings']) for x in real)}; "
      f"largest: {sorted(((int(x['n_killings']), x['feud_name']) for x in real), reverse=True)[:5]}")
print("feuds ended by:", collections.Counter(low(x.get("ended_by")) for x in real).most_common())
print("settlement reported after killing:", collections.Counter(low(r["settled_after"])[:7] for r in rows).most_common())

# agreement with the network-based measure (depth 1)
net = {}
nf = A / "revenge_killings_depth1.csv"
if nf.exists():
    for r in csv.DictReader(open(nf, encoding="utf-8")):
        net[(r["saga"], r["killer"], r["victim"])] = r
    def kappa(a, b):
        n = len(a); po = sum(x == y for x, y in zip(a, b)) / n
        pe = sum(a.count(c) / n * b.count(c) / n for c in set(a) | set(b)); return po, (po - pe) / (1 - pe) if pe < 1 else float("nan")
    t = [low(r["revenge_basis"]) in ("explicit", "implied") for r in rows]
    for label, f in [("network: killer tied to earlier victim", lambda q: bool(q.get("revenge_tie"))),
                     ("network: targeted revenge", lambda q: q.get("targeted") == "yes")]:
        n_ = [f(net.get((r["saga"], r["killer"], r["victim"]), {})) for r in rows]
        po, k = kappa(t, n_)
        both = sum(a and b for a, b in zip(t, n_))
        print(f"text revenge vs {label}: agreement {po:.0%}, kappa {k:.2f}; both {both}, text only {sum(a and not b for a,b in zip(t,n_))}, network only {sum(b and not a for a,b in zip(t,n_))}")

# check sheet: random 20 revenge links + 10 random non-revenge killings
import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill
rng = random.Random(2805)
samp = rng.sample(rev, min(20, len(rev))) + rng.sample([r for r in rows if r not in rev], 10); rng.shuffle(samp)
wb = openpyxl.Workbook(); ws = wb.active; ws.title = "check"
H = ["#", "kid", "saga", "chapter", "killer", "victim", "AI: motive", "AI: avenges", "AI: revenge basis", "AI: avenger relation",
     "AI: evidence", "is the motive right? (yes/no)", "if revenge: is the avenged person right? (yes/no)", "is the relation right? (yes/no)", "note"]
ws.append(H)
for i, r in enumerate(samp, 1):
    ws.append([i, r["kid"], r["saga"], r["chapter"], r["killer"], r["victim"], r["motive"], r["avenges_person"], r["revenge_basis"],
               f"{r['avenger_relation']} [{r['relation_category']}]", r["evidence"], "", "", "", ""])
for i, wdt in enumerate([4, 8, 18, 7, 18, 18, 14, 18, 10, 26, 60, 12, 14, 12, 30], 1):
    ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = wdt
for c in ws[1]: c.font = Font(bold=True); c.alignment = Alignment(wrap_text=True)
for row in ws.iter_rows(min_row=2):
    for c in row: c.alignment = Alignment(wrap_text=True, vertical="top")
    for c in row[11:]: c.fill = PatternFill("solid", fgColor="FFF2CC")
g = wb.create_sheet("how to")
for l in [["What", "Check, from the saga text (sagadb.org, the chapter given), whether the AI got the motive and the revenge link right. Your own judgement; AI may only help you understand the old Icelandic."],
          ["Revenge", "A killing is revenge only if the text says so (hefna, hefnd, til hefnda, eftirmál) or it is unmistakable. Being on the hostile side is not enough."],
          ["Sample", "20 random killings the AI called revenge + 10 random killings it did not (seed 2805)."]]:
    g.append(l)
g.column_dimensions["A"].width = 10; g.column_dimensions["B"].width = 110
out = ROOT / "data/review/manual_check_revenge.xlsx"
if not out.exists():
    wb.save(out); print(f"\ncheck sheet written: {out.relative_to(ROOT)}")

# ---- figure: who avenges, and whom revenge strikes ----
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
INK, MUTED, GRID, ACCENT, LIGHT = "#1d2427", "#5b6669", "#d5dad6", "#24506b", "#c9cfcc"
fam = collections.Counter(e["layer"] for e in csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")) if e["layer"] in ("blood", "affinity", "foster"))
av = collections.Counter(low(r["relation_category"]) for r in rev)
kin_av = sum(av[t] for t in ("blood", "affinity", "foster")); tot_f = sum(fam.values())
# who gets avenged: share of victims avenged, by number of recorded blood relatives of the victim
import re as _re, random as _random
blood = collections.Counter()
for e in csv.DictReader(open(A / "family_edges.csv", encoding="utf-8")):
    if e["layer"] == "blood":
        blood[(e["saga"], e["a"])] += 1; blood[(e["saga"], e["b"])] += 1
_clean = lambda n: _re.sub(r"\s*\(.*?\)", "", n or "").strip()
avk = {r["avenges_kid"] for r in rev if r["avenges_kid"]}
avp = {(r["saga"], _clean(r["avenges_person"])) for r in rev if r["avenges_person"]}
avf = {(s_, p_.split()[0]) for s_, p_ in avp if p_}
def is_avenged(r):
    v = _clean(r["victim"])
    return r["kid"] in avk or (r["saga"], v) in avp or (r["saga"], v.split()[0] if v else "") in avf
bins = [(0, 0, "none"), (1, 2, "1–2"), (3, 5, "3–5"), (6, 999, "6 or more")]
vb = lambda r: blood[(r["saga"], r["victim"])]
dose = []
for lo, hi, lab_ in bins:
    sub = [r for r in rows if lo <= vb(r) <= hi]; a_ = sum(is_avenged(r) for r in sub)
    dose.append((lab_, a_, len(sub)))
# within-saga permutation test of (has blood kin) vs (none)
labs = [is_avenged(r) for r in rows]
def _d(L):
    g1 = [x for r, x in zip(rows, L) if vb(r) > 0]; g0 = [x for r, x in zip(rows, L) if vb(r) == 0]
    return sum(g1) / len(g1) - sum(g0) / len(g0)
obs_d = _d(labs); rng_ = _random.Random(2805); idx = collections.defaultdict(list)
for n_, r in enumerate(rows): idx[r["saga"]].append(n_)
nul = []
for _ in range(2000):
    L = labs[:]
    for ii in idx.values():
        v = [L[n_] for n_ in ii]; rng_.shuffle(v)
        for n_, x in zip(ii, v): L[n_] = x
    nul.append(_d(L))
p_dose = (sum(abs(x) >= abs(obs_d) for x in nul) + 1) / 2001
print("who gets avenged, by victim's recorded blood kin:", dose, f"difference {obs_d:.3f}, p = {p_dose:.4f}")
tg = collections.Counter(low(r["target"]) for r in rev)
tcats = [("the killer himself", "The killer himself"), ("killer's kin", "The killer's kin"), ("killer's household or ally", "The killer's household or ally")]
n_rev = len(rev)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(7.0, 2.3), gridspec_kw={"width_ratios": [1, 1]})
x = range(len(dose))
a1.bar(list(x), [100 * a_ / n_ for _, a_, n_ in dose], width=0.62, color=ACCENT)
for i, (_, a_, n_) in enumerate(dose):
    a1.text(i, 100 * a_ / n_ + 1.5, f"{100 * a_ / n_:.0f}%", ha="center", fontsize=7, color=INK, fontweight="bold")
a1.set_xticks(list(x), [f"{l}\n({a_}/{n_})" for l, a_, n_ in dose], fontsize=6.5, color=INK)
a1.set_ylim(0, 62); a1.set_ylabel("victims avenged (%)", fontsize=6.5, color=MUTED)
a1.set_xlabel("victim's recorded blood relatives", fontsize=6.5, color=MUTED, labelpad=4)
a1.set_title("A  Who gets avenged", fontsize=7.5, loc="left", color=INK)
a1.grid(axis="y", color=GRID, lw=0.5); a1.set_axisbelow(True)
a1.tick_params(axis="y", labelsize=6, colors=MUTED); a1.tick_params(axis="x", length=0, pad=3)
a1.spines[["top", "right", "left"]].set_visible(False); a1.spines["bottom"].set_color(GRID)
y2 = range(len(tcats))
a2.barh(list(y2), [tg[c] for c, _ in tcats], height=0.5, color=ACCENT)
for i, (c, _) in enumerate(tcats):
    a2.text(tg[c] + 0.8, i, f"{tg[c]} ({tg[c] / n_rev:.0%})", va="center", fontsize=6.5, color=INK)
a2.set_yticks(list(y2), [l for _, l in tcats], fontsize=7, color=INK); a2.invert_yaxis()
a2.set_xlabel("revenge killings", fontsize=6.5, color=MUTED)
a2.set_title(f"B  Whom revenge strikes (n = {n_rev})", fontsize=7.5, loc="left", color=INK)
a2.set_xlim(0, max(tg.values()) * 1.25)
a2.tick_params(axis="x", labelsize=6, colors=MUTED); a2.tick_params(axis="y", length=0)
a2.grid(axis="x", color=GRID, lw=0.5); a2.set_axisbelow(True)
a2.spines[["top", "right", "left"]].set_visible(False); a2.spines["bottom"].set_color(GRID)
fig.tight_layout(); fig.savefig(FIG / "revenge.png", dpi=300, bbox_inches="tight"); fig.savefig(FIG / "revenge.pdf", bbox_inches="tight")
print("saved figures/revenge.png")
