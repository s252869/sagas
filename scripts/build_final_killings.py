"""Apply data/final/corrections.csv + aliases.csv to the pass-1 killings (family sheets)
and write data/final/killings_pass1.csv (one row per distinct killer->victim pair)
and data/final/pass2_input.json (blind input for the independent second pass)."""
import csv, json, re
from pathlib import Path
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
FIN = ROOT / "data/final"
corr = {(r["saga"], r["killer"], r["victim"]): r for r in csv.DictReader(open(FIN / "corrections.csv", encoding="utf-8"))}
alias = {(r["saga"], r["name"]): r["canonical"] for r in csv.DictReader(open(FIN / "aliases.csv", encoding="utf-8"))}
canon = lambda s, n: alias.get((s, n.strip()), n.strip())

out, seen, used = [], {}, set()
for p in ["person1", "person2", "person3"]:
    ws = openpyxl.load_workbook(ROOT / f"data/family/{p}_family.xlsx", read_only=True)["killings"]
    rows = list(ws.iter_rows(values_only=True)); h = rows[0]
    for r in rows[1:]:
        d = dict(zip(h, r))
        key = (d["saga"], d["killer"], d["victim"])
        c = corr.get(key)
        pairs, changed, reason = [(d["killer"], d["victim"])], "", ""
        if c:
            used.add(key)
            reason = c["reason"]
            if c["action"] == "drop":
                continue
            pairs = [(k.strip(), c["new_victim"]) for k in c["new_killer"].split(";")]
            changed = "corrected"
        for k, v in pairs:
            k, v = canon(d["saga"], k), canon(d["saga"], v)
            pk = (d["saga"], k, v)
            src = re.findall(r"ch\.? ?\d+", str(d["source"] or ""))
            if pk in seen:  # merged duplicate (e.g. alias collapsed two rows)
                seen[pk]["n_sentences"] += d["n_sentences"] or 0
                continue
            row = {"saga": d["saga"], "killer": k, "victim": v, "annotator": p,
                   "n_sentences": d["n_sentences"] or 0, "first_sentence_id": d["first_sentence_id"],
                   "chapter_hint": ", ".join(dict.fromkeys(src))[:40],
                   "relation_p1": "" if changed else (d["relation_killer_to_victim"] or ""),
                   "same_group_p1": "" if changed else (d["same_family_group?"] or ""),
                   "correction": changed, "correction_reason": reason, "notes_p1": d["notes"] or ""}
            seen[pk] = row; out.append(row)

missing = set(corr) - used
if missing:
    print("!! corrections that matched nothing:", missing)
for i, r in enumerate(out, 1):
    r["kid"] = f"KL{i:03d}"
cols = ["kid", "saga", "killer", "victim", "annotator", "n_sentences", "first_sentence_id", "chapter_hint",
        "relation_p1", "same_group_p1", "correction", "correction_reason", "notes_p1"]
with open(FIN / "killings_pass1.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(out)
blind = [{k: r[k] for k in ("kid", "saga", "killer", "victim", "first_sentence_id")} for r in out]
json.dump(blind, open(FIN / "pass2_input.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(f"{len(out)} killings ({sum(1 for r in out if r['correction'])} corrected), "
      f"{len(corr) - sum(1 for c in corr.values() if c['action']!='drop')} dropped")
