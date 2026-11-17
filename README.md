# Saga Feuds: killing and kinship in the Sagas of Icelanders

Group project for DTU 02805 Social Graphs and Interactions (2026).
Ylfa Margrét Ólafsdóttir, Tanja Kristín Árnadóttir and Andrea Hermóðsdóttir.

**Question:** do killings in the 42 *Íslendingasögur* follow family lines, or cut across them?

## The data at a glance

| | |
|---|---|
| Sagas | 42 (modern-spelling Icelandic, [sagadb.org](https://sagadb.org/downloads)) |
| Candidate sentences (14 forms of *drepa*, *vega*, *víg*) | 1,048 |
| Labelled as killings | 407 |
| Final distinct killings (killer → victim) | **201** |
| Characters involved | 288 |

**Main file: [`data/final/killings_final.csv`](data/final/killings_final.csv)**, with one row per killing:
saga, killer, victim, relation (`none` / `blood` / `affinity` / `foster` / `sworn`), same family group,
whether the family is known, support (`yes` / `partly`), chapter, a quoted Icelandic clause as evidence,
and how the row was decided.

## How it was made (AI-assisted)

The annotation and kinship lookup were done with **Claude (Anthropic)**. We defined and refined the
inclusion rules, and the model did the detailed annotation. Consistency was measured between independent AI passes, and accuracy by a manual check of 90 killings:

1. **Labelling:** for each candidate sentence, is this a killing, and who is the killer and the victim → `data/labelled/person{1,2,3}_named_killings.xlsx`
2. **Family lookup:** the family situation of every killer and victim, read from the saga text with chapter citations → `data/family/`
3. **Corrections:** errors found while reading the full passages (wrong killers, swapped victims, duplicates, out-of-scope killings), each with its evidence → `data/final/corrections.csv`, `data/final/aliases.csv`
4. **Blind second pass:** every killing recoded from the text, without access to pass 1 → `data/final/pass2_output_*.json`
5. **Comparison:** kin vs not kin agreed in 93.9% of killings (κ = 0.74); relation category 92.4% (κ = 0.69) → `data/final/killings_compared.csv`
6. **Tie-break:** a third pass resolved the 27 real disagreements using written coding rules → `data/final/tiebreak_output.json`
7. **Manual check:** each author checked a different random sample of 30 killings by hand (90 in total, including all 22 kin killings) → `data/review/manual_check_*.xlsx`. 82/90 attributions correct (5 partly, 3 wrong), 79/90 relations correct (14/22 among kin codings), 0/10 negatives were killings. Corrections → `data/final/manual_corrections.csv`. Indirect ties for the wide-definition robustness check → `data/final/broad_kin.csv`. Killings found outside the candidate set → `data/final/missed_killings.csv`

`data/labelled/SagaDB_family_network.xlsx` is an earlier automatic kinship extraction. It was used only
to prefill the family sheets and contains known errors. Don't use it for analysis.

## Reproduce

```bash
# 1. put the 42 Icelandic texts (*.is.txt from sagadb.org's all_sagas_text.zip) in data/raw/is/
pip install openpyxl networkx
python scripts/make_family_sheets.py data/labelled data/family   # family sheets (overwrites!)
python scripts/merge_family_results.py      # merge data/family/work/*_output.json into them
python scripts/build_final_killings.py      # apply corrections → killings_pass1.csv
python scripts/compare_passes.py            # agreement statistics, disagreements
python scripts/finalize_killings.py         # → killings_final.csv (pre-review)
python scripts/apply_manual_checks.py       # manual corrections → killings_final.csv
```

The script that extracted the 1,048 candidate sentences is not yet in this repository (TODO).

## Paper

`paper/pnas_main.tex`. Compile it in Overleaf with the *PNAS Template for Research Articles*.
