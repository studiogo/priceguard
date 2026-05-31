# PriceGuard

🇵🇱 [Wersja polska / Polish version](README.md)

**Anchoring is a 50-year-old thinking error. The first number you hear shifts your judgment — even when that number is meaningless. AI models make this same mistake, just like humans. When you ask AI to price something and someone's number is already in the conversation, the model drifts toward it — and you can lose money. PriceGuard prevents that: it hides the number from the model and gives an estimate that ignores it.**

---

## What anchoring is

The first number you hear sticks to your judgment. It sways you even when that number is random and unrelated to the topic.

This is not new. In 1974, Daniel Kahneman and Amos Tversky had people spin a wheel of fortune, then asked what percentage of UN countries were African. People who landed on 10 guessed 25% on average. People who landed on 65 guessed 45%. The wheel was random. It moved the answer anyway.

Dan Ariely went further. He asked people to write the last two digits of their social security number, then bid on products. Higher digits led to higher bids. The number had nothing to do with the value of the wine or the keyboard, yet it set the price.

## AI makes the same mistake

Language models inherit this bias from us. Drop someone else's number into the chat — "the last agency charged 30,000" — and the model drifts toward it. You ask for a fair quote and get an echo of what the model heard.

There's one difference. In humans you can't measure it on the spot. In a model you can — and you can switch it off.

---

## What it costs you

The same job, priced twice. Once after the client throws a **low** number, once after a **high** one. "Spread" tells you how many times the high-anchor price beats the low-anchor price. A fair tool should stay near 1×.

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

You lose both ways. A low anchor underprices the job — you leave money on the table. A high one overprices it — you scare the client off, or quote a number you can't defend.

**Read this as instability, not accuracy.** PriceGuard does not know the "true" market price. It only shows that a plain model hands you a near-random number — driven by what it heard — and replaces it with one stable answer.

---

## Does internet access fix it? No.

A common assumption: "give the AI a search engine and it will stop parroting the number." We tested it — 4 models, 10 pricing situations, 3 conditions, 240 calls.

| Condition | Underprices (low anchor) / Overprices (high anchor), median |
|---|---|
| No internet | −19% / **+355%** |
| Internet, passive (model decides) | −25% / **+276%** |
| Internet, active research (forced to check rates) | −33% / **+90%** |
| **PriceGuard (isolation)** | **+0% / +8%** |

Passive internet barely helps — the model has search but answers from memory anyway. Forced research softens the overpricing but deepens the underpricing. It moves the problem, it doesn't remove it. Only isolation is stable in both directions.

---

## The cure: isolation

One thing works — the model must not see the anchor. Not a "please ignore this number" request (that doesn't help), but physically hiding it. PriceGuard runs five steps:

1. **Detect** every number in the question and context.
2. **Classify** each number:
   - **ANCHOR** — someone else's suggestion/offer/price. It should not set the fair value.
   - **CONSTRAINT** — a hard fact the answer must use (a budget as a limit, capacity, time).
   - Test: *does the fair value change because this number is different?* If not, it's an anchor.
3. **Spawn a blind sub-agent.** It gets the question with anchors removed (constraints stay). It never sees the anchor, so it estimates independently.
4. **(Optional) measure the impact** with a separate, raw call.
5. **Show the result.** The recommendation is the blind estimate. Constraints are applied separately, at the end.

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

- **We measure instability, not truth.** The reference is the model's own blind estimate, not a verified market price. The claim is: *the same work gets ~6 different prices depending on a random number — PriceGuard gives one stable answer.*
- **The ANCHOR/CONSTRAINT split is ~75% accurate** on natural language. When unsure, the skill shows both versions.
- **Not perfect.** PriceGuard cuts the spread to ~1.2×, not 1.0×. A few categories still leak +70–100% at the high anchor.

---

## License

MIT — see [LICENSE](LICENSE).
