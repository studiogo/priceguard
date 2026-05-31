#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-stats.py — przedziały ufności (bootstrap 95%) dla wyników anty-zakotwiczenia.
Czyta gotowe JSON-y z biegów (bez nowych zapytań), liczy medianę A-Index i medianę
zawyżenia (odp_wysoka/odp_niska) z 95% CI per warunek.
"""
import json, random, statistics as st, os, sys
random.seed(42)
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")


def boot_ci(vals, n=5000):
    if not vals:
        return (float("nan"), float("nan"), float("nan"), 0)
    base = st.median(vals)
    L = len(vals)
    bs = []
    for _ in range(n):
        s = [vals[random.randrange(L)] for _ in range(L)]
        bs.append(st.median(s))
    bs.sort()
    return (base, bs[int(0.025 * n)], bs[int(0.975 * n)], L)


def collect(path, q_field, unwrap):
    d = json.load(open(path))
    qs = {q["id"]: q for q in d[q_field]}
    raw = d["raw"]
    tmp = {}
    for k, v in raw.items():
        p = k.split("|")
        if q_field == "hard":
            if p[0] != "hard":
                continue
            _, m, qid, side, cond = p
        else:
            m, qid, side, cond = p
        val = unwrap(v)
        if val is None:
            continue
        tmp.setdefault((cond, m, qid), {})[side] = val
    A, S = {}, {}
    for (cond, m, qid), sd in tmp.items():
        if "low" in sd and "high" in sd and qid in qs:
            denom = abs(qs[qid]["high"] - qs[qid]["low"])
            if denom:
                A.setdefault(cond, []).append(abs(sd["high"] - sd["low"]) / denom)
            if sd["low"] and sd["low"] > 0:
                S.setdefault(cond, []).append(sd["high"] / sd["low"])
    return A, S


def merge(*dicts):
    out = {}
    for d in dicts:
        for k, v in d.items():
            out.setdefault(k, []).extend(v)
    return out


def show(title, A, S, conds):
    print(f"\n=== {title} ===")
    print(f"{'warunek':24s}{'mediana A-Index [95% CI]':30s}{'mediana zawyzenia [95% CI]':32s}{'n'}")
    print("-" * 92)
    for c in conds:
        a, alo, ahi, n = boot_ci(A.get(c, []))
        s, slo, shi, _ = boot_ci(S.get(c, []))
        ai = f"{a:.3f} [{alo:.3f}; {ahi:.3f}]"
        sw = f"+{(s-1)*100:.0f}% [{(slo-1)*100:.0f}%; {(shi-1)*100:.0f}%]"
        print(f"{c:24s}{ai:30s}{sw:32s}{n}")


# KROK 1 — scal panel tani + frontier
a1, s1 = collect(f"{D}/spike-results-2026-05-30.json", "questions", lambda v: v)
a2, s2 = collect(f"{D}/spike-results-2026-05-30-frontier.json", "questions", lambda v: v)
show("KROK 1 — jawna kotwica (8 modeli, 5 laboratoriow)",
     merge(a1, a2), merge(s1, s2), ["baseline", "ignore", "opposite", "blind"])

# KROK 2 — kotwica wbudowana
a3, s3 = collect(f"{D}/krok2-results-2026-05-30.json", "hard", lambda v: v[0] if isinstance(v, list) else v)
show("KROK 2 — kotwica wbudowana w tekst (3 modele)",
     a3, s3, ["baseline", "ignore", "opposite", "pipeline"])

print("\n(A-Index nizej=lepiej; zawyzenie = o ile odp. przy wysokiej kotwicy > przy niskiej; CI = bootstrap 5000x)")
