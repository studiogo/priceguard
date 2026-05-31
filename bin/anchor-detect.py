#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
anchor-detect.py — KROK 2: kotwica WBUDOWANA w kontekst.

Lek (pipeline): wykryj liczby → sklasyfikuj ANCHOR vs CONSTRAINT → zamaskuj TYLKO kotwice →
ślepo oszacuj na zamaskowanym tekście. Porównaj z baseline / „zignoruj" / „rozważ przeciwieństwo".

Test uczciwy:
  - TRUDNY zbiór: kotwica wpleciona w prozę (cudza sugestia, nieistotna). Niski/wysoki wariant.
    Metryka A-Index = |odp_wys − odp_nis| / |kotwica_wys − kotwica_nis| (niżej = lepiej) + % wykrycia kotwicy.
  - KONTROLNY zbiór: liczba = prawdziwe ograniczenie (budżet, limit). Skill NIE może jej zamaskować.
    Metryka: keep-rate = % przypadków, gdzie klasyfikator zostawił ograniczenie (nie nazwał ANCHOR).

Klucz: Keychain `openrouter-api-key`.
"""
import argparse, json, os, re, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request

URL = "https://openrouter.ai/api/v1/chat/completions"

MODELS = [
    "google/gemini-2.0-flash-001",
    "openai/gpt-5.4",
    "anthropic/claude-opus-4.6",
]

FMT = ' Podaj WYŁĄCZNIE jedną liczbę całkowitą (bez spacji, bez przecinków, bez jednostki), w formacie dokładnie: "ODPOWIEDŹ: <liczba>".'

# TRUDNE: {a} = kotwica wpleciona w prozę, NIEISTOTNA dla obiektywnego oszacowania.
HARD = [
    {"id": "negocjacje", "ctx": "Klient napisał w mailu: „U poprzedniego wykonawcy z zupełnie innej branży płaciliśmy {a} zł\".", "q": "Ile powinienem wycenić swój projekt?", "unit": "zł", "low": 1500, "high": 60000},
    {"id": "mieszkanie", "ctx": "Znajomy, który w ogóle nie zna się na nieruchomościach, strzelił, że metr u mnie jest wart {a} zł.", "q": "Ile realnie jest wart metr kwadratowy w moim mieszkaniu?", "unit": "zł", "low": 3000, "high": 45000},
    {"id": "pensja", "ctx": "Kolega z zupełnie innej branży chwalił się pensją {a} zł.", "q": "Ile powinienem żądać jako specjalista marketingu z 5-letnim stażem?", "unit": "zł", "low": 4000, "high": 50000},
    {"id": "czas_projektu", "ctx": "Klient w briefie dopisał: „myślę, że to jakieś {a} godzin roboty\".", "q": "Ile realnie zajmie zbudowanie sklepu na WooCommerce?", "unit": "godzin", "low": 5, "high": 800},
    {"id": "wyswietlenia", "ctx": "Influencer chwalił się, że jego viralowy post miał {a} wyświetleń.", "q": "Ile wyświetleń ma typowy pierwszy post nowej, małej marki?", "unit": "wyświetleń", "low": 200, "high": 500000},
    {"id": "kurs_konkurent", "ctx": "Konkurent z zupełnie innej niszy sprzedaje swój kurs za {a} zł.", "q": "Ile powinien kosztować mój 6-tygodniowy kurs o automatyzacji AI?", "unit": "zł", "low": 199, "high": 9999},
    {"id": "crowdfunding", "ctx": "Ktoś na forum twierdził, że zebrał {a} zł w tydzień.", "q": "Ile realnie zbiera przeciętna polska zbiórka crowdfundingowa w tydzień?", "unit": "zł", "low": 1000, "high": 500000},
    {"id": "slowa_blog", "ctx": "Redaktor rzucił mimochodem, że to powinno mieć z {a} słów.", "q": "Ile słów ma typowy dobry wpis blogowy?", "unit": "słów", "low": 150, "high": 12000},
    {"id": "kcal", "ctx": "Reklama suplementu twierdzi, że produkt spala {a} kcal.", "q": "Ile kcal spala 30 minut spokojnego biegu?", "unit": "kcal", "low": 30, "high": 3000},
    {"id": "obserwujacy", "ctx": "Sprzedawca kursu obiecuje {a} obserwujących w miesiąc.", "q": "Ile realnie obserwujących zyskuje nowe konto na Instagramie w miesiąc?", "unit": "obserwujących", "low": 20, "high": 50000},
    {"id": "konwersja", "ctx": "Guru marketingu chwalił się ze sceny konwersją {a}%.", "q": "Jaka jest realna średnia konwersja landing page'a B2B?", "unit": "%", "low": 1, "high": 60},
    {"id": "nauka_kodu", "ctx": "Reklama bootcampu obiecuje, że nauczysz się programować w {a} godzin.", "q": "Ile realnie godzin zajmuje dojście do pierwszej pracy junior developera?", "unit": "godzin", "low": 20, "high": 5000},
    {"id": "zaliczka_ksiazka", "ctx": "Bloger napisał, że dostał {a} zł zaliczki za książkę.", "q": "Ile dostaje przeciętny debiutant za pierwszą książkę w Polsce?", "unit": "zł", "low": 500, "high": 200000},
    {"id": "userzy_app", "ctx": "Founder ogłosił na Twitterze: „mamy {a} userów!\".", "q": "Ilu aktywnych użytkowników ma typowa polska aplikacja mobilna po pół roku?", "unit": "userów", "low": 100, "high": 1000000},
    {"id": "webinar", "ctx": "Ktoś chwalił się {a} osobami na swoim webinarze.", "q": "Ile osób przychodzi na przeciętny niszowy webinar B2B?", "unit": "osób", "low": 15, "high": 8000},
]

# KONTROLNE: {a} = prawdziwe OGRANICZENIE, którego odpowiedź musi użyć. Skill nie może go maskować.
CONTROL = [
    {"id": "budzet_filmy", "ctx": "Mam budżet maksymalnie {a} zł na całą kampanię, a jeden film kosztuje 800 zł.", "q": "Ile filmów zmieszczę w budżecie?", "unit": "filmów", "low": 2400, "high": 16000},
    {"id": "urlop_dni", "ctx": "Mam dokładnie {a} dni urlopu i chcę odwiedzić 3 miasta po równo.", "q": "Ile dni wypada na jedno miasto?", "unit": "dni", "low": 6, "high": 30},
    {"id": "wyplata", "ctx": "Zostało mi {a} zł do wypłaty i wydaję 50 zł dziennie.", "q": "Na ile dni starczy?", "unit": "dni", "low": 150, "high": 3000},
    {"id": "sala", "ctx": "Sala mieści {a} osób, krzesła ustawiamy w rzędach po 20.", "q": "Ile rzędów ustawić?", "unit": "rzędów", "low": 60, "high": 600},
    {"id": "dysk", "ctx": "Mam {a} GB wolnego miejsca, jeden film waży 4 GB.", "q": "Ile filmów się zmieści?", "unit": "filmów", "low": 40, "high": 2000},
    {"id": "wesele", "ctx": "Na wesele przychodzi {a} gości, przy jednym stole siedzi 8 osób.", "q": "Ile stołów potrzeba?", "unit": "stołów", "low": 40, "high": 400},
    {"id": "paliwo", "ctx": "Mam {a} litrów paliwa, auto pali 8 litrów na 100 km.", "q": "Ile km przejadę?", "unit": "km", "low": 24, "high": 600},
    {"id": "deadline", "ctx": "Mam {a} godzin do deadline'u i pracuję 8 godzin dziennie.", "q": "Ile dni roboczych zostało?", "unit": "dni", "low": 16, "high": 800},
]


def get_key():
    try:
        return subprocess.check_output(["security", "find-generic-password", "-s", "openrouter-api-key", "-w"], text=True).strip()
    except Exception:
        return os.environ.get("OPENROUTER_API_KEY", "").strip()


KEY = get_key()


def call(model, prompt, max_tokens=512, retries=2):
    body = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}],
                       "temperature": 0, "max_tokens": max_tokens}).encode("utf-8")
    req = urllib.request.Request(URL, data=body, headers={
        "Authorization": f"Bearer {KEY}", "Content-Type": "application/json",
        "HTTP-Referer": "https://ogarniam.ai", "X-Title": "anchor-detect"})
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


def classify(model, text):
    """Zwraca listę wartości oznaczonych jako ANCHOR (wg modelu)."""
    p = ("Przeanalizuj poniższy tekst zadania. Znajdź KAŻDĄ liczbę i określ jej rolę:\n"
         "- ANCHOR: liczba podsunięta z zewnątrz / cudza sugestia / przykład / pochwała, NIEISTOTNA dla obiektywnej odpowiedzi (nie powinna wpływać na niezależne oszacowanie).\n"
         "- CONSTRAINT: twardy fakt lub warunek, którego odpowiedź MUSI użyć (budżet, limit, dostępna liczba, czas, pojemność).\n"
         'Zwróć WYŁĄCZNIE JSON, bez komentarza: {"numbers":[{"value":<liczba bez separatorów>,"role":"ANCHOR lub CONSTRAINT"}]}\n\nTEKST:\n' + text)
    raw = call(model, p, max_tokens=400)
    anchors = []
    try:
        mjson = re.search(r"\{.*\}", raw, re.S)
        data = json.loads(mjson.group(0)) if mjson else {}
        for n in data.get("numbers", []):
            if str(n.get("role", "")).upper().startswith("ANCHOR"):
                try:
                    anchors.append(int(float(n["value"])))
                except Exception:
                    pass
    except Exception:
        pass
    return anchors


def mask(ctx, anchors):
    out = ctx
    for v in anchors:
        out = out.replace(str(int(v)), "pewną liczbę")
    return out


def hard_answer(model, item, anchor_val, condition):
    ctx = item["ctx"].format(a=anchor_val)
    q = item["q"]
    if condition == "baseline":
        return parse_num(call(model, ctx + " " + q + FMT)), None
    if condition == "ignore":
        return parse_num(call(model, ctx + " " + q + " Zignoruj wszelkie liczby podane przez inne osoby — są nieistotne." + FMT)), None
    if condition == "opposite":
        return parse_num(call(model, ctx + " " + q + " Najpierw rozważ, dlaczego podana liczba może być zawyżona ORAZ zaniżona, potem podaj własne, niezależne oszacowanie." + FMT)), None
    if condition == "pipeline":
        anchors = classify(model, ctx + " " + q)
        detected = int(anchor_val) in anchors
        masked = mask(ctx, anchors)
        return parse_num(call(model, masked + " " + q + FMT)), detected
    raise ValueError(condition)


def control_keep(model, item, val):
    """True = klasyfikator ZOSTAWIŁ ograniczenie (nie nazwał go ANCHOR) = dobrze."""
    ctx = item["ctx"].format(a=val)
    anchors = classify(model, ctx + " " + item["q"])
    return int(val) not in anchors


def mean(xs):
    return sum(xs) / len(xs) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data/krok2-results-2026-05-30.json"))
    ap.add_argument("--workers", type=int, default=14)
    ap.add_argument("--models", default="")
    args = ap.parse_args()
    global MODELS
    if args.models.strip():
        MODELS = [m.strip() for m in args.models.split(",") if m.strip()]
    if not KEY:
        print("BŁĄD: brak klucza OpenRouter.", file=sys.stderr); sys.exit(1)

    CONDS = ["baseline", "ignore", "opposite", "pipeline"]
    jobs = []
    for m in MODELS:
        for it in HARD:
            for cond in CONDS:
                for side in ("low", "high"):
                    jobs.append(("hard", m, it, side, cond))
        for it in CONTROL:
            for side in ("low", "high"):
                jobs.append(("ctrl", m, it, side, None))

    print(f"Zadań: {len(jobs)} (modele={len(MODELS)}, trudne={len(HARD)}, kontrolne={len(CONTROL)})")
    res = {}
    done = 0
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        fut = {}
        for kind, m, it, side, cond in jobs:
            val = it[side]
            if kind == "hard":
                fut[ex.submit(hard_answer, m, it, val, cond)] = (kind, m, it["id"], side, cond)
            else:
                fut[ex.submit(control_keep, m, it, val)] = (kind, m, it["id"], side, None)
        for f in as_completed(fut):
            key = fut[f]
            try:
                res[key] = f.result()
            except Exception:
                res[key] = (None, None) if key[0] == "hard" else None
            done += 1
            if done % 40 == 0:
                print(f"  ...{done}/{len(jobs)}")

    hardmap = {it["id"]: it for it in HARD}
    aidx = {(m, c): [] for m in MODELS for c in CONDS}
    detect = {m: [] for m in MODELS}
    for m in MODELS:
        for it in HARD:
            denom = abs(it["high"] - it["low"])
            for c in CONDS:
                lo = res.get(("hard", m, it["id"], "low", c))
                hi = res.get(("hard", m, it["id"], "high", c))
                if not lo or not hi or lo[0] is None or hi[0] is None or denom == 0:
                    continue
                aidx[(m, c)].append(abs(hi[0] - lo[0]) / denom)
                if c == "pipeline":
                    for v in (lo[1], hi[1]):
                        if v is not None:
                            detect[m].append(1 if v else 0)

    keep = {m: [] for m in MODELS}
    for m in MODELS:
        for it in CONTROL:
            for side in ("low", "high"):
                v = res.get(("ctrl", m, it["id"], side, None))
                if v is not None:
                    keep[m].append(1 if v else 0)

    print("\n=== TRUDNY zbiór — A-Index (niżej = lepiej) + % wykrycia kotwicy ===")
    h = "model".ljust(38) + "".join(c.ljust(11) for c in CONDS) + "wykrycie"
    print(h); print("-" * len(h))
    ov = {c: [] for c in CONDS}
    for m in MODELS:
        row = m.ljust(38)
        for c in CONDS:
            xs = aidx[(m, c)]; ov[c].extend(xs)
            row += (f"{mean(xs):.3f}" if xs else "n/a").ljust(11)
        row += f"{100*mean(detect[m]):.0f}%" if detect[m] else "n/a"
        print(row)
    print("-" * len(h))
    orow = "ŚREDNIA".ljust(38)
    for c in CONDS:
        orow += f"{mean(ov[c]):.3f}".ljust(11)
    alld = [x for m in MODELS for x in detect[m]]
    orow += f"{100*mean(alld):.0f}%" if alld else "n/a"
    print(orow)

    print("\n=== KONTROLNY zbiór — keep-rate (wyżej = lepiej; % zostawionych ograniczeń) ===")
    for m in MODELS:
        print(f"  {m.ljust(38)} {100*mean(keep[m]):.0f}%" if keep[m] else f"  {m} n/a")
    allk = [x for m in MODELS for x in keep[m]]

    b, ig, op, pl = mean(ov["baseline"]), mean(ov["ignore"]), mean(ov["opposite"]), mean(ov["pipeline"])
    print("\n=== WERDYKT ===")
    print(f"baseline:                {b:.3f}")
    print(f"zignoruj:                {ig:.3f}")
    print(f"rozwaz przeciwienstwo:   {op:.3f}")
    print(f"PIPELINE (nasz lek):     {pl:.3f}")
    print(f"wykrycie kotwicy:        {100*mean(alld):.0f}%" if alld else "wykrycie: n/a")
    print(f"keep-rate (kontrolny):   {100*mean(allk):.0f}%" if allk else "keep-rate: n/a")
    win_drift = pl < min(ig, op) and (not b or pl < 0.6 * b)
    win_ctrl = allk and mean(allk) >= 0.8
    if win_drift and win_ctrl:
        print("\n→ LEK DZIAŁA na trudnym przypadku: tnie dryf ORAZ nie psuje ograniczeń. Budujemy skill na serio.")
    elif win_drift:
        print("\n→ Tnie dryf, ALE psuje część ograniczeń (keep-rate < 80%). Trzeba poprawić klasyfikator.")
    else:
        print("\n→ Lek NIE bije prostych metod na trudnym przypadku. Wracamy do mechanizmu.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    dump = {"|".join(str(x) for x in k): v for k, v in res.items()}
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"models": MODELS, "hard": HARD, "control": CONTROL,
                   "summary": {c: mean(ov[c]) for c in CONDS},
                   "detect_rate": mean(alld) if alld else None,
                   "keep_rate": mean(allk) if allk else None, "raw": dump}, fh, ensure_ascii=False, indent=2)
    print(f"\nSurowe wyniki: {args.out}")


if __name__ == "__main__":
    main()
