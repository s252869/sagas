"""Build the person table and the family graph used by SQ1 and SQ2.

Nodes are (saga, name). Sources:
  - data/final/killings_final.csv            killers and victims (the people we analyse)
  - data/family/person{1,2,3}_family.xlsx    'people' tab: kin columns + family_group (AI, chapter-cited)
Kin columns hold strings like "Hámundur; Rannveig (ch 19)". Parenthetical notes are stripped.
Layers: blood (parents, children, siblings), affinity (spouses, in-laws), foster (foster/sworn),
        other (other_kin, e.g. frændi of unspecified degree).
Writes data/analysis/persons.csv and data/analysis/family_edges.csv.
"""
import csv, re, collections
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
import os
KILLINGS = os.environ.get("KILLINGS", "killings_all.csv")   # killings_final.csv = original keyword set only

OUT = ROOT / "data/analysis"; OUT.mkdir(parents=True, exist_ok=True)
alias = {(r["saga"], r["name"]): r["canonical"] for r in csv.DictReader(open(ROOT / "data/final/aliases.csv", encoding="utf-8"))}
canon = lambda s, n: alias.get((s, n), n)

COLS = {"parents (father; mother)": "blood", "siblings": "blood", "children": "blood",
        "spouses": "affinity", "in_laws": "affinity", "foster_sworn": "foster", "other_kin": "other"}


def names(cell):
    out = []
    for part in re.split(r"[;|]", str(cell or "")):
        part = re.sub(r"\([^)]*\)", "", part)          # drop "(ch 19)", "(inferred ...)"
        part = re.sub(r"\[[^\]]*\]", "", part)
        part = part.split(":")[-1] if ":" in part else part
        part = re.sub(r"\b(ch|kafli)\.? ?\d+.*$", "", part).strip(" ,.-–")
        if part and part[0].isupper() and len(part) < 40 and part.lower() not in ("none", "unknown", "n/a"):
            out.append(part)
    return out


def norm_group(g):
    g = re.sub(r"\((follower|slave|servant|thrall|household|retainer)[^)]*\)", "", str(g or ""), flags=re.I)
    g = re.sub(r"\s+", " ", g).strip(" ,;/").lower()
    return "" if g in ("", "none", "unknown", "not found", "ambiguous") or g.startswith("ambiguous") else g


persons, edges = {}, set()
for p in ["person1", "person2", "person3"]:
    ws = openpyxl.load_workbook(ROOT / f"data/family/{p}_family.xlsx", read_only=True)["people"]
    rows = list(ws.iter_rows(values_only=True)); h = rows[0]
    for r in rows[1:]:
        d = dict(zip(h, r)); saga = d["saga"]; me = canon(saga, d["person"])
        persons[(saga, me)] = {"saga": saga, "name": me, "family_group": norm_group(d["family_group (kin group / household)"]),
                               "status": d["status"] or ""}
        for col, layer in COLS.items():
            for n in names(d[col]):
                n = canon(saga, n)
                if n != me:
                    edges.add((saga, *sorted([me, n]), layer))

import json as _json
_np = ROOT / "data/extension/new_people.json"
if KILLINGS == "killings_all.csv" and _np.exists():
    for d in _json.loads(_np.read_text(encoding="utf-8")):
        saga = d["saga"]; me = canon(saga, d["name"])
        if (saga, me) not in persons:
            persons[(saga, me)] = {"saga": saga, "name": me, "family_group": norm_group(d.get("family_group")), "status": d.get("status") or ""}
        for col, layer in {"parents": "blood", "siblings": "blood", "children": "blood", "spouses": "affinity", "in_laws": "affinity",
                           "foster_sworn": "foster", "other_kin": "other"}.items():
            for n in names(d.get(col)):
                n = canon(saga, n)
                if n != me:
                    edges.add((saga, *sorted([me, n]), layer))

kill = list(csv.DictReader(open(ROOT / "data/final" / KILLINGS, encoding="utf-8")))
part = {(r["saga"], n) for r in kill for n in (r["killer"], r["victim"])}
for key in part:
    persons.setdefault(key, {"saga": key[0], "name": key[1], "family_group": "", "status": "not in family sheets"})
for key, v in persons.items():
    v["in_killing_network"] = "yes" if key in part else "no"

with open(OUT / "persons.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, ["saga", "name", "family_group", "status", "in_killing_network"]); w.writeheader()
    w.writerows(v for k, v in sorted(persons.items()) if k in part)
with open(OUT / "family_edges.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f); w.writerow(["saga", "a", "b", "layer"]); w.writerows(sorted(edges))

grp = [k for k in part if persons[k]["family_group"]]
print(f"killing participants: {len(part)}; with a family group: {len(grp)} ({len(grp)/len(part):.0%})")
print("missing group:", sorted(f"{s[:10]}:{n}" for s, n in part - set(grp))[:40])
print(f"family edges: {len(edges)} ({dict(collections.Counter(e[3] for e in edges))})")
nodes = {(e[0], e[1]) for e in edges} | {(e[0], e[2]) for e in edges}
print(f"family-graph nodes: {len(nodes)}; participants in graph: {len(part & nodes)}")
