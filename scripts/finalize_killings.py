"""Combine pass 1, blind pass 2 and the tie-break into data/final/killings_final.csv.

Decision rule per killing:
  - tie-break exists            -> tie-break decision
  - corrected pair (no pass 1)  -> pass 2
  - otherwise (passes agree, counting 'unknown' as 'none') -> pass 1
'unknown' relations become 'none' with family_known = no (reported separately in the analysis).
"""
import csv, json, collections
from pathlib import Path

FIN = Path(__file__).resolve().parents[1] / "data/final"
rows = list(csv.DictReader(open(FIN / "killings_compared.csv", encoding="utf-8")))
tb = {r["kid"]: r for r in json.loads((FIN / "tiebreak_output.json").read_text(encoding="utf-8"))}
DROP = {"KL201": "duplicate of KL203 (Þorsteins saga hvíta ch 7: the brothers killed Þorgils together)"}

cat = lambda s: (str(s or "").split(":")[0].split("(")[0].strip().lower() or "none")
yn = lambda s: {"yes": "yes", "no": "no"}.get(str(s or "").strip().lower()[:3].rstrip(), "unknown")
out, src = [], collections.Counter()
for r in rows:
    if r["kid"] in DROP:
        continue
    if r["kid"] in tb:
        t = tb[r["kid"]]; rel, detail, grp, how = cat(t["relation"]), t["relation_detail"], yn(t["same_group"]), "tie-break"
    elif r["correction"]:
        rel, detail, grp, how = cat(r["relation_p2"]), r["relation_detail_p2"], yn(r["same_group_p2"]), "pass 2 (corrected pair)"
    else:
        rel, detail, grp, how = cat(r["relation_p1"]), r["relation_p1"], yn(r["same_group_p1"]), "both passes agree"
    family_known = "no" if (cat(r["relation_p2"]) == "unknown" and rel in ("none", "unknown")) else "yes"
    rel = "none" if rel == "unknown" else rel
    src[how] += 1
    out.append({"kid": r["kid"], "saga": r["saga"], "killer": r["killer"], "victim": r["victim"],
                "relation": rel, "relation_detail": detail, "same_group": grp, "family_known": family_known,
                "support": "partly" if r["supported_p2"].startswith("part") else "yes",
                "chapter": r["chapter_p2"], "evidence": r["evidence_p2"], "decided_by": how,
                "correction": r["correction_reason"], "annotator": r["annotator"]})
with open(FIN / "killings_final.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, list(out[0])); w.writeheader(); w.writerows(out)
print(f"{len(out)} final killings; decided by {dict(src)}")
print("relation:", dict(collections.Counter(r["relation"] for r in out)))
print("same_group:", dict(collections.Counter(r["same_group"] for r in out)))
print("family_known:", dict(collections.Counter(r["family_known"] for r in out)),
      "| support:", dict(collections.Counter(r["support"] for r in out)))
print("people:", len({(r["saga"], n) for r in out for n in (r["killer"], r["victim"])}))
