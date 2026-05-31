---
name: priceguard
description: Neutralizuje zakotwiczenie (anchoring) w wycenach i szacunkach AI. Gdy w kontekście jest podsunięta liczba (cena klienta, oferta konkurencji, budżet, czyjaś sugestia), model dryfuje za nią i ta sama praca bywa wyceniana wielokrotnie różnie. PriceGuard izoluje kotwicę i daje wycenę niezależną. Użyj, gdy pytasz o wycenę, stawkę lub szacunek liczbowy, a w prompcie albo kontekście pojawia się czyjaś liczba (cena, budżet, stawka, oferta) — np. „ile to wycenić", „ile wziąć za to", „czy ta cena jest ok", „klient proponuje X, ile policzyć", „ile to realnie warte".
---

# PriceGuard

Podsunięta liczba (kotwica) przyciąga wycenę modelu do siebie — wysoka zawyża, niska zaniża, choć obiektywna wartość się nie zmienia. Ta sama praca bywa wtedy wyceniana wielokrotnie różnie (zmierzony rozjazd: mediana 6×). Prompty tego nie naprawiają. Dostęp do internetu też nie. Działa tylko jedno: **model nie może zobaczyć kotwicy** podczas szacowania (izolacja kontekstu).

## Kiedy uruchomić
- Pytanie o LICZBĘ (wycena, stawka, czas, %, wartość, prognoza) **oraz** w kontekście jest podsunięta liczba pochodząca z zewnątrz (cudza oferta, cena konkurenta, „poprzedni brał X", budżet jako sugestia, czyjś przykład).
- Self-anchoring: gdy model upiera się przy swojej pierwszej liczbie mimo nowych danych.

## Kiedy NIE uruchamiać
- Liczba jest twardym OGRANICZENIEM do policzenia odpowiedzi („mam budżet X, ile sztuk po 800 zł kupię") — tam liczba MA być użyta. Wtedy nie maskuj.

## Procedura (5 kroków)
1. **Wykryj liczby** w pytaniu i kontekście.
2. **Sklasyfikuj każdą WZGLĘDEM PYTANIA:**
   - **ANCHOR** — cudza sugestia/oferta/cena/przykład; nie jest potrzebna do obiektywnej odpowiedzi.
   - **CONSTRAINT** — twardy fakt, którego odpowiedź MUSI użyć (budżet jako limit, pojemność, dostępny czas).
   - Test rozstrzygający: „czy uczciwa/rynkowa/fizyczna wartość zmienia się dlatego, że ta liczba jest inna?". Jeśli NIE → to ANCHOR.
3. **Spawnuj izolowanego, „ślepego" sub-agenta** (Agent tool) i daj mu pytanie, w którym KOTWICE są usunięte lub zamaskowane (ograniczenia zostają). Sub-agent nie widzi kotwicy → szacuje niezależnie. To jest sedno — izolacja, nie prośba.
4. **Wpływ kotwicy — domyślnie cytuj badanie, nie mierz na żywo.** Walidacja (31.05) pokazała, że pomiar na żywo jest kruchy (sub-agent bywa przerywany albo daje anomalie). Dlatego:
   - **Domyślnie:** podaj typowy rozjazd z badania — *„kotwica zwykle rozjeżdża wycenę tej samej pracy ~6× (mediana, 10 sytuacji × 4 modele)"*. Oznacz jako wartość ogólną, nie pomiar tego konkretnego pytania. To stabilne i uczciwe.
   - **Opcjonalnie (zaawansowane):** jeśli chcesz pomiaru dla TEGO pytania — spawnuj drugiego sub-agenta z kotwicą i TWARDĄ instrukcją *„odpowiedz natychmiast jedną liczbą, bez narzędzi, bez szukania"*. Pamiętaj: sub-agent CC (Opus) broni się sam → wynik to DOLNA granica (~3×), nie pełne 6×.
   ⛔ **ZAKAZ FABRYKACJI.** Nigdy nie wpisuj zmyślonej liczby wpływu („~1200–2000 zł", „dryf −70%"). Dozwolone tylko: cytat z badania (~6×), realny pomiar surowy, albo „nie zmierzono". Wymyślona liczba = porażka skilla — to ten sam błąd zakotwiczenia, który skill ma leczyć.
5. **Pokaż wynik:**
   - Rekomendacja = wersja ślepa (bez kotwicy).
   - Wpływ kotwicy = domyślnie rozjazd z badania (~6×, wartość ogólna). Jeśli zmierzony na żywo — podaj jako dolną granicę; nigdy nie szacuj z głowy.
   - Jeśli liczba była CONSTRAINT, zastosuj ją osobno, po szacunku („rynkowo ~X; Twój budżet Y to mieści / nie mieści").
   - Uczciwie: pokazujesz NIESTABILNOŚĆ wyceny (ta sama praca, różne liczby → różne ceny), NIE „prawdę rynkową" — referencją jest sam model bez kotwicy, nie obiektywny rynek.

## Czego NIE robić (potwierdzone empirycznie, 11 modeli)
- **NIE** dopisuj „zignoruj tę liczbę" — model i tak dryfuje (słaba, niestabilna ulga).
- **NIE** używaj „rozważ przeciwieństwo / czemu ta liczba może być zła" — to POGARSZA (zmusza model do wczepienia się w kotwicę).
- **NIE** licz na to, że model Z DOSTĘPEM DO INTERNETU sam się odkotwiczy — nie odkotwicza (zmierzone 31.05: internet bierny ~+444% wobec +500% bez sieci — praktycznie bez ulgi; dopiero wymuszony research łagodzi, i to nie do zera). Dostęp do sieci ≠ użycie sieci ≠ brak kotwicy.
- **NIE** zmyślaj wersji „z kotwicą" ani liczby wpływu — albo zmierz ją drugim wywołaniem (krok 4, surowy strzał), albo napisz „nie zmierzono". Zmyślona liczba w tabeli wpływu = porażka skilla.
- Jedyne, co działa: model nie widzi kotwicy.

## Wariant przenośny — OPCJONALNY (bez sub-agentów Claude Code)
Sam lek (procedura wyżej) NIE wymaga klucza ani OpenRoutera — liczy na sub-agentach Claude Code. Poniższe to opcja tylko dla kogoś, kto chce uruchomić pomiary BEZ Claude Code (np. zweryfikować efekt na innych modelach). Skrypty w `bin/` robią pełny pipeline na OpenRouter (klucz w Keychain `openrouter-api-key`):
- `bin/anchor-detect.py` — wykrywanie + maskowanie + ślepe oszacowanie (kotwica wbudowana w tekst).
- `bin/anchor-client-demo.py` — demo na realnych sytuacjach klienckich.
- `bin/anchor-online.py` — czy internet leczy kotwicę (offline vs web search, 3 warunki).
- `bin/anchor-table.py` — tabela do artykułu: zaniżenie/zawyżenie + rozjazd w złotówkach.
- `bin/anchor-stats.py` — przedziały ufności (bootstrap) z gotowych wyników.

## Uczciwe ograniczenie
Klasyfikacja ANCHOR/CONSTRAINT przy naturalnym języku trafia ~75% (nie 100%). Przy niepewności **pokaż obie wersje** (ślepą i zakotwiczoną) i oznacz, że to ocena, nie pewnik. Skill nie jest idealny: zostawia rozjazd ~1,2× (nie 1,0×), pojedyncze sytuacje do +70–100%.

## Dowód i metodologia
Pełne dane i skrypty pomiarowe są w katalogach `data/` i `bin/`. Metoda, wyniki i tabele — w README. Skrót: bez leku kotwica przesuwa wycenę o setki procent (rozjazd mediana 6×); internet tego nie naprawia; lek sprowadza rozjazd do ~1,2×.
