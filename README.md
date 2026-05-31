# PriceGuard

🇬🇧 [English version](README.en.md)

**Zapytaj AI o wycenę strony firmowej. Powiedz, że poprzednia agencja brała 30 000 zł — AI wyceni około 30 000. Powiedz, że brała 800 zł — wyceni jakieś 4 500. Ta sama praca, a wycena różni się sześć razy. Wystarczyła jedna liczba.**

To zakotwiczenie — błąd myślenia opisany już 50 lat temu. Gdy pytasz AI o wycenę, a w rozmowie padła wcześniej jakaś liczba, model dryfuje w jej stronę. Przez to zaniża albo zawyża wycenę, a Ty tracisz pieniądze. PriceGuard temu zapobiega: ukrywa tę liczbę przed modelem i wycenia niezależnie od niej.

---

## Czym jest zakotwiczenie

Pierwsza liczba, którą usłyszysz, przykleja się do Twojej oceny. Wpływa na nią nawet wtedy, gdy ta liczba jest przypadkowa i nie ma nic wspólnego z tematem.

To nie nowość. W 1974 roku Daniel Kahneman i Amos Tversky kazali ludziom zakręcić kołem fortuny, a potem zapytali: ile procent państw w ONZ to kraje afrykańskie? Kto wylosował 10, odpowiadał średnio 25%. Kto wylosował 65, odpowiadał aż 45%. Liczba z koła była zupełnie losowa, a mimo to przesunęła odpowiedzi.

Dan Ariely poszedł dalej. Poprosił ludzi, żeby zapisali dwie ostatnie cyfry numeru ubezpieczenia, a potem licytowali produkty. Im wyższe cyfry ktoś zapisał, tym wyżej licytował. Te cyfry nie miały nic wspólnego z wartością wina czy klawiatury, a mimo to ustawiały cenę.

## AI popełnia ten sam błąd

Modele językowe przejęły ten błąd po nas. Gdy wkleisz do czatu cudzą liczbę — „poprzednia agencja brała 30 000" — model dryfuje w jej stronę. Pytasz o uczciwą wycenę, a dostajesz odbicie tego, co przed chwilą przeczytał.

Jest jedna różnica. U człowieka tego błędu nie zmierzysz od ręki. U modelu zmierzysz — i możesz go wyłączyć.

---

## Ile Cię to kosztuje

Wystarczy, że klient sam rzuci cenę, a AI idzie za nią — w obie strony.

**Klient podaje za niską cenę → AI zaniża, a Ty oddajesz pieniądze.**
> „Budżet na szkolenie mamy jakieś **1 000 zł**." AI wycenia **1 000 zł** — choć dzień szkolenia jest wart około 5 000. Właśnie oddałeś 80% stawki.

**Klient podaje za wysoką cenę → AI zawyża, a Ty tracisz zlecenie.**
> „Poprzednia agencja brała **30 000 zł** za stronę." AI wycenia **30 000** — choć ta strona jest warta ~5 000. Z taką ofertą klient ucieka.

Poniżej: o ile zwykłe AI mija się z uczciwą wyceną, gdy klient sam poda cenę — i jak blisko zera trzyma to PriceGuard.

| Praca | Klient za nisko → AI | → PriceGuard | Klient za wysoko → AI | → PriceGuard |
|---|---|---|---|---|
| Szkolenie 1-dniowe | **−80%** | −10% | +380% | +70% |
| Audyt SEO | **−40%** | −20% | +330% | 0% |
| Social media | **−30%** | −10% | +60% | 0% |
| Kampania Meta | **−27%** | −18% | +264% | 0% |
| Strona firmowa | −10% | 0% | +500% | +70% |
| Stawka godzinowa | 0% | 0% | +433% | +33% |
| Film promocyjny | 0% | 0% | +900% | +100% |
| Godzina konsultacji | 0% | +10% | +1900% | −10% |
| **Mediana (10 sytuacji)** | **−19%** | **0%** | **+355%** | **+8%** |

*Odchylenie od uczciwej wyceny (model bez kotwicy), 4 modele, mediana. Zwykłe AI zaniża nawet o 80% i zawyża o setki procent. PriceGuard w obie strony trzyma się zera.*

**Czytaj to jako niestabilność, nie trafność.** PriceGuard nie zna „prawdziwej" ceny rynkowej. Pokazuje tylko jedno: zwykły model podaje liczbę niemal losową, zależną od tego, co usłyszał. PriceGuard zastępuje ją jedną stabilną.

---

## Czy internet to naprawia? Nie.

Wielu liczy, że wystarczy dać AI wyszukiwarkę, a model przestanie papugować liczbę. Sprawdziliśmy to — 4 modele, 10 sytuacji wycenowych, 3 warunki, 240 wywołań.

| Warunek | Zaniża (niska kotwica) / Zawyża (wysoka), mediana |
|---|---|
| Bez internetu | −19% / **+355%** |
| Internet bierny (model sam decyduje) | −25% / **+276%** |
| Internet + wymuszony research | −33% / **+90%** |
| **PriceGuard (izolacja)** | **+0% / +8%** |

Sam internet prawie nie pomaga — model ma wyszukiwarkę, a i tak odpowiada z pamięci. Wymuszony research zmniejsza zawyżanie, ale za to pogłębia zaniżanie. Przesuwa problem, nie usuwa go. Stabilna w obie strony jest tylko izolacja.

---

## Lek: izolacja

Działa tylko jedno: model nie może zobaczyć kotwicy. Prośba „zignoruj tę liczbę" nie wystarcza — to nie pomaga. Liczbę trzeba fizycznie ukryć. PriceGuard robi to w pięciu krokach:

1. **Wykrywa** każdą liczbę w pytaniu i kontekście.
2. **Klasyfikuje** każdą liczbę:
   - **KOTWICA** — cudza sugestia, oferta albo cena. Nie powinna ustalać uczciwej wartości.
   - **OGRANICZENIE** — twardy fakt, którego odpowiedź musi użyć (budżet jako limit, pojemność, czas).
   - Test: czy uczciwa wartość zmienia się dlatego, że ta liczba jest inna? Jeśli nie, to kotwica.
3. **Odpala ślepego pod-agenta.** Pod-agent dostaje pytanie z usuniętymi kotwicami (ograniczenia zostają). Nie widzi kotwicy, więc wycenia niezależnie.
4. **(Opcjonalnie) mierzy wpływ kotwicy** — osobnym, surowym wywołaniem.
5. **Pokazuje wynik.** Rekomendacja to ślepa wycena. Ograniczenia dokładasz osobno, na końcu.

---

## Instalacja — to wszystko, czego potrzebujesz

PriceGuard to **skill do Claude Code**. Działa lokalnie, przez sub-agenty Claude Code. **Nie wymaga żadnego klucza ani konta** — kopiujesz katalog i gotowe.

### macOS / Linux

```bash
cp -r priceguard ~/.claude/skills/priceguard
```

### Windows (PowerShell)

```powershell
Copy-Item -Recurse priceguard "$env:USERPROFILE\.claude\skills\priceguard"
```

Skill włącza się sam, gdy poprosisz Claude Code o wycenę, a w rozmowie jest cudza liczba. To cała instalacja. Reszta tej strony to materiały badawcze — **nie musisz ich ruszać**.

---

## Dla sceptyków: odtwórz nasze pomiary (opcjonalne)

Skrypty w `bin/` to **nasza infrastruktura badawcza**. Posłużyły, żeby sprawdzić efekt zakotwiczenia na 11 modelach (Gemini, GPT, Llama, Mistral…) — i udowodnić, że mają go wszystkie, nie tylko Claude. **Do używania PriceGuarda są zbędne.** Odpalasz je tylko wtedy, gdy chcesz sam zweryfikować liczby z tej strony.

Wtedy potrzebujesz Pythona 3 i klucza [OpenRouter](https://openrouter.ai) (jeden klucz daje dostęp do wielu modeli):

**macOS / Linux** — klucz w Keychain *albo* w zmiennej środowiskowej:

```bash
# wariant A: Keychain macOS (skrypty czytają go same)
security add-generic-password -s openrouter-api-key -a "$USER" -w "sk-or-v1-..."
# wariant B: zmienna środowiskowa
export OPENROUTER_API_KEY="sk-or-v1-..."
python3 bin/anchor-online.py
```

**Windows (PowerShell)** — zmienna środowiskowa (`python`, nie `python3`):

```powershell
setx OPENROUTER_API_KEY "sk-or-v1-..."
# otwórz terminal na nowo, potem:
python bin\anchor-online.py
```

| Skrypt | Co robi |
|---|---|
| `bin/anchor-spike.py` | Pierwszy, szybki test efektu zakotwiczenia (etap 1) |
| `bin/anchor-detect.py` | Wykrywa i maskuje kotwicę, potem wycenia na ślepo (etap 2) |
| `bin/anchor-ambiguous.py` | Test na liczbach dwuznacznych, najtrudniejszy przypadek (etap 2b) |
| `bin/anchor-discriminate.py` | Sprawdza, czy model odróżnia kotwicę od ograniczenia (etap 2c) |
| `bin/anchor-client-demo.py` | Demo na realnych sytuacjach klienckich (baza / zignoruj / przeciwieństwo / izolacja) |
| `bin/anchor-online.py` | Czy internet to naprawia? (bez sieci kontra wyszukiwarka, 3 warunki) |
| `bin/anchor-table.py` | Buduje tabelę rozjazdu z tej strony |
| `bin/anchor-stats.py` | Liczy przedziały ufności (bootstrap) z zapisanych wyników |

Każdy skrypt korzysta tylko z biblioteki standardowej Pythona. Uruchom z `--help`, żeby zobaczyć opcje.

---

## Uczciwe ograniczenia

- **Mierzymy niestabilność, nie prawdę.** Punktem odniesienia jest ślepa wycena samego modelu, a nie zweryfikowana cena rynkowa. Teza brzmi: ta sama praca dostaje około sześciu różnych cen zależnie od przypadkowej liczby, a PriceGuard daje jedną stabilną.
- **Podział na kotwicę i ograniczenie trafia w około 75% przypadków.** Gdy nie ma pewności, skill pokazuje obie wersje.
- **PriceGuard nie jest idealny.** Ścina rozjazd do około 1,2×, a nie do 1,0×. Kilka kategorii nadal przecieka 70–100% przy wysokiej kotwicy.

---

## Licencja

MIT — zobacz [LICENSE](LICENSE).
