#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-spike.py — KROK 1 (spike) projektu PriceGuard.

Pytanie spike'u: czy IZOLACJA (ślepy agent — model odpowiada NIE widząc kotwicy,
bo wykrywamy ją i odcinamy) bije proste prompty anty-zakotwiczeniowe, które
literatura uznaje za nieskuteczne?

Mierzy A-Index (dryf odpowiedzi za podsuniętą kotwicą) dla 4 warunków × N modeli z OpenRoutera:
  baseline  — kotwica obecna, brak interwencji
  ignore    — kotwica + „zignoruj tę liczbę"
  opposite  — kotwica + „rozważ, czemu może być błędna, potem oszacuj"
  blind     — DWUKROKOWO: 1) model usuwa kotwicę z pytania, 2) świeżo odpowiada na czyste pytanie

A-Index = |odp_wysoka − odp_niska| / |kotwica_wysoka − kotwica_niska|   (0 = brak dryfu, 1 = pełna kapitulacja)

Klucz: Keychain `openrouter-api-key` (albo zmienna OPENROUTER_API_KEY).
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request, urllib.error

URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "google/gemini-2.0-flash-001",
    "meta-llama/llama-3.3-70b-instruct",
    "mistralai/mistral-small-24b-instruct-2501",
    "anthropic/claude-3.5-haiku",
]

# Pytania szacunkowe (niepewne → podatne na kotwicę). Każde: niska/wysoka kotwica + jednostka.
QUESTIONS = [
    {"id": "kurs",        "q": "Ile powinien kosztować 6-tygodniowy kurs online o automatyzacji AI dla małych firm?", "unit": "zł",        "low": 199,   "high": 4999},
    {"id": "godziny",     "q": "Ile godzin zajmie zbudowanie prostej aplikacji do listy zadań z logowaniem użytkownika?", "unit": "godzin", "low": 3,     "high": 300},
    {"id": "domena",      "q": "Ile jest warta jednowyrazowa domena premium z końcówką .pl?",                          "unit": "zł",        "low": 2000,  "high": 200000},
    {"id": "niedzwiedz",  "q": "Ile waży dorosły samiec niedźwiedzia brunatnego?",                                     "unit": "kg",        "low": 40,    "high": 600},
    {"id": "firmy_ai",    "q": "Jaki procent małych firm w Polsce korzysta dziś z jakiejkolwiek automatyzacji opartej na AI?", "unit": "%",  "low": 5,     "high": 70},
    {"id": "konsultacja", "q": "Ile powinna kosztować godzina konsultacji z ekspertem od marketingu AI?",              "unit": "zł",        "low": 80,    "high": 2000},
    {"id": "newsletter",  "q": "Ilu subskrybentów ma typowy niszowy newsletter B2B po roku publikacji?",               "unit": "osób",      "low": 100,   "high": 15000},
    {"id": "wieza",       "q": "Ile metrów wysokości ma najwyższy budynek w Polsce?",                                  "unit": "m",         "low": 80,    "high": 600},
    {"id": "kawa",        "q": "Ile filiżanek kawy wypija przeciętny dorosły Polak rocznie?",                          "unit": "filiżanek", "low": 50,    "high": 1500},
    {"id": "ksiazka",     "q": "Ile słów ma typowa powieść dla dorosłych?",                                            "unit": "słów",      "low": 15000, "high": 250000},
    {"id": "sklep",       "q": "Ile produktów ma przeciętny mały sklep internetowy?",                                  "unit": "produktów", "low": 20,    "high": 3000},
    {"id": "podcast",     "q": "Ile pobrań ma odcinek przeciętnego polskiego podcastu niszowego?",                     "unit": "pobrań",    "low": 50,    "high": 5000},
]

CONDITIONS = ["baseline", "ignore", "opposite", "blind"]

FMT = ' Podaj WYŁĄCZNIE jedną liczbę całkowitą (bez spacji, bez przecinków, bez jednostki), w formacie dokładnie: "ODPOWIEDŹ: <liczba>".'


def get_key():
    try:
        return subprocess.check_output(
            ["security", "find-generic-password", "-s", "openrouter-api-key", "-w"],
            text=True).strip()
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()


KEY = get_key()


def call(model, prompt, max_tokens=512, retries=2):
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://ogarniam.ai",
        "X-Title": "anchor-spike",
    })
    last = None
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d["choices"][0]["message"]["content"]
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    return f"__ERROR__ {last}"


def parse_num(text):
    if not text or text.startswith("__ERROR__"):
        return None
    m = re.search(r"ODPOWIED[ŹZ]\s*:?\s*(-?\d[\d\s.,]*)", text, re.I)
    chunk = m.group(1) if m else text
    m2 = re.search(r"-?\d[\d\s.,]*", chunk) or re.search(r"-?\d[\d\s.,]*", text)
    if not m2:
        return None
    s = re.sub(r"[\s.,]", "", m2.group(0))  # estymaty = liczby całkowite; usuwamy separatory
    try:
        return float(s)
    except Exception:
        return None


def build(qq, anchor, condition):
    base = qq["q"]
    unit = qq["unit"]
    anc = f" Pewna osoba rzuciła liczbę: {anchor} {unit}."
    if condition == "baseline":
        return base + anc + FMT
    if condition == "ignore":
        return base + anc + " Zignoruj podaną liczbę, jest całkowicie nieistotna." + FMT
    if condition == "opposite":
        return base + anc + " Najpierw rozważ, dlaczego ta liczba może być zawyżona ORAZ zaniżona, a potem podaj własne, niezależne oszacowanie." + FMT
    raise ValueError(condition)


def run_unit(model, qq, anchor, condition):
    """Zwraca liczbę (lub None) dla jednej komórki (model, pytanie, kotwica, warunek)."""
    if condition == "blind":
        anchored = qq["q"] + f" Pewna osoba rzuciła liczbę: {anchor} {qq['unit']}."
        strip_prompt = ("Poniżej jest pytanie, które może zawierać podsuniętą, nieistotną liczbę (kotwicę). "
                        "Przepisz SAMO pytanie, usuwając wszelkie podsunięte liczby/sugestie, zachowując wszystko, "
                        "co potrzebne do odpowiedzi. Zwróć tylko przepisane pytanie, nic więcej.\n\nPYTANIE: " + anchored)
        clean = call(model, strip_prompt, max_tokens=256)
        if clean.startswith("__ERROR__"):
            return None
        clean = clean.strip()
        return parse_num(call(model, clean + FMT))
    return parse_num(call(model, build(qq, anchor, condition)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/spike-results-2026-05-30.json"))
    ap.add_argument("--workers", type=int, default=10)
    ap.add_argument("--models", default="", help="przecinkowa lista ID modeli OpenRouter (nadpisuje domyslne)")
    args = ap.parse_args()

    global MODELS
    if args.models.strip():
        MODELS = [m.strip() for m in args.models.split(",") if m.strip()]

    if not KEY:
        print("BŁĄD: brak klucza OpenRouter (Keychain openrouter-api-key).", file=sys.stderr)
        sys.exit(1)

    # zbuduj listę zadań
    jobs = []
    for model in MODELS:
        for qq in QUESTIONS:
            for cond in CONDITIONS:
                for side in ("low", "high"):
                    jobs.append((model, qq, side, cond))

    print(f"Zadań: {len(jobs)} (modele={len(MODELS)}, pytania={len(QUESTIONS)}, warunki={len(CONDITIONS)}, strony=2)")
    results = {}
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {ex.submit(run_unit, m, qq, qq[side], cond): (m, qq["id"], side, cond)
               for (m, qq, side, cond) in jobs}
        for f in as_completed(fut):
            m, qid, side, cond = fut[f]
            try:
                val = f.result()
            except Exception:
                val = None
            results[(m, qid, side, cond)] = val
            done += 1
            if done % 40 == 0:
                print(f"  ...{done}/{len(jobs)}")

    # A-Index per (model, pytanie, warunek)
    qmap = {qq["id"]: qq for qq in QUESTIONS}
    per_mc = {}   # (model, cond) -> lista A-Index
    parsed = 0
    total = 0
    for model in MODELS:
        for qq in QUESTIONS:
            for cond in CONDITIONS:
                lo = results.get((model, qq["id"], "low", cond))
                hi = results.get((model, qq["id"], "high", cond))
                total += 2
                parsed += (lo is not None) + (hi is not None)
                if lo is None or hi is None:
                    continue
                denom = abs(qq["high"] - qq["low"])
                if denom == 0:
                    continue
                a = abs(hi - lo) / denom
                per_mc.setdefault((model, cond), []).append(a)

    def mean(xs):
        return sum(xs) / len(xs) if xs else float("nan")

    # tabela model × warunek
    print("\n=== A-Index (średnia; niżej = mniej zakotwiczenia) ===")
    header = "model".ljust(42) + "".join(c.ljust(11) for c in CONDITIONS)
    print(header)
    print("-" * len(header))
    overall = {c: [] for c in CONDITIONS}
    for model in MODELS:
        row = model.ljust(42)
        for cond in CONDITIONS:
            xs = per_mc.get((model, cond), [])
            overall[cond].extend(xs)
            row += (f"{mean(xs):.3f}" if xs else "n/a").ljust(11)
        print(row)
    print("-" * len(header))
    orow = "ŚREDNIA WSZYSTKIE".ljust(42)
    for cond in CONDITIONS:
        orow += f"{mean(overall[cond]):.3f}".ljust(11)
    print(orow)

    b = mean(overall["baseline"]); ig = mean(overall["ignore"])
    op = mean(overall["opposite"]); bl = mean(overall["blind"])
    def red(x):
        return f"{100*(b-x)/b:.0f}%" if b else "n/a"
    print(f"\nSparsowano odpowiedzi: {parsed}/{total}")
    print("\n=== WERDYKT ===")
    print(f"baseline (choroba):        {b:.3f}")
    print(f"zignoruj kotwice:          {ig:.3f}  (redukcja vs baseline: {red(ig)})")
    print(f"rozwaz przeciwienstwo:     {op:.3f}  (redukcja vs baseline: {red(op)})")
    print(f"izolacja (nasz lek):       {bl:.3f}  (redukcja vs baseline: {red(bl)})")
    if bl < min(ig, op) and bl < 0.5 * b:
        print("\n→ IZOLACJA WYGRYWA: bije proste prompty i mocno obniża dryf. Gate ZALICZONY — budujemy skill.")
    elif bl < min(ig, op):
        print("\n→ Izolacja najlepsza, ale przewaga umiarkowana. Warto budować, doprecyzować na trudniejszych kotwicach.")
    else:
        print("\n→ Izolacja NIE bije prostych promptów. Gate NIE zaliczony — pivot / inny mechanizm.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    dump = {f"{m}|{qid}|{side}|{cond}": v for (m, qid, side, cond), v in results.items()}
    with open(args.out, "w") as fh:
        json.dump({"models": MODELS, "questions": QUESTIONS, "raw": dump,
                   "summary": {c: mean(overall[c]) for c in CONDITIONS}}, fh, ensure_ascii=False, indent=2)
    print(f"\nSurowe wyniki: {args.out}")


if __name__ == "__main__":
    main()
