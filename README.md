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
| [Sharingan](sharingan/) | ICT's quarterly shift and IPDA data ranges: the anchor (last closed month or last structure shift), the 60 / 40 / 20-day look back as buy-side and sell-side liquidity (bold to the candle that swept it, ✕ there), the +20 / +40 / +60 cast forward, daily market structure (the last shifts and the flip level), the Quarterly Theory quarters and true year / month opens, and the walk-forward-tested odds of each level trading within 20 days and by +60. v3: the same 60 / 40 / 20 down the Quarterly Theory fractal (H, M15, M5, M1 layers with tested reach odds), Daye's A / M / D / X quarters for the week, day and session, and an HTF FVG → sweep → OB → SMT entry model with backtest marks and a live scorecard (tested: no edge) | v3 built, passes the local checks; not yet compiled on TradingView |
| [Mangekyō](mangekyo/) | v3: daily (Mangekyō) and weekly (Eternal Mangekyō) FVGs, volume imbalances and suspension blocks in one script with one Timeframe switch: the most local above and below price, the one price is in graded in octants, inversion FVGs, wick CEs, PO3 candles with a live forming candle (no lag, fully personalisable), and a compact ✓ / ✕ card with the tested reach and touch-hold odds and caution rows only when live | v3 built, passes the local checks; not yet compiled on TradingView |
| [Hadō 99](hado-99/) | The DXY / oil macro regime card and the C2 → C3 Fractal Model with tested odds, now with personalisable HTF (PO3) candles: Model, ICT or custom body, border and wick colours, sizes, tags, times, countdown, the forming candle's open and the last candle's high / low | Built, passes the local checks; not yet compiled on TradingView. The earlier version is in [hado-99](https://github.com/unclehk2000/hado-99) |
| [Benihime v2](benihime-v2/) | The RTH gap map with a tally card, a live FILL bar, live fill and CE odds, a Mobile layout and alerts | Built, compiles with 0 errors and 0 warnings. v1 is in [benihime](https://github.com/unclehk2000/benihime) |
| [Benihime v3](benihime-v3/) | The RTH ORG as the day's dealing range (Zabimaru-style grid, CE ✓ / fill ✓ with the sisters, ICT's CE by 10:00), this week's ORG CEs, RTH-only structure and the NQ / ES / RTY triplet, after a HYDRA pass on the lecture claims | Built, passes the local checks; not yet compiled on TradingView |
| [Rinnegan](rinnegan/) | Dealing ranges from a swept swing (100) to the next swing the other way (0) on ST and IT swings, tracked live (EQ touched, 0 broken, 100 taken), with the live odds of each end trading first (= where price sits, tested within 3 points); since v1.1 the DR / IDR defining ranges (RDR, ODR, ADR) with STD lines and their tested rates. The popular rules sit beside their chance rates | New (Nov 2026), passes the local checks; not yet compiled on TradingView |
| [Eternal Mangekyō](eternal-mangekyo/) | Merged into Mangekyō v3 (Timeframe → Weekly · Eternal Mangekyō); the folder keeps the weekly research | Merged |
| [Sakanade](sakanade/) | Is the high or low already in? Live odds that the day's high and low (18:00–17:00 ET) and the week's hold to the close: gradient-boosted trees for the day (1.1 million samples, run inside Pine), a Brownian model for the week (the trees did not beat it), on price, in a pane and on a card | New (Nov 2026), passes the local checks; not yet compiled on TradingView |
| [Shinsō](shinso/) | ICT's draw on liquidity with machine-learned odds: PDH / PDL, PWH / PWL, PMH / PML and the Asia and London ranges, each with the chance it trades before 16:59, and which of the nearest buy-side and sell-side pools goes first (gradient-boosted trees, Brier 0.088 vs 0.167 flat). ICT's draw readings tested: none moved the odds | New (Nov 2026), passes the local checks; not yet compiled on TradingView |
| [Ryūjin Jakka](ryujin-jakka/) | Session range forecasts: the expected range of Asia, London, NY AM and NY PM with calibrated 25–75% / 10–90% bands (held 47–52% / 76–80% out of sample), projected from the session's low and high while it runs. Release days tested: FOMC afternoons ran 2.5×; Asia and London 7–10% quieter before CPI / NFP | New (Nov 2026), passes the local checks; not yet compiled on TradingView |
| [Suzumebachi](suzumebachi/) | Market structure at a chosen sensitivity with every MSS / BOS labelled by its scenario (raid, FVG, stop size, prior-day location, midnight open) and its tested 1R odds, trained on ES + YM and checked on 2025–26 and NQ / RTY (739,504 breaks). Every passing scenario is a failing break: a sell BOS chasing the prior day's top quarter returns to its extreme first 54–56% (56% overnight); the textbook MSS is a coin flip (50.5%) | New (Nov 2026), passes the local checks; not yet compiled on TradingView |
| [Hōgyoku](hogyoku/) | Four-market HTF profiler: NQ / ES / YM / RTY on 15m, 1H, 4H, D as a price delivery matrix (C2 vs C1), the four markets' C1-C2-C3 aligned on C1 (SMT / PSP at a glance), per-market reach odds for the forming candle, and the 15 of 72 matrix readings that beat the drift (0.5–2.5 points each; the 15m laggard catch-up is the one cross-market regression). Inspired by the GXV HTF Profiler's concepts; no GXV code | New (Nov 2026), passes the local checks; not yet compiled on TradingView |

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
