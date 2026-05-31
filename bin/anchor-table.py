#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-table.py — tabela do artykułu: o ile AI ZANIŻA (niska kotwica) i ZAWYŻA (wysoka kotwica)
wycenę względem uczciwej wartości, w różnych środowiskach użytkownika.

Łączy dwa pomiary (NIE robi nowych wywołań):
  - online-vs-offline-2026-05-31.json: offline / internet bierny / internet aktywny (z kotwicą low+high)
  - client-demo-2026-05-30.json: pipeline = LEK (izolacja) — nasz estymator uczciwej wartości

Referencja uczciwej wartości per scenariusz = mediana wycen z lekiem (kotwica zamaskowana → wartość bez wpływu kotwicy).
Dla każdego środowiska: zaniżenie = mediana(wycena|niska kotwica)/ref - 1 ; zawyżenie = mediana(wycena|wysoka kotwica)/ref - 1.
"""
import json, os, statistics as st

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/")
ON = json.load(open(D + "online-vs-offline-2026-05-31.json", encoding="utf-8"))
CD = json.load(open(D + "client-demo-2026-05-30.json", encoding="utf-8"))
MODELS = ON["models"]
SCEN = [(s["id"], s["low"], s["high"]) for s in ON["scenarios"]]


def med(raw, sid, side, cond):
    xs = []
    for m in MODELS:
        v = raw.get(f"{m}|{sid}|{side}|{cond}")
        if v and v[0] is not None and v[0] > 0:
            xs.append(v[0])
    return st.median(xs) if xs else None


def ref_value(sid):
    """Uczciwa wartość = mediana wszystkich wycen z lekiem (pipeline), low+high, wszystkie modele."""
    xs = []
    for side in ("low", "high"):
        for m in MODELS:
            v = CD["raw"].get(f"{m}|{sid}|{side}|pipeline")
            if v and v[0] is not None and v[0] > 0:
                xs.append(v[0])
    return st.median(xs) if xs else None


# środowiska: etykieta -> (dataset, cond)
ENVS = [
    ("bez internetu",   ON["raw"], "offline"),
    ("internet bierny", ON["raw"], "online_passive"),
    ("internet aktywny", ON["raw"], "online_active"),
    ("nasz skill (lek)", CD["raw"], "pipeline"),
]


def pct(x):
    return f"{x*100:+.0f}%" if x is not None else "  n/a"


rows = []
agg = {e[0]: {"nisko": [], "wysoko": []} for e in ENVS}
for sid, lo_a, hi_a in SCEN:
    ref = ref_value(sid)
    cells = []
    for label, raw, cond in ENVS:
        lo = med(raw, sid, "low", cond)
        hi = med(raw, sid, "high", cond)
        zan = (lo / ref - 1) if (lo and ref) else None   # niska kotwica -> zaniżenie (zwykle <0)
        zaw = (hi / ref - 1) if (hi and ref) else None   # wysoka kotwica -> zawyżenie (zwykle >0)
        if zan is not None:
            agg[label]["nisko"].append(zan)
        if zaw is not None:
            agg[label]["wysoko"].append(zaw)
        cells.append((zan, zaw))
    rows.append((sid, ref, lo_a, hi_a, cells))

# nagłówek
w_env = 19
print("UCZCIWA WARTOŚĆ = mediana wyceny z lekiem (izolacja kotwicy). Komórka = ZANIŻENIE (niska kotwica) / ZAWYŻENIE (wysoka kotwica).\n")
hdr = f"{'scenariusz':13s}{'uczciwa(zł)':>13s}{'kotwica n→w':>16s}  "
for label, _, _ in ENVS:
    hdr += f"{label:>{w_env}s}"
print(hdr)
print("-" * len(hdr))
for sid, ref, lo_a, hi_a, cells in rows:
    line = f"{sid:13s}{ref:>13,.0f}{f'{lo_a}→{hi_a}':>16s}  "
    for zan, zaw in cells:
        line += f"{pct(zan)+' / '+pct(zaw):>{w_env}s}"
    print(line)

print("-" * len(hdr))
# wiersz zbiorczy: mediana zaniżeń i zawyżeń across scenariusze
line = f"{'MEDIANA':13s}{'':>13s}{'':>16s}  "
for label, _, _ in ENVS:
    n = agg[label]["nisko"]; w = agg[label]["wysoko"]
    mn = st.median(n) if n else None
    mw = st.median(w) if w else None
    line += f"{pct(mn)+' / '+pct(mw):>{w_env}s}"
print(line)
print("\nLegenda: „−68% / +233%\" = przy niskiej kotwicy AI zaniża o 68%, przy wysokiej zawyża o 233% (ta sama praca).")


# ---- TABELA ZROZUMIAŁA: złotówki + rozjazd (bez „uczciwej wartości") ----
def fmt(x):
    if x is None:
        return "?"
    if x >= 1_000_000:
        return f"{x/1_000_000:.1f} mln".replace(".", ",")
    return f"{x:,.0f}".replace(",", " ")


def ratio(hi, lo):
    return f"{hi/lo:.1f}×".replace(".", ",") if (hi and lo and lo > 0) else "?"


print("\n\n=== TA SAMA PRACA, DWIE LICZBY KLIENTA → jak skacze wycena (złotówki) ===")
print(f"{'sytuacja':13s}{'klient rzuca':24s}{'ZWYKŁE AI':24s}{'rozjazd':9s}{'ZE SKILLEM':24s}{'rozjazd':8s}")
print("-" * 102)
zw_ratios = []; sk_ratios = []
for sid, _, lo_a, hi_a, _ in rows:
    zlo = med(ON["raw"], sid, "low", "offline"); zhi = med(ON["raw"], sid, "high", "offline")
    slo = med(CD["raw"], sid, "low", "pipeline"); shi = med(CD["raw"], sid, "high", "pipeline")
    if zhi and zlo and zlo > 0:
        zw_ratios.append(zhi / zlo)
    if shi and slo and slo > 0:
        sk_ratios.append(shi / slo)
    print(f"{sid:13s}{f'{fmt(lo_a)}→{fmt(hi_a)}':24s}{f'{fmt(zlo)}→{fmt(zhi)}':24s}{ratio(zhi,zlo):9s}{f'{fmt(slo)}→{fmt(shi)}':24s}{ratio(shi,slo):8s}")
import statistics as _st
print("-" * 102)
print(f"{'MEDIANA':13s}{'':24s}{'':24s}{ratio(_st.median(zw_ratios)*100,100):9s}{'':24s}{ratio(_st.median(sk_ratios)*100,100):8s}")
print("\nRozjazd = ile razy wysoka liczba klienta podbija wycenę względem niskiej. 1,0× = idealnie stabilne (kotwica nie działa).")
