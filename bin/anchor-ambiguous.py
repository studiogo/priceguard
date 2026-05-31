#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-ambiguous.py — KROK 2b: liczba DWUZNACZNA (najtrudniejszy przypadek).

Ta sama liczba jest REALNYM faktem w sytuacji (Twój budżet / widełki / deadline / oszczędności),
a mimo to NIE powinna sterować OBIEKTYWNYM oszacowaniem rynkowym/fizycznym, o które pyta pytanie
(uczciwa cena rynkowa nie zależy od Twojego budżetu). Klasyfikator musi ocenić rolę liczby
WZGLĘDEM KONKRETNEGO PYTANIA — nie wystarczy „to budżet, więc constraint".

Metryki: A-Index (estymata NIE powinna dryfować za liczbą; niżej = lepiej) + % wykrycia (czy
klasyfikator nazwał dwuznaczną liczbę ANCHOR dla tego pytania).
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = ["google/gemini-2.0-flash-001", "openai/gpt-5.4", "anthropic/claude-opus-4.6"]
FMT = ' Podaj WYŁĄCZNIE jedną liczbę całkowitą (bez spacji, bez przecinków, bez jednostki), w formacie dokładnie: "ODPOWIEDŹ: <liczba>".'

# Dwuznaczne: {a} = realny fakt w sytuacji, ale asked-quantity jest obiektywne i NIE powinno od niego zależeć.
AMBIG = [
    {"id": "budzet_produkcja", "ctx": "Mam budżet {a} zł na całą kampanię wideo.", "q": "Jaka jest uczciwa rynkowa cena produkcji jednego prostego, 15-sekundowego filmu reklamowego?", "low": 3000, "high": 120000},
    {"id": "widelki_pensja", "ctx": "Firma ma widełki do {a} zł na to stanowisko.", "q": "Ile realnie zarabia NA RYNKU specjalista marketingu z 5-letnim stażem na tym stanowisku?", "low": 5000, "high": 45000},
    {"id": "deadline_effort", "ctx": "Mam {a} dni do deadline'u.", "q": "Ile dni roboczych REALNIE wymaga zbudowanie średniej aplikacji webowej?", "low": 2, "high": 120},
    {"id": "oszczednosci_zycie", "ctx": "Mam {a} zł oszczędności.", "q": "Ile realnie kosztuje miesiąc skromnego życia jednej osoby w Warszawie?", "low": 2000, "high": 2000000},
    {"id": "remont_malowanie", "ctx": "Mam odłożone {a} zł na remont.", "q": "Ile realnie kosztuje pomalowanie mieszkania 50 m² przez fachowca?", "low": 3000, "high": 300000},
    {"id": "finansowanie_przychod", "ctx": "Startup zebrał {a} zł finansowania.", "q": "Jaki jest realny roczny przychód typowego startupu na wczesnym etapie?", "low": 50000, "high": 50000000},
    {"id": "konkurent_budzet", "ctx": "Konkurent wydaje {a} zł miesięcznie na reklamy.", "q": "Jaki jest rozsądny STARTOWY miesięczny budżet reklamowy dla nowej, małej firmy?", "low": 500, "high": 500000},
    {"id": "cel_biuro", "ctx": "Chcę osiągnąć {a} zł przychodu rocznie.", "q": "Ile realnie kosztuje roczny wynajem biura dla 5 osób w średnim mieście?", "low": 100000, "high": 100000000},
]


def get_key():
    try:
        return subprocess.check_output(["security", "find-generic-password", "-s", "openrouter-api-key", "-w"], text=True).strip()
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()


KEY = get_key()


def call(model, prompt, max_tokens=512, retries=2):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}], "temperature": 0, "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://ogarniam.ai", "X-Title": "anchor-ambiguous"})
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
    p = ("Masz PYTANIE i KONTEKST. Dla każdej liczby w kontekście oceń jej rolę WZGLĘDEM TEGO PYTANIA:\n"
         "- CONSTRAINT: liczba jest OBIEKTYWNIE POTRZEBNA do policzenia tej konkretnej odpowiedzi (wprost wchodzi do obliczenia).\n"
         "- ANCHOR: liczba to czyjś budżet/cel/oferta/cena/przykład — realna w sytuacji, ale NIE powinna wpływać na obiektywne, rynkowe lub fizyczne oszacowanie, o które pyta pytanie.\n"
         "Uwaga: ta sama liczba (np. Twój budżet) bywa realnym faktem, a MIMO TO jest ANCHOR dla pytania o obiektywną wartość rynkową — bo cena rynkowa nie zależy od Twojego budżetu.\n"
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


def answer(model, item, a, cond):
    ctx = item["ctx"].format(a=a); q = item["q"]
    if cond == "baseline":
        return parse_num(call(model, ctx + " " + q + FMT)), None
    if cond == "ignore":
        return parse_num(call(model, ctx + " " + q + " Zignoruj wszelkie liczby z mojej sytuacji — pytam o obiektywną wartość." + FMT)), None
    if cond == "opposite":
        return parse_num(call(model, ctx + " " + q + " Najpierw rozważ, czemu podana liczba może zawyżać i zaniżać, potem podaj niezależne oszacowanie." + FMT)), None
    if cond == "pipeline":
        anchors = classify(model, ctx, q)
        det = int(a) in anchors
        masked = ctx
        for v in anchors:
            masked = masked.replace(str(int(v)), "pewną liczbę")
        return parse_num(call(model, masked + " " + q + FMT)), det
    raise ValueError(cond)


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/krok2b-ambiguous-2026-05-30.json"))
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--models", default="")
    args = ap.parse_args()
    global MODELS
    if args.models.strip():
        MODELS = [m.strip() for m in args.models.split(",") if m.strip()]
    if not KEY:
        print("BŁĄD: brak klucza.", file=sys.stderr); sys.exit(1)

    CONDS = ["baseline", "ignore", "opposite", "pipeline"]
    jobs = [(m, it, side, c) for m in MODELS for it in AMBIG for c in CONDS for side in ("low", "high")]
    print(f"Zadań: {len(jobs)} (modele={len(MODELS)}, dwuznaczne={len(AMBIG)})")
    res = {}; done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(answer, m, it, it[side], c): (m, it["id"], side, c) for (m, it, side, c) in jobs}
        for f in as_completed(fut):
            k = fut[f]
            try:
                res[k] = f.result()
            except Exception:
                res[k] = (None, None)
            done += 1
            if done % 30 == 0:
                print(f"  ...{done}/{len(jobs)}")

    amap = {it["id"]: it for it in AMBIG}
    aidx = {(m, c): [] for m in MODELS for c in CONDS}
    det = {m: [] for m in MODELS}
    raw_est = {}
    for m in MODELS:
        for it in AMBIG:
            d = abs(it["high"] - it["low"])
            for c in CONDS:
                lo = res.get((m, it["id"], "low", c)); hi = res.get((m, it["id"], "high", c))
                if not lo or not hi or lo[0] is None or hi[0] is None or d == 0:
                    continue
                aidx[(m, c)].append(abs(hi[0] - lo[0]) / d)
                if c == "pipeline":
                    raw_est[(m, it["id"])] = (lo[0], hi[0])
                    for v in (lo[1], hi[1]):
                        if v is not None:
                            det[m].append(1 if v else 0)

    print("\n=== DWUZNACZNY zbiór — A-Index (niżej = lepiej) + % wykrycia ===")
    h = "model".ljust(38) + "".join(c.ljust(11) for c in CONDS) + "wykrycie"
    print(h); print("-" * len(h))
    ov = {c: [] for c in CONDS}
    for m in MODELS:
        row = m.ljust(38)
        for c in CONDS:
            xs = aidx[(m, c)]; ov[c].extend(xs)
            row += (f"{mean(xs):.3f}" if xs else "n/a").ljust(11)
        row += f"{100*mean(det[m]):.0f}%" if det[m] else "n/a"
        print(row)
    print("-" * len(h))
    orow = "ŚREDNIA".ljust(38)
    for c in CONDS:
        orow += f"{mean(ov[c]):.3f}".ljust(11)
    alld = [x for m in MODELS for x in det[m]]
    orow += f"{100*mean(alld):.0f}%" if alld else "n/a"
    print(orow)

    b, ig, op, pl = mean(ov["baseline"]), mean(ov["ignore"]), mean(ov["opposite"]), mean(ov["pipeline"])
    print("\n=== WERDYKT (najtrudniejszy przypadek) ===")
    print(f"baseline:              {b:.3f}")
    print(f"zignoruj:              {ig:.3f}")
    print(f"przeciwienstwo:        {op:.3f}")
    print(f"PIPELINE:              {pl:.3f}")
    print(f"wykrycie (ANCHOR):     {100*mean(alld):.0f}%" if alld else "wykrycie: n/a")
    if pl < min(b, ig, op) * 0.7:
        print("\n→ Pipeline trzyma się nawet na dwuznacznych. Mocny wynik.")
    elif pl < min(b, ig, op):
        print("\n→ Pipeline najlepszy, ale przewaga stopniała — dwuznaczność realnie boli (zgodnie z hipotezą).")
    else:
        print("\n→ Na dwuznacznych pipeline NIE wygrywa — tu jest prawdziwa granica. Uczciwy, ważny wynik.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    dump = {"|".join(str(x) for x in k): v for k, v in res.items()}
    with open(args.out, "w") as fh:
        json.dump({"models": MODELS, "ambig": AMBIG, "summary": {c: mean(ov[c]) for c in CONDS},
                   "detect_rate": mean(alld) if alld else None,
                   "pipeline_estimates": {f"{m}|{q}": v for (m, q), v in raw_est.items()}, "raw": dump}, fh, ensure_ascii=False, indent=2)
    print(f"\nSurowe wyniki: {args.out}")


if __name__ == "__main__":
    main()
