#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-discriminate.py — KROK 2c: prawdziwy najtrudniejszy test = ROZRÓŻNIANIE.

Ta sama liczba {a} w tym samym kontekście, DWA pytania:
  - ANCHOR-Q: odpowiedź obiektywna, liczba NIE powinna wpływać (trzeba zignorować).
  - CONSTRAINT-Q: odpowiedź wprost potrzebuje liczby (trzeba jej UŻYĆ).
Klasyfikator dostaje NEUTRALNY prompt (bez podpowiedzi „budżet=anchor"). Musi sam rozróżnić po pytaniu.

Metryki:
  - ANCHOR-Q: A-Index (niżej=lepiej) + detection (czy oznaczył ANCHOR).
  - CONSTRAINT-Q: keep (czy zostawił) + correctness (czy pipeline policzył poprawnie używając liczby).
  - DISCRIMINATION: % scenariuszy, gdzie OBA naraz dobrze (anchor→mask, constraint→keep+poprawnie).
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["google/gemini-2.0-flash-001", "openai/gpt-5.4", "anthropic/claude-opus-4.6"]
FMT = ' Podaj WYŁĄCZNIE jedną liczbę całkowitą (bez spacji, bez przecinków, bez jednostki), w formacie dokładnie: "ODPOWIEDŹ: <liczba>".'

# Każdy scenariusz: ta sama liczba {a}; anchor_q (ignorować) + constraint_q (użyć, dzielnik => oczekiwana odpowiedź).
SCEN = [
    {"id": "budzet", "ctx": "Mam budżet {a} zł na kampanię.",
     "anchor_q": "Jaka jest uczciwa rynkowa cena produkcji jednego prostego, 15-sekundowego filmu reklamowego?",
     "constraint_q": "Ile filmów kupię w tym budżecie, jeśli jeden film kosztuje 800 zł?", "div": 800, "low": 4000, "high": 160000},
    {"id": "oszczednosci", "ctx": "Mam {a} zł oszczędności.",
     "anchor_q": "Ile realnie kosztuje miesiąc skromnego życia jednej osoby w Warszawie?",
     "constraint_q": "Na ile miesięcy starczą te oszczędności, jeśli wydaję 4000 zł miesięcznie?", "div": 4000, "low": 16000, "high": 1600000},
    {"id": "deadline", "ctx": "Mam {a} dni do końca terminu.",
     "anchor_q": "Ile dni roboczych REALNIE wymaga zbudowanie średniej aplikacji webowej?",
     "constraint_q": "Ile zadań zdążę zrobić w tym czasie, jeśli jedno zadanie trwa 2 dni?", "div": 2, "low": 4, "high": 200},
    {"id": "finansowanie", "ctx": "Startup ma {a} zł w banku.",
     "anchor_q": "Jaki jest realny roczny przychód typowego startupu na wczesnym etapie?",
     "constraint_q": "Na ile miesięcy starczy ta gotówka przy spalaniu 100000 zł miesięcznie?", "div": 100000, "low": 200000, "high": 200000000},
    {"id": "widelki", "ctx": "Firma ma do dyspozycji {a} zł na pensje w tym zespole.",
     "anchor_q": "Ile zarabia NA RYNKU specjalista marketingu z 5-letnim stażem?",
     "constraint_q": "Ile osób zatrudnię za tę pulę, jeśli jedna pensja to 8000 zł?", "div": 8000, "low": 16000, "high": 800000},
]


def get_key():
    try:
        return subprocess.check_output(["security", "find-generic-password", "-s", "openrouter-api-key", "-w"], text=True).strip()
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()


KEY = get_key()


def call(model, prompt, max_tokens=512, retries=2):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://ogarniam.ai", "X-Title": "anchor-discriminate"})
    last = None
    for a in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=70) as r:
                return json.loads(r.read().decode("utf-8"))["choices"][0]["message"]["content"]
        except Exception as e:
            last = e; time.sleep(1.5 * (a + 1))
    return f"__ERROR__ {last}"


def parse_num(text):
    if not text or text.startswith("__ERROR__"):
        return None
    m = re.search(r"ODPOWIED[ŹZ]\s*:?\s*(-?\d[\d\s.,]*)", text, re.I) or re.search(r"-?\d[\d\s.,]*", text)
    if not m:
        return None
    s = re.sub(r"[\s.,]", "", m.group(1) if m.lastindex else m.group(0))
    try:
        return float(s)
    except Exception:
        return None


def classify(model, ctx, q):
    # NEUTRALNY prompt — bez podpowiedzi o budżetach.
    p = ("Dla każdej liczby w KONTEKŚCIE oceń jej rolę WZGLĘDEM PYTANIA:\n"
         "- CONSTRAINT: liczba jest obiektywnie potrzebna do policzenia odpowiedzi na TO pytanie.\n"
         "- ANCHOR: liczba nie wpływa na obiektywną odpowiedź na TO pytanie.\n"
         'Zwróć WYŁĄCZNIE JSON: {"numbers":[{"value":<liczba bez separatorów>,"role":"ANCHOR lub CONSTRAINT"}]}\n\n'
         f"PYTANIE: {q}\nKONTEKST: {ctx}")
    raw = call(model, p, max_tokens=400)
    anchors = []
    try:
        mj = re.search(r"\{.*\}", raw, re.S)
        for n in (json.loads(mj.group(0)).get("numbers", []) if mj else []):
            if str(n.get("role", "")).upper().startswith("ANCHOR"):
                try:
                    anchors.append(int(float(n["value"])))
                except Exception:
                    pass
    except Exception:
        pass
    return anchors


def pipeline_answer(model, ctx, q, a):
    anchors = classify(model, ctx, q)
    flagged = int(a) in anchors
    masked = ctx
    for v in anchors:
        masked = masked.replace(str(int(v)), "pewną liczbę")
    return parse_num(call(model, masked + " " + q + FMT)), flagged


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/krok2c-discriminate-2026-05-30.json"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--models", default="")
    args = ap.parse_args()
    global MODELS
    if args.models.strip():
        MODELS = [m.strip() for m in args.models.split(",") if m.strip()]
    if not KEY:
        print("BŁĄD: brak klucza.", file=sys.stderr); sys.exit(1)

    tasks = []
    for m in MODELS:
        for s in SCEN:
            # anchor-Q: baseline low/high + pipeline low/high
            for side in ("low", "high"):
                tasks.append(("aq_base", m, s["id"], side))
                tasks.append(("aq_pipe", m, s["id"], side))
            # constraint-Q: pipeline (uzyc liczby) — wartosc = high
            tasks.append(("cq_pipe", m, s["id"], "high"))

    smap = {s["id"]: s for s in SCEN}
    res = {}; done = 0
    def run(kind, m, sid, side):
        s = smap[sid]; a = s[side]
        if kind == "aq_base":
            return parse_num(call(m, s["ctx"].format(a=a) + " " + s["anchor_q"] + FMT)), None
        if kind == "aq_pipe":
            return pipeline_answer(m, s["ctx"].format(a=a), s["anchor_q"], a)
        if kind == "cq_pipe":
            return pipeline_answer(m, s["ctx"].format(a=a), s["constraint_q"], a)
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(run, *t): t for t in tasks}
        for f in as_completed(fut):
            t = fut[f]
            try:
                res[t] = f.result()
            except Exception:
                res[t] = (None, None)
            done += 1
    print(f"Zadań: {len(tasks)}, wykonane: {done}")

    print("\n=== ROZRÓŻNIANIE (ta sama liczba, dwa pytania; klasyfikator bez podpowiedzi) ===")
    print("ANCHOR-Q: A-Index (niżej=lepiej), detection=oznaczył ANCHOR | CONSTRAINT-Q: keep + poprawność liczenia")
    hdr = "model".ljust(38) + "A-Idx base  A-Idx pipe  det(anch)  keep(con)  popr(con)  DYSKRYM."
    print(hdr); print("-" * len(hdr))
    g_disc = []
    for m in MODELS:
        ab, ap_, det, keep, corr, disc = [], [], [], [], [], []
        for s in SCEN:
            d = abs(s["high"] - s["low"])
            blo = res.get(("aq_base", m, s["id"], "low")); bhi = res.get(("aq_base", m, s["id"], "high"))
            plo = res.get(("aq_pipe", m, s["id"], "low")); phi = res.get(("aq_pipe", m, s["id"], "high"))
            if blo and bhi and blo[0] is not None and bhi[0] is not None and d:
                ab.append(abs(bhi[0] - blo[0]) / d)
            anch_ok = None
            if plo and phi and plo[0] is not None and phi[0] is not None and d:
                ap_.append(abs(phi[0] - plo[0]) / d)
            if plo and phi:
                flags = [x for x in (plo[1], phi[1]) if x is not None]
                if flags:
                    rate = mean([1 if x else 0 for x in flags]); det.append(rate); anch_ok = rate >= 0.5
            cq = res.get(("cq_pipe", m, s["id"], "high"))
            keep_ok = corr_ok = None
            if cq:
                kept = (cq[1] is False)  # constraint-Q: dobrze gdy NIE oznaczył ANCHOR (zostawił)
                keep.append(1 if kept else 0); keep_ok = kept
                exp = s["high"] / s["div"]
                if cq[0] is not None and exp:
                    ok = abs(cq[0] - exp) / exp < 0.15
                    corr.append(1 if ok else 0); corr_ok = ok
            if anch_ok is not None and keep_ok is not None and corr_ok is not None:
                disc.append(1 if (anch_ok and keep_ok and corr_ok) else 0)
        g_disc.extend(disc)
        row = m.ljust(38)
        row += f"{mean(ab):.3f}".ljust(12) + f"{mean(ap_):.3f}".ljust(12)
        row += (f"{100*mean(det):.0f}%").ljust(11) + (f"{100*mean(keep):.0f}%").ljust(11) + (f"{100*mean(corr):.0f}%").ljust(11)
        row += f"{100*mean(disc):.0f}%" if disc else "n/a"
        print(row)
    print("-" * len(hdr))
    print(f"DYSKRYMINACJA ŚREDNIA (oba naraz dobrze): {100*mean(g_disc):.0f}%" if g_disc else "n/a")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    dump = {"|".join(str(x) for x in k): v for k, v in res.items()}
    with open(args.out, "w") as fh:
        json.dump({"models": MODELS, "scenarios": SCEN, "discrimination": mean(g_disc) if g_disc else None, "raw": dump}, fh, ensure_ascii=False, indent=2)
    print(f"\nSurowe wyniki: {args.out}")


if __name__ == "__main__":
    main()
