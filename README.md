# PriceGuard

🇬🇧 [English version](README.en.md)

**Zakotwiczenie to błąd myślenia znany od 50 lat. Pierwsza liczba, którą usłyszysz, przesuwa Twoją ocenę — nawet gdy ta liczba jest bez sensu. Modele AI popełniają ten błąd tak samo jak ludzie. Gdy pytasz AI o wycenę, a w rozmowie padła już czyjaś liczba, model dryfuje za nią — i możesz przez to stracić pieniądze. PriceGuard temu zapobiega: ukrywa liczbę przed modelem i daje wycenę niezależną od niej.**

---

## Czym jest zakotwiczenie

Pierwsza liczba, którą usłyszysz, przykleja się do Twojej oceny. Wpływa na Ciebie, nawet gdy ta liczba jest przypadkowa i nie ma związku z tematem.

To nie nowość. W 1974 roku Daniel Kahneman i Amos Tversky dali ludziom zakręcić kołem fortuny. Potem pytali, ile procent krajów w ONZ to kraje afrykańskie. Kto wylosował 10, zgadywał średnio 25%. Kto wylosował 65, zgadywał aż 45%. Liczba z koła była losowa. A i tak przesunęła odpowiedź.

Dan Ariely poszedł dalej. Poprosił ludzi, żeby zapisali dwie ostatnie cyfry numeru ubezpieczenia, a potem licytowali produkty. Wyższy numer dawał wyższe oferty. Cyfra nie miała żadnego związku z wartością wina czy klawiatury, a i tak ustawiała cenę.

## AI popełnia ten sam błąd

Modele językowe dziedziczą ten błąd po nas. Wklejasz do czatu cudzą liczbę — „poprzednia agencja brała 30 000" — a model dryfuje w jej stronę. Pytasz o uczciwą wycenę, a dostajesz echo tego, co model usłyszał.

Różnica jest jedna. U człowieka tego błędu nie zmierzysz na poczekaniu. U modelu zmierzysz — i możesz go wyłączyć.

---

## Ile Cię to kosztuje

Ta sama praca, wyceniona dwa razy. Raz gdy klient rzuci **niską** liczbę, raz gdy **wysoką**. „Rozjazd" mówi, ile razy cena przy wysokiej kotwicy przebija cenę przy niskiej. Uczciwe narzędzie powinno trzymać się blisko 1×.

| Praca | Klient mówi | Zwykłe AI | Rozjazd | Z PriceGuard | Rozjazd |
|---|---|---|---|---|---|
| Strona firmowa | 800 → 30 000 | 4 500 → 30 000 | **6,7×** | 5 000 → 8 500 | **1,7×** |
| Stawka godzinowa | 40 → 800 | 150 → 800 | 5,3× | 150 → 200 | 1,3× |
| Audyt SEO | 500 → 50 000 | 3 000 → 21 500 | 7,2× | 4 000 → 5 000 | 1,2× |
| Film promocyjny | 300 → 40 000 | 5 000 → 50 000 | 10,0× | 5 000 → 10 000 | 2,0× |
| Logo + identyfikacja | 50 → 15 000 | 5 000 → 15 000 | 3,0× | 4 000 → 4 000 | 1,0× |
| Startup (pre-seed) | 50 tys → 50 mln | 1,4 mln → 3,0 mln | 2,2× | 3,0 mln → 3,5 mln | 1,2× |
| Social media / mies. | 500 → 30 000 | 1 750 → 4 000 | 2,3× | 2 250 → 2 500 | 1,1× |
| Godzina konsultacji | 100 → 5 000 | 250 → 5 000 | 20,0× | 275 → 225 | 0,8× |
| Szkolenie 1-dniowe | 1 000 → 80 000 | 1 000 → 24 000 | 24,0× | 4 500 → 8 500 | 1,9× |
| Kampania Meta / mies. | 1 000 → 100 000 | 2 000 → 10 000 | 5,0× | 2 250 → 2 750 | 1,2× |
| **Mediana** | | | **6,0×** | | **1,2×** |

*Kwoty w złotych (polski rynek freelancera), 4 modele, mediana. Zwykłe AI rozjeżdża tę samą pracę średnio 6×. PriceGuard trzyma ją koło 1,2×.*

Tracisz w obie strony. Niska kotwica zaniża cenę — zostawiasz pieniądze na stole. Wysoka zawyża — odstraszasz klienta albo podajesz cenę, której nie obronisz.

**Czytaj to jako niestabilność, nie trafność.** PriceGuard nie zna „prawdziwej" ceny rynkowej. Pokazuje tylko, że zwykły model daje Ci liczbę niemal losową — zależną od tego, co usłyszał — i zastępuje ją jedną stabilną odpowiedzią.

---

## Czy internet to naprawia? Nie.

Częste założenie: „dam AI wyszukiwarkę i przestanie papugować liczbę". Sprawdziliśmy to — 4 modele, 10 sytuacji wycenowych, 3 warunki, 240 wywołań.

| Warunek | Zaniża (niska kotwica) / Zawyża (wysoka), mediana |
|---|---|
| Bez internetu | −19% / **+355%** |
| Internet bierny (model sam decyduje) | −25% / **+276%** |
| Internet + wymuszony research | −33% / **+90%** |
| **PriceGuard (izolacja)** | **+0% / +8%** |

Bierny internet prawie nie pomaga — model ma wyszukiwarkę, ale i tak odpowiada z pamięci. Wymuszony research łagodzi zawyżanie, ale pogłębia zaniżanie. Przesuwa problem, nie usuwa go. Tylko izolacja jest stabilna w obie strony.

---

## Lek: izolacja

Działa jedno — model nie może zobaczyć kotwicy. Nie prośba „zignoruj tę liczbę" (to nie pomaga), tylko fizyczne ukrycie. PriceGuard robi pięć kroków:

1. **Wykrywa** każdą liczbę w pytaniu i kontekście.
2. **Klasyfikuje** każdą liczbę:
   - **KOTWICA** — cudza sugestia, oferta, cena. Nie powinna ustalać uczciwej wartości.
   - **OGRANICZENIE** — twardy fakt, którego odpowiedź musi użyć (budżet jako limit, pojemność, czas).
   - Test: *czy uczciwa wartość zmienia się dlatego, że ta liczba jest inna?* Jeśli nie, to kotwica.
3. **Odpala ślepego pod-agenta.** Pod-agent dostaje pytanie z usuniętymi kotwicami (ograniczenia zostają). Nigdy nie widzi kotwicy, więc szacuje niezależnie.
4. **(Opcjonalnie) mierzy wpływ** — osobnym, surowym wywołaniem.
5. **Pokazuje wynik.** Rekomendacja to ślepa wycena. Ograniczenia stosujesz osobno, na końcu.

---

## Instalacja

PriceGuard działa w dwóch postaciach: jako **skill do Claude Code** (bez klucza) i jako **skrypty Pythona**, które odtwarzają badanie (potrzebny klucz OpenRouter).

### Skill — macOS / Linux

```bash
cp -r priceguard ~/.claude/skills/priceguard
```

### Skill — Windows (PowerShell)

```powershell
Copy-Item -Recurse priceguard "$env:USERPROFILE\.claude\skills\priceguard"
```

Skill włącza się sam, gdy poprosisz Claude Code o wycenę, a w grze jest cudza liczba.

### Skrypty (opcjonalnie — żeby odtworzyć pomiary)

Potrzebujesz Pythona 3 i klucza [OpenRouter](https://openrouter.ai).

**macOS / Linux** — trzymaj klucz w Keychain *albo* w zmiennej środowiskowej:

```bash
# wariant A: Keychain macOS (skrypty czytają go same)
security add-generic-password -s openrouter-api-key -a "$USER" -w "sk-or-v1-..."
# wariant B: zmienna środowiskowa
export OPENROUTER_API_KEY="sk-or-v1-..."
python3 bin/anchor-online.py
```

**Windows (PowerShell)** — użyj zmiennej środowiskowej (`python`, nie `python3`):

```powershell
setx OPENROUTER_API_KEY "sk-or-v1-..."
# otwórz terminal na nowo, potem:
python bin\anchor-online.py
```

---

## Skrypty

| Skrypt | Co robi |
|---|---|
| `bin/anchor-detect.py` | Wykrywa i maskuje kotwicę, potem szacuje na ślepo |
| `bin/anchor-client-demo.py` | Demo na sytuacjach klienckich (baza / zignoruj / przeciwieństwo / izolacja) |
| `bin/anchor-online.py` | Czy internet to naprawia? (bez sieci kontra wyszukiwarka, 3 warunki) |
| `bin/anchor-table.py` | Buduje tabelę rozjazdu z tej strony |
| `bin/anchor-stats.py` | Przedziały ufności (bootstrap) z zapisanych wyników |

Każdy skrypt korzysta tylko z biblioteki standardowej Pythona. Uruchom z `--help`, żeby zobaczyć opcje.

---

## Uczciwe ograniczenia

- **Mierzymy niestabilność, nie prawdę.** Punktem odniesienia jest ślepa wycena samego modelu, nie zweryfikowana cena rynkowa. Teza brzmi: *ta sama praca dostaje ~6 różnych cen zależnie od przypadkowej liczby — PriceGuard daje jedną stabilną.*
- **Podział KOTWICA / OGRANICZENIE trafia ~75%** przy naturalnym języku. Przy wątpliwości skill pokazuje obie wersje.
- **Nie jest idealny.** PriceGuard ścina rozjazd do ~1,2×, nie do 1,0×. Kilka kategorii nadal przecieka +70–100% przy wysokiej kotwicy.

---

## Licencja

MIT — zobacz [LICENSE](LICENSE).
