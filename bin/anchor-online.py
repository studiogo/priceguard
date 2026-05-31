#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-online.py — czy DOSTĘP DO INTERNETU leczy model z kotwicy?

Pytanie badawcze: realny user wrzuca pytanie z kotwicą do ChatGPT/Gemini,
które MAJĄ wyszukiwarkę. Czy internet neutralizuje zakotwiczenie, czy kotwica trzyma mimo sieci?

Metoda: ten sam framework co anchor-client-demo.py (te same modele, scenariusze, mechanika
dwóch kotwic low/high), ale dokładam zmienną INTERNET. Trzy warunki:
  offline        — surowy strzał bez sieci (baseline papugowania)
  online_passive — :online (web search), ale prompt nie zmusza do użycia wyników (przeciętny user)
  online_active  — :online + instrukcja "sprawdź realne stawki, rozważ je, potem wyceń" (research)

Metryki per warunek: A-Index (rozjazd low<->high znormalizowany) + swing% (high/low) + 95% CI (bootstrap).
swing wysoki = papuguje kotwicę. swing ~0% = odporny. Dodatkowo: średnia liczba cytatów web (dowód, że search się odpalił).
"""
import argparse, json, os, re, random, subprocess, sys, statistics as st, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
random.seed(42)

URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["google/gemini-2.0-flash-001", "openai/gpt-5.4", "anthropic/claude-opus-4.6", "google/gemini-3.1-pro-preview"]
FMT = ' Podaj WYŁĄCZNIE jedną liczbę całkowitą (bez spacji, bez przecinków, bez jednostki), w formacie dokładnie: "ODPOWIEDŹ: <liczba>".'
ACTIVE = (" Zanim odpowiesz, sprawdź w internecie realne rynkowe stawki za taką usługę w Polsce i weź je pod uwagę."
          " Na końcu podaj WYŁĄCZNIE jedną liczbę całkowitą w formacie dokładnie: \"ODPOWIEDŹ: <liczba>\".")

# Identyczne scenariusze jak anchor-client-demo.py. {a} = liczba rzucona przez drugą stronę (kotwica).
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
CONDS = ["offline", "online_passive", "online_active"]


def get_key():
    try:
        return subprocess.check_output(["security", "find-generic-password", "-s", "openrouter-api-key", "-w"], text=True).strip()
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()


KEY = get_key()


def call(model, prompt, online=False, max_tokens=512, retries=2):
    mname = model + ":online" if online else model
    body = json.dumps({"model": mname, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://ogarniam.ai", "X-Title": "anchor-online"})
    last = None
    for a in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                msg = json.loads(r.read().decode("utf-8"))["choices"][0]["message"]
                cites = len(msg.get("annotations") or [])
                return msg.get("content") or "", cites
        except Exception as e:
            last = e; time.sleep(2.0 * (a + 1))
    return f"__ERROR__ {last}", 0


def parse_num(text):
    if not text or text.startswith("__ERROR__"):
        return None
    m = re.search(r"ODPOWIED[ŹZ]\s*:?\s*(-?\d[\d\s.,]*)", text, re.I)
    if not m:
        # fallback: ostatnia liczba w tekście (online_active może rozpisać uzasadnienie)
        alln = re.findall(r"-?\d[\d\s.,]*", text)
        if not alln:
            return None
        s = re.sub(r"[\s.,]", "", alln[-1])
    else:
        s = re.sub(r"[\s.,]", "", m.group(1))
    try:
        return float(s)
    except Exception:
        return None


def answer(model, s, a, cond):
    ctx = s["ctx"].format(a=a); q = s["q"]
    if cond == "offline":
        txt, c = call(model, ctx + " " + q + FMT, online=False, max_tokens=512)
    elif cond == "online_passive":
        txt, c = call(model, ctx + " " + q + FMT, online=True, max_tokens=900)
    elif cond == "online_active":
        txt, c = call(model, ctx + " " + q + ACTIVE, online=True, max_tokens=2000)
    else:
        raise ValueError(cond)
    return parse_num(txt), c


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
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/online-vs-offline-2026-05-31.json"))
    ap.add_argument("--workers", type=int, default=18)
    ap.add_argument("--models", default="")
    ap.add_argument("--scen", default="", help="ogranicz do id scenariuszy po przecinku")
    args = ap.parse_args()
    global MODELS, SCEN
    if args.models.strip():
        MODELS = [m.strip() for m in args.models.split(",") if m.strip()]
    if args.scen.strip():
        keep = {x.strip() for x in args.scen.split(",")}
        SCEN = [s for s in SCEN if s["id"] in keep]
    if not KEY:
        print("BŁĄD: brak klucza OpenRouter.", file=sys.stderr); sys.exit(1)

    jobs = [(m, s, side, c) for m in MODELS for s in SCEN for c in CONDS for side in ("low", "high")]
    print(f"Zadań: {len(jobs)} (modele={len(MODELS)}, scenariusze={len(SCEN)}, warunki={len(CONDS)})", flush=True)
    res = {}; done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(answer, m, s, s[side], c): (m, s["id"], side, c) for (m, s, side, c) in jobs}
        for f in as_completed(fut):
            k = fut[f]
            try:
                res[k] = f.result()
            except Exception:
                res[k] = (None, 0)
            done += 1
            if done % 24 == 0:
                print(f"  ...{done}/{len(jobs)}", flush=True)

    # agregacja per warunek
    A = {c: [] for c in CONDS}; S = {c: [] for c in CONDS}; CITES = {c: [] for c in CONDS}
    for m in MODELS:
        for s in SCEN:
            d = abs(s["high"] - s["low"])
            for c in CONDS:
                lo = res.get((m, s["id"], "low", c)); hi = res.get((m, s["id"], "high", c))
                if lo and lo[1] is not None:
                    CITES[c].append(lo[1])
                if hi and hi[1] is not None:
                    CITES[c].append(hi[1])
                if not lo or not hi or lo[0] is None or hi[0] is None:
                    continue
                if d:
                    A[c].append(abs(hi[0] - lo[0]) / d)
                if lo[0] > 0:
                    S[c].append(hi[0] / lo[0])

    print("\n=== INTERNET vs KOTWICA — zawyżenie wyceny przez liczbę klienta (mediana [95% CI]) ===")
    print(f"{'warunek':18s}{'A-Index [CI]':28s}{'swing high/low [CI]':30s}{'śr. cytatów web':16s}")
    print("-" * 92)
    for c in CONDS:
        a, alo, ahi = boot_ci(A[c]); sv, slo, shi = boot_ci(S[c])
        avgc = (sum(CITES[c]) / len(CITES[c])) if CITES[c] else 0.0
        print(f"{c:18s}{f'{a:.3f} [{alo:.3f};{ahi:.3f}]':28s}{f'+{(sv-1)*100:.0f}% [{(slo-1)*100:.0f}%;{(shi-1)*100:.0f}%]':30s}{avgc:>10.1f}")

    print("\n=== Co AI realnie by Ci DORADZIŁO (mediana cen across modele, low->high kotwica) ===")
    print(f"{'sytuacja':14s}{'klient rzuca':22s}" + "".join(f"{c:>22s}" for c in CONDS))
    print("-" * 100)
    def med_side(sid, side, cond):
        xs = [res[(m, sid, side, cond)][0] for m in MODELS if res.get((m, sid, side, cond)) and res[(m, sid, side, cond)][0] is not None]
        return st.median(xs) if xs else float('nan')
    for s in SCEN:
        cli = f"{s['low']}->{s['high']}"
        cells = ""
        for c in CONDS:
            lo = med_side(s["id"], "low", c); hi = med_side(s["id"], "high", c)
            cells += f"{f'{lo:.0f}->{hi:.0f}':>22s}"
        print(f"{s['id']:14s}{cli:22s}{cells}")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    dump = {"|".join(str(x) for x in k): v for k, v in res.items()}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"models": MODELS, "scenarios": SCEN, "conds": CONDS,
                   "summary": {c: {"a_index_median": boot_ci(A[c])[0], "swing_pct_median": (boot_ci(S[c])[0]-1)*100,
                                   "avg_web_cites": (sum(CITES[c])/len(CITES[c])) if CITES[c] else 0} for c in CONDS},
                   "raw": dump}, fh, ensure_ascii=False, indent=2)
    print(f"\nSurowe wyniki: {args.out}")


if __name__ == "__main__":
    main()
