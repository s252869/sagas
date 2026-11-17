"""Integrate the verified extension killings (data/extension/r2_output_*.json) with the original dataset.
out: data/final/killings_all.csv        original 194 (source=original) + kept new killings (source=extension)
     data/extension/new_people.json     family records of new people (read by build_family_graph.py)
     data/feuds/feud_output_ext.json    feud/motive annotation of new killings (read by feud_analysis.py)
     data/extension/integration_log.csv every new killing with its decision"""
import csv, json, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E, FIN = ROOT / "data/extension", ROOT / "data/final"
orig = list(csv.DictReader(open(FIN / "killings_final.csv", encoding="utf-8")))
newk = {r["kid"]: r for r in csv.DictReader(open(E / "new_killings.csv", encoding="utf-8"))}
r2k, people, feuds_new = {}, [], {}
for f in sorted(E.glob("r2_output_*.json")):
    d = json.loads(f.read_text(encoding="utf-8"))
    for k in d.get("killings", []):
        r2k[k["kid"]] = k
    people += d.get("people", [])
missing = set(newk) - set(r2k)
print(f"verified {len(r2k)}/{len(newk)} new killings" + (f"; MISSING {len(missing)}" if missing else ""))
low = lambda x: str(x or "").strip().lower()
cat = lambda x: low(x).split(":")[0].split("(")[0].strip() or "none"

# status of people (for family_known)
status = {}
for p in csv.DictReader(open(ROOT / "data/analysis/persons.csv", encoding="utf-8")):
    status[(p["saga"], p["name"])] = p["status"]
for p in people:
    status[(p["saga"], p["name"])] = p.get("status", "")

log, rows, seen = [], [], {(r["saga"], r["killer"], r["victim"]) for r in orig}
# original killings that are passing references to killings the extension captures where they are narrated in full
REPLACED = {"KL126": "Grettis ch 27 mention of the Hundadalur killing narrated in Fóstbræðra ch 8 (KN234)",
            "KL127": "Grettis ch 27 mention of the Hundadalur killing narrated in Fóstbræðra ch 8 (KN233)",
            "KL169": "Eyrbyggja mention of Gísli's death narrated in Gísla saga (KN106)"}
for r in orig:
    if r["kid"] in REPLACED:
        log.append({"kid": r["kid"], "saga": r["saga"], "killer": r["killer"], "victim": r["victim"], "decision": "dropped: cross-saga duplicate",
                    "duplicate_of": "", "note": REPLACED[r["kid"]]})
        continue
    rows.append({**r, "source": "original"})
cols = list(rows[0])
dec = collections.Counter()
for kid, b in newk.items():
    a = r2k.get(kid, {})
    d = low(a.get("decision")) or "unverified"
    k, v = a.get("killer") or b["killer"], a.get("victim") or b["victim"]
    if d == "keep" and (b["saga"], k, v) in seen:
        d = "duplicate (after name correction)"
    dec[d] += 1
    log.append({"kid": kid, "saga": b["saga"], "killer": k, "victim": v, "decision": d, "duplicate_of": a.get("duplicate_of", ""), "note": a.get("note", "")})
    if d != "keep":
        continue
    seen.add((b["saga"], k, v))
    rel = cat(a.get("relation"))
    rel = rel if rel in ("blood", "affinity", "foster", "sworn") else "none"
    fk = "no" if any(low(status.get((b["saga"], x), "")).startswith("not found") for x in (k, v)) else "yes"
    rows.append({c: "" for c in cols} | {
        "kid": kid, "saga": b["saga"], "killer": k, "victim": v, "relation": rel, "relation_detail": a.get("relation_detail", ""),
        "same_group": low(a.get("same_group")) if low(a.get("same_group")) in ("yes", "no") else "unknown", "family_known": fk,
        "support": "partly" if low(a.get("support")).startswith("part") else "yes", "chapter": a.get("chapter") or b["chapter"],
        "evidence": a.get("evidence", ""), "decided_by": "extension: AI labelling + AI verification", "correction": "",
        "annotator": "extension", "relation_broad": rel if rel != "none" else "none", "kin_broad": "yes" if rel != "none" else "no",
        "manually_checked_by": "", "source": "extension"})
with open(FIN / "killings_all.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, cols); w.writeheader(); w.writerows(rows)
with open(E / "integration_log.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.DictWriter(fh, list(log[0])); w.writeheader(); w.writerows(log)
json.dump(people, open(E / "new_people.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

# feud annotation in the format of feud_output_*.json
FK = ["feud_id", "feud_name", "feud_type", "killer_side", "victim_side", "motive", "avenges_kid", "avenges_person", "revenge_basis",
      "avenger_relation", "relation_category", "target", "evidence", "settled_after", "confidence", "note"]
fk_out, fset = [], {}
for r in rows:
    if r["source"] != "extension":
        continue
    a = r2k[r["kid"]]
    fk_out.append({"kid": r["kid"], **{k: a.get(k, "") for k in FK}})
    fid = a.get("feud_id", "")
    if fid and "_N" in fid and fid not in fset:
        fset[fid] = {"feud_id": fid, "saga": r["saga"], "feud_name": a.get("feud_name", ""), "feud_type": "feud", "n_killings": 0}
json.dump({"killings": fk_out, "feuds": list(fset.values())}, open(ROOT / "data/feuds/feud_output_ext.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("decisions:", dict(dec))
n_new = sum(1 for r in rows if r["source"] == "extension")
print(f"combined dataset: {len(rows)} killings ({len(orig)} original + {n_new} new); new people records: {len(people)}")
print("new killings by relation:", dict(collections.Counter(r["relation"] for r in rows if r["source"] == "extension")))
