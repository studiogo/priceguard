# PriceGuard

🇵🇱 [Wersja polska / Polish version](README.md)

**Ask AI to price a company website. Say the previous agency charged 30,000 zł — it will quote around 30,000. Say it charged 800 zł — it will quote about 4,500. The same work, yet the quote differs sixfold. One number did that.**

This is anchoring — a thinking error described 50 years ago. When you ask AI to price something and a number already came up earlier in the chat, the model drifts toward it. That makes it underprice or overprice the job, and you lose money. PriceGuard prevents this: it hides the number from the model and prices independently of it.

---

## What anchoring is

The first number you hear sticks to your judgment. It affects that judgment even when the number is random and has nothing to do with the topic.

This is not new. In 1974, Daniel Kahneman and Amos Tversky had people spin a wheel of fortune, then asked: what percentage of UN countries are African? People who landed on 10 answered 25% on average. People who landed on 65 answered 45%. The wheel was completely random, yet it shifted the answers.

Dan Ariely went further. He asked people to write the last two digits of their social security number, then bid on products. The higher the digits someone wrote, the higher they bid. Those digits had nothing to do with the value of the wine or the keyboard, yet they set the price.

## AI makes the same mistake

Language models picked up this error from us. Drop someone else's number into the chat — "the last agency charged 30,000" — and the model drifts toward it. You ask for a fair quote and get a reflection of what it just read.

There is one difference. In a human you can't measure this error on the spot. In a model you can — and you can switch it off.

---

## What it costs you

The same work, priced twice. Once after the client throws a low number, once after a high one. The "spread" column shows how many times the high-anchor quote beats the low-anchor one. A fair tool should stay near 1×.

| Job | Client says | Plain AI | Spread | With PriceGuard | Spread |
|---|---|---|---|---|---|
| Company website | 800 → 30,000 | 4,500 → 30,000 | **6.7×** | 5,000 → 8,500 | **1.7×** |
| Hourly rate | 40 → 800 | 150 → 800 | 5.3× | 150 → 200 | 1.3× |
| SEO audit | 500 → 50,000 | 3,000 → 21,500 | 7.2× | 4,000 → 5,000 | 1.2× |
| Promo video | 300 → 40,000 | 5,000 → 50,000 | 10.0× | 5,000 → 10,000 | 2.0× |
| Logo + identity | 50 → 15,000 | 5,000 → 15,000 | 3.0× | 4,000 → 4,000 | 1.0× |
| Startup pre-seed | 50k → 50M | 1.4M → 3.0M | 2.2× | 3.0M → 3.5M | 1.2× |
| Social media / mo | 500 → 30,000 | 1,750 → 4,000 | 2.3× | 2,250 → 2,500 | 1.1× |
| Strategy hour | 100 → 5,000 | 250 → 5,000 | 20.0× | 275 → 225 | 0.8× |
| 1-day training | 1,000 → 80,000 | 1,000 → 24,000 | 24.0× | 4,500 → 8,500 | 1.9× |
| Meta campaign / mo | 1,000 → 100,000 | 2,000 → 10,000 | 5.0× | 2,250 → 2,750 | 1.2× |
| **Median** | | | **6.0×** | | **1.2×** |

*Amounts in PLN (Polish freelance market), 4 models, median across runs. Plain AI swings the same job ~6× on average. PriceGuard holds it near 1.2×.*

You lose on both sides. A low anchor underprices the job and you leave money on the table. A high anchor overprices it and you scare the client off — or quote a rate you can't defend.

**Read this as instability, not accuracy.** PriceGuard does not know the "true" market price. It shows one thing only: a plain model gives you a near-random number that depends on what it heard. PriceGuard replaces it with one stable answer.

---

## Does internet access fix it? No.

Many assume that giving AI a search engine will stop it from parroting the number. We tested it — 4 models, 10 pricing situations, 3 conditions, 240 calls.

| Condition | Underprices (low anchor) / Overprices (high anchor), median |
|---|---|
| No internet | −19% / **+355%** |
| Internet, passive (model decides) | −25% / **+276%** |
| Internet, active research (forced to check rates) | −33% / **+90%** |
| **PriceGuard (isolation)** | **+0% / +8%** |

The internet alone barely helps — the model has search but answers from memory anyway. Forced research reduces the overpricing but deepens the underpricing instead. It moves the problem, it doesn't remove it. Only isolation is stable in both directions.

---

## The cure: isolation

Only one thing works: the model must not see the anchor. A "please ignore this number" request is not enough — it doesn't help. The number has to be physically hidden. PriceGuard does it in five steps:

1. **Detects** every number in the question and context.
2. **Classifies** each number:
   - **ANCHOR** — someone else's suggestion, offer, or price. It should not set the fair value.
   - **CONSTRAINT** — a hard fact the answer must use (a budget as a limit, capacity, time).
   - Test: does the fair value change because this number is different? If not, it's an anchor.
3. **Spawns a blind sub-agent.** It gets the question with anchors removed (constraints stay). It never sees the anchor, so it estimates independently.
4. **(Optional) measures the anchor's impact** with a separate, raw call.
5. **Shows the result.** The recommendation is the blind estimate. You apply constraints separately, at the end.

---

## Install

PriceGuard ships in two forms: a **Claude Code skill** (no key needed) and **standalone Python scripts** that reproduce the study (need an OpenRouter key).

### Skill — macOS / Linux

```bash
cp -r priceguard ~/.claude/skills/priceguard
```

### Skill — Windows (PowerShell)

```powershell
Copy-Item -Recurse priceguard "$env:USERPROFILE\.claude\skills\priceguard"
```

The skill loads automatically when you ask Claude Code to price something and an outside number is in play.

### Scripts (optional, to reproduce the measurements)

You need Python 3 and an [OpenRouter](https://openrouter.ai) API key.

**macOS / Linux** — store the key in the Keychain *or* an environment variable:

```bash
# option A: macOS Keychain (the scripts read it automatically)
security add-generic-password -s openrouter-api-key -a "$USER" -w "sk-or-v1-..."
# option B: environment variable
export OPENROUTER_API_KEY="sk-or-v1-..."
python3 bin/anchor-online.py
```

**Windows (PowerShell)** — use an environment variable (`python`, not `python3`):

```powershell
setx OPENROUTER_API_KEY "sk-or-v1-..."
# reopen the terminal, then:
python bin\anchor-online.py
```

---

## Scripts

| Script | What it does |
|---|---|
| `bin/anchor-detect.py` | Detect + mask the anchor, then estimate blind |
| `bin/anchor-client-demo.py` | The client-situation demo (baseline / ignore / opposite / isolation) |
| `bin/anchor-online.py` | Does internet fix it? (offline vs web search, 3 conditions) |
| `bin/anchor-table.py` | Builds the spread table above |
| `bin/anchor-stats.py` | Bootstrap confidence intervals from saved results |

Each script uses only the Python standard library. Run with `--help` for options.

---

## Honest limitations

- **We measure instability, not truth.** The reference is the model's own blind estimate, not a verified market price. The claim is: the same work gets about six different prices depending on a random number, and PriceGuard gives one stable answer.
- **The ANCHOR/CONSTRAINT split is right about 75% of the time** on natural language. When unsure, the skill shows both versions.
- **PriceGuard is not perfect.** It cuts the spread to about 1.2×, not 1.0×. A few categories still leak 70–100% at the high anchor.

---

## License

MIT — see [LICENSE](LICENSE).
