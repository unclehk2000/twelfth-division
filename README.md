# Twelfth Division

**Indicators built and tested but not yet published on TradingView.**

In Bleach, the Twelfth Division is the Gotei 13's research and development division: where new gear is built and tested before it goes out. This repo plays the same role for the Hueco Mundo indicator set. Each indicator has its own folder with:
- the script;
- a README;
- its TradingView publication text;
- mock-ups;
- the research scripts behind its odds (no market data).

Once an indicator is published, it moves to its own repository.

TradingView Pine Script v6. Open source under the Mozilla Public License 2.0.

## In the lab

| Indicator | What it is | Status |
|---|---|---|
| [Zabimaru](zabimaru/) | The NY opening range (09:30–10:00) as a live dealing range, an octant grid that follows price as the range forms, a NQ / ES / RTY triplet card, ATR10 with the volatility trend, and the session opens (Hihiō: 18:00, midnight, custom) | Built, compiles with 0 errors and 0 warnings, ready to publish |
| [Getsuga Tenshō](getsuga-tensho/) | Friday's Shikai mid → Monday's as this week's dealing range: eighths with fraction (price) labels, SDs at 1.5 / −0.5, PWH / PWL and the week open as reference lines, Mon–Fri day candles in the Session Map's style, and a card with the odds of each level by Friday | Built, compiles with 0 errors and 0 warnings, ready to publish |
| [Sharingan](sharingan/) | ICT's quarterly shift and IPDA data ranges: the anchor (last closed month or last structure shift), the 60 / 40 / 20-day look back as buy-side and sell-side liquidity (bold to the candle that swept it, ✕ there), the +20 / +40 / +60 cast forward, daily market structure (the last shifts and the flip level), the Quarterly Theory quarters and true year / month opens, and the walk-forward-tested odds of each level trading within 20 days and by +60 | Built, passes the local checks; not yet compiled on TradingView |
| [Mangekyō](mangekyo/) | Daily FVGs, volume imbalances and suspension blocks from the 20 / 40 / 60-day look back, or this week's and last week's: the most local ones above and below price, the one price is in graded in eighths across the chart as ICT grades it on the 1-minute chart, the gap's candles right of price (PO3) when price trades inside one, settlement-vs-last-trade bodies (ICT's widest), front-month / continuous / back-adjusted data, the week's premium and discount draw, and tested reach and hold odds against the same candles without a gap | Built, passes the local checks; not yet compiled on TradingView |
| [Benihime v2](benihime-v2/) | The RTH gap map with a tally card, a live FILL bar, live fill and CE odds, a Mobile layout and alerts | Built, compiles with 0 errors and 0 warnings. v1 is in [benihime](https://github.com/unclehk2000/benihime) |

## How each one was tested

Each number on a card passed the same rule before it was shown:
- pooled p < 0.05 with errors clustered by date;
- the same sign in 2018–24 and 2025–26;
- the same sign on NQ, ES and RTY.

The rule is in [stats-kit](https://github.com/unclehk2000/stats-kit). What did not pass is listed in each README, e.g. Benihime's confluence zones and Hihiō's open lines as magnets.

The research scripts in each `research/` folder read 1-minute CSVs from the original workspace. No market data is included; point them at your own files to re-run.

## Related

- [how-we-got-here](https://github.com/unclehk2000/how-we-got-here): the working archive behind the published indicators.
- [hydra](https://github.com/unclehk2000/hydra), [stats-kit](https://github.com/unclehk2000/stats-kit), [pinetools](https://github.com/unclehk2000/pinetools), [mockup](https://github.com/unclehk2000/mockup): the tools.

## Licence

Mozilla Public License 2.0, see [LICENSE](LICENSE). © Unclehk2000. Research tools, not financial advice.
