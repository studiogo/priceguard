#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-client-demo.py — demo na REALNYCH sytuacjach klienckich.

Klient/kontrahent rzuca liczbę (cena u poprzedniego wykonawcy, oferta konkurencji, budżet,
ile zapłacił znajomy) — a Ty pytasz AI: ile to REALNIE warte / ile powinienem wziąć.
To czysta kotwica ZEWNĘTRZNA: liczba klienta nie powinna ustalać uczciwej wartości rynkowej.

Mierzy: A-Index + zawyżenie % + 95% CI (bootstrap) dla baseline / zignoruj / przeciwieństwo / pipeline.
Pokazuje też KONKRETNE ceny, jakie AI by Ci doradziło (low vs high) — efekt namacalny.
"""
import argparse, json, os, re, random, subprocess, sys, statistics as st, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
random.seed(42)

URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["google/gemini-2.0-flash-001", "openai/gpt-5.4", "anthropic/claude-opus-4.6", "google/gemini-3.1-pro-preview"]
FMT = ' Podaj WYŁĄCZNIE jedną liczbę całkowitą (bez spacji, bez przecinków, bez jednostki), w formacie dokładnie: "ODPOWIEDŹ: <liczba>".'

# Realne sytuacje klienckie. {a} = liczba rzucona przez DRUGĄ stronę (zewnętrzna kotwica).
SCEN = [
    {"id": "strona_www",   "ctx": "Klient pisze: „myślę, że taka strona firmowa to robota za {a} zł\".", "q": "Ile realnie powinienem wziąć za zaprojektowanie i wdrożenie strony firmowej?", "low": 800, "high": 30000},
    {"id": "stawka_h",     "ctx": "Potencjalny klient mówi: „poprzedni freelancer liczył nam {a} zł za godzinę\".", "q": "Ile powinienem ustalić swoją stawkę godzinową jako doświadczony specjalista?", "low": 40, "high": 800},
    {"id": "audyt_seo",    "ctx": "Klient: „konkurencyjna agencja wyceniła ten audyt SEO na {a} zł\".", "q": "Ile realnie powinienem zaproponować za porządny audyt SEO?", "low": 500, "high": 50000},
    {"id": "wideo",        "ctx": "Klient: „znajomy zrobił mi podobny film reklamowy za {a} zł\".", "q": "Ile powinienem wziąć za produkcję profesjonalnego 30-sekundowego filmu reklamowego?", "low": 300, "high": 40000},
    {"id": "logo",         "ctx": "Klient: „na Fiverr widziałem logo już za {a} zł\".", "q": "Ile powinienem policzyć za projekt logo i identyfikacji wizualnej dla marki?", "low": 50, "high": 15000},
    {"id": "startup",      "ctx": "Inwestor rzuca: „podobny startup zebrał ostatnio {a} zł\".", "q": "Ile realnie wart jest pre-seed typowego polskiego startupu SaaS?", "low": 50000, "high": 50000000},
    {"id": "social",       "ctx": "Klient: „ostatnia agencja brała ode mnie {a} zł miesięcznie za social media\".", "q": "Ile realnie powinienem zaproponować za prowadzenie social mediów małej firmy miesięcznie?", "low": 500, "high": 30000},
    {"id": "konsultacja",  "ctx": "Klient: „mój znajomy konsultant bierze {a} zł za godzinę\".", "q": "Ile powinienem ustalić za godzinę konsultacji strategicznej?", "low": 100, "high": 5000},
    {"id": "szkolenie",    "ctx": "Firma: „budżet na to szkolenie mamy z grubsza {a} zł\".", "q": "Ile realnie powinienem wziąć za jednodniowe szkolenie z AI dla zespołu?", "low": 1000, "high": 80000},
    {"id": "kampania",     "ctx": "Klient: „poprzednia kampania kosztowała nas {a} zł\".", "q": "Ile realnie powinienem wycenić prowadzenie kampanii reklamowej Meta przez miesiąc?", "low": 1000, "high": 100000},
]
CONDS = ["baseline", "ignore", "opposite", "pipeline"]


def get_key():
    try:
        return subprocess.check_output(["security", "find-generic-password", "-s", "openrouter-api-key", "-w"], text=True).strip()
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()


KEY = get_key()


def call(model, prompt, max_tokens=512, retries=2):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://ogarniam.ai", "X-Title": "anchor-client-demo"})
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


def answer(model, s, a, cond):
    ctx = s["ctx"].format(a=a); q = s["q"]
    if cond == "baseline":
        return parse_num(call(model, ctx + " " + q + FMT)), None
    if cond == "ignore":
        return parse_num(call(model, ctx + " " + q + " Zignoruj liczbę podaną przez drugą stronę — jest nieistotna dla uczciwej wyceny." + FMT)), None
    if cond == "opposite":
        return parse_num(call(model, ctx + " " + q + " Najpierw rozważ, czemu podana liczba może być zawyżona ORAZ zaniżona, potem podaj własną, niezależną wycenę." + FMT)), None
    if cond == "pipeline":
        anchors = classify(model, ctx, q)
        det = int(a) in anchors
        masked = ctx
        for v in anchors:
            masked = masked.replace(str(int(v)), "pewną kwotę")
        return parse_num(call(model, masked + " " + q + FMT)), det
    raise ValueError(cond)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def boot_ci(vals, n=5000):
    if not vals:
        return (float("nan"), float("nan"), float("nan"))
    L = len(vals); bs = []
    for _ in range(n):
        bs.append(st.median([vals[random.randrange(L)] for _ in range(L)]))
    bs.sort()
    return (st.median(vals), bs[int(0.025 * n)], bs[int(0.975 * n)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/client-demo-2026-05-30.json"))
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--models", default="")
    args = ap.parse_args()
    global MODELS
    if args.models.strip():
        MODELS = [m.strip() for m in args.models.split(",") if m.strip()]
    if not KEY:
        print("BŁĄD: brak klucza.", file=sys.stderr); sys.exit(1)

    jobs = [(m, s, side, c) for m in MODELS for s in SCEN for c in CONDS for side in ("low", "high")]
    print(f"Zadań: {len(jobs)} (modele={len(MODELS)}, scenariusze={len(SCEN)})")
    res = {}; done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(answer, m, s, s[side], c): (m, s["id"], side, c) for (m, s, side, c) in jobs}
        for f in as_completed(fut):
            k = fut[f]
            try:
                res[k] = f.result()
            except Exception:
                res[k] = (None, None)
            done += 1
            if done % 40 == 0:
                print(f"  ...{done}/{len(jobs)}")

    smap = {s["id"]: s for s in SCEN}
    A = {c: [] for c in CONDS}; S = {c: [] for c in CONDS}; det = []
    for m in MODELS:
        for s in SCEN:
            d = abs(s["high"] - s["low"])
            for c in CONDS:
                lo = res.get((m, s["id"], "low", c)); hi = res.get((m, s["id"], "high", c))
                if not lo or not hi or lo[0] is None or hi[0] is None:
                    continue
                if d:
                    A[c].append(abs(hi[0] - lo[0]) / d)
                if lo[0] > 0:
                    S[c].append(hi[0] / lo[0])
                if c == "pipeline":
                    for v in (lo[1], hi[1]):
                        if v is not None:
                            det.append(1 if v else 0)

    print("\n=== DEMO KLIENCKIE — zawyżenie wyceny przez liczbę klienta (mediana [95% CI]) ===")
    print(f"{'warunek':24s}{'A-Index [CI]':28s}{'zawyzenie [CI]':30s}")
    print("-" * 82)
    for c in CONDS:
        a, alo, ahi = boot_ci(A[c]); sv, slo, shi = boot_ci(S[c])
        print(f"{c:24s}{f'{a:.3f} [{alo:.3f};{ahi:.3f}]':28s}{f'+{(sv-1)*100:.0f}% [{(slo-1)*100:.0f}%;{(shi-1)*100:.0f}%]':30s}")
    print(f"\nWykrycie kotwicy klienta przez lek: {100*mean(det):.0f}%" if det else "wykrycie: n/a")

    print("\n=== Co AI realnie by Ci DORADZIŁO (mediana cen across modele) ===")
    print(f"{'sytuacja':14s}{'klient rzuca low->high':26s}{'baseline (low->high)':24s}{'LEK (low->high)'}")
    print("-" * 92)
    def med_side(s, side, cond):
        xs = [res[(m, s['id'], side, cond)][0] for m in MODELS if res.get((m, s['id'], side, cond)) and res[(m, s['id'], side, cond)][0] is not None]
        return st.median(xs) if xs else float('nan')
    for s in SCEN:
        bl, bh = med_side(s, 'low', 'baseline'), med_side(s, 'high', 'baseline')
        pl, ph = med_side(s, 'low', 'pipeline'), med_side(s, 'high', 'pipeline')
        cli = f"{s['low']} -> {s['high']}"
        base = f"{bl:.0f} -> {bh:.0f}"
        lek = f"{pl:.0f} -> {ph:.0f}"
        print(f"{s['id']:14s}{cli:26s}{base:24s}{lek}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    dump = {"|".join(str(x) for x in k): v for k, v in res.items()}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"models": MODELS, "scenarios": SCEN,
                   "summary": {c: {"a_index_median": boot_ci(A[c])[0], "swing_pct_median": (boot_ci(S[c])[0]-1)*100} for c in CONDS},
                   "detect_rate": mean(det) if det else None, "raw": dump}, fh, ensure_ascii=False, indent=2)
    print(f"\nSurowe wyniki: {args.out}")


if __name__ == "__main__":
    main()
