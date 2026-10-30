# Mangekyō: what the daily gaps did

NQ, ES, RTY daily 2010–26 and YM 2017–26. Daily candles are the front month, back-adjusted, with the settlement as close unless stated. Settlement vs last trade uses 2018–26, from 1-minute bars.

## The test

Each gap was matched with **5 three-candle windows that left no gap**:
- same symbol and direction, within ±2 years;
- the middle candle moved as far (body in ATR);
- candle 3 closed as far from its own low (high).

The control zone hangs from candle 3 with the real gap's width. Both go through the same lifecycle: first touch, CE, far edge traded, a close beyond the far edge.

Differences are real minus control, with errors clustered by week. The suite's rule for a number on the card:
- p < 0.05;
- the same sign in 2010–24 and 2025–26;
- the same sign on NQ, ES and RTY.

## Census

| Kind | Per year, per market | Median width (ATR) | Back within 5 / 20 days | Closed beyond within 60 days |
|---|---|---|---|---|
| FVG | 54–60 | 0.28 | 70% / 84% | 78% |
| Suspension block | 15–21 | 0.55 | 75% / 86% | 75% |
| Volume imbalance | 66–73 | 0.05 | 74% / 86% | 84% |

## Gaps against the same candles with no gap (FVG, 2010–26: 3,434 gaps, 3,253 touched)

| Outcome | Gap | No gap | Difference | t |
|---|---|---|---|---|
| Near edge back within 20 days | 83.7% | 85.9% | −2.1 | −2.0 |
| CE traded within 20 days | 78.0% | 80.9% | −2.9 | −2.4 |
| **First touch day holds the far edge** | **48.7%** | **45.0%** | **+3.5** | **+3.7** |
| Not closed beyond within 10 days of the touch | 29.3% | 28.4% | +1.1 | +1.0 |
| 1 ATR bounce before a close beyond | 42.7% | 42.1% | +1.0 | +0.8 |

- **Draw:** gaps are not revisited more often; slightly less (the displacement carries on).
- **First touch:** the far edge (candle 1's high or low) stops the touch day 3.5 points more often. That passes the suite's rule:
  - NQ +4.1, ES +2.9, RTY +6.0, YM −0.4;
  - 2010–24 +3.5, 2025–26 +4.2.
- **After the touch day:** no edge.

## Volume, structure, displacement, the week

| Split (touch day holds, gap vs no gap) | n | Gap | No gap | Difference | t |
|---|---|---|---|---|---|
| Middle candle volume: low tercile | 1,083 | 42.8% | 36.4% | +6.3 | +4.1 |
| Middle candle volume: mid tercile | 1,082 | 47.7% | 43.8% | +3.9 | +2.4 |
| Middle candle volume: high tercile | 1,083 | 55.4% | 55.1% | +0.3 | +0.2 |
| Closed beyond the last swing (break) | 1,805 | 52.4% | 47.5% | +4.9 | +4.1 |
| No break | 1,448 | 44.0% | 42.2% | +1.8 | +1.3 |
| Candle 1 or 2 swept the last swing | 833 | 48.3% | 46.4% | +1.8 | +1.1 |
| Gap in last week's discount (bull) / premium (bear) | 462 | 33.3% | 34.5% | −1.2 | −0.5 |
| Middle candle body ≥ 1 ATR | 964 | 67.0% | 65.2% | +1.8 | +1.1 |

At the same width (logit with errors clustered by week):

| Term | Effect | z |
|---|---|---|
| High-volume tercile | −2 points | −0.8 |
| Break | +4 points | 1.6 (negative on NQ and in 2025–26) |
| Sweep | +1 point | 0.4 |

So:
- **Volume:** high-volume gaps hold more in raw terms only because they are wider. Against the same candles their edge is nil.
- **Structure:** the edge sits mostly in break gaps, but the gap between break and no-break isn't significant.
- **Width carries everything.** Touch day holds by width: 0.1 ATR 20%, 0.25 48%, 0.5 71%, 1 ATR 87%.

## The weekly range from the daily chart

At each week's open: the nearest live FVG or suspension block above (premium draw) and below (discount draw). Controls are 5 weeks with similar prior 1 and 4 weeks.

| Look back | Side | Weeks | Median distance | Reached by the week (gap / control) | Week's extreme stops inside, when reached |
|---|---|---|---|---|---|
| 20 | above | 1,242 | 0.61 ATR | 67.6% / 67.8% | 28.0% / 27.5% |
| 20 | below | 2,037 | 0.55 ATR | 61.0% / 62.8% | 27.1% / 28.3% |
| 60 | above | 1,583 | 0.63 ATR | 65.5% / 65.6% | 30.4% / 30.1% |
| 60 | below | 2,540 | 0.61 ATR | 58.9% / 60.2% | 27.9% / 29.2% |

The nearest gaps frame the week as often as any level as far away. The card's by-Friday odds come from distance.

## ICT's body rule, octants, inversion

- **Touch day's close and the next 10 days (survived, FVG):**

  | Touch day closed | Gap | No gap |
  |---|---|---|
  | Back outside | 43.9% | 42.9% |
  | Near half (CE held) | 34.2% | 30.6% |
  | Past CE | 16.1% | 21.0% |

  The rule describes depth, at any level.
- **Octants:** the touch day's wick stopped across the zone like the control; within 1/16 of CE 12.5% vs 11.3%.
- **Inverted FVGs** (after a close beyond):
  - retested within 20 days 88.5% vs 89.6%;
  - touch day held 43.5% vs 44.4%;
  - 10 days 25.8% vs 24.4%.

## Settlement as close (SET) vs last trade, 2018–26

- The daily close is the settlement: Barchart's close matches the 15:59–16:00 ET minute (the settlement window, with a volume spike).
- With SET off, the close is the 16:59 last trade. Example, NQZ26 on 20 Oct 2026: settlement 29,688.00 (a down candle) vs last trade 29,893.75 (an up candle).

| | NQ | ES | RTY | YM |
|---|---|---|---|---|
| Last − settlement, median \|Δ\| | 0.040 ATR | 0.042 | 0.038 | 0.042 |
| Days > 0.1 ATR | 18% | 18% | 12% | 16% |
| Candle colour flips | 4.7% | 5.1% | 3.2% | 4.5% |
| Volume imbalances, SET / last | 591 / 527 | 622 / 559 | 612 / 584 | 677 / 561 |
| Suspension blocks, SET / last | 152 / 129 | 166 / 138 | 145 / 132 | 204 / 130 |
| Imbalances present under both | 49% | 50% | 44% | 45% |

- Wick FVGs are identical under both settings.
- Neither setting's imbalances or suspension blocks beat the same candles without one:
  - imbalances, 10 days after the touch: SET −1.5 (t −1.3), last −0.9 (t −0.9);
  - suspension blocks: SET −2.9 (t −1.1), last −1.7 (t −0.6).
- Imbalances that exist under only one setting are tiny (median 0.02 ATR) and a little weaker: 16.1% vs 18.4%, t −1.9.

## Front month vs continuous

| | NQ | ES | RTY | YM |
|---|---|---|---|---|
| Roll jump \|next − front\|, median, 2022–26 | 0.58 ATR | 0.69 | 0.44 | 0.63 |
| Same, 2010–19 | 0.12 | 0.27 | 0.23 | 0.05 |
| Contract's own chart, 60 days before it was front: gaps vs the front's | 1,134 vs 964 (+18%) | 945 vs 899 (+5%) | 1,643 vs 851 (+93%) | 563 vs 504 (+12%) |
| Of the front's gaps, also on the contract's chart | 99% | 99% | 100% | 100% |

- **Unadjusted 1!:** gaps from before the last roll sit at the old contract's prices, by more than a typical gap is wide (since 2022).
- **The contract's own chart** shows every front-month gap, plus extra gaps from its deferred months. Deferred volume ran 0.1% of the front's on NQ, 20–40 days before the roll (per-contract volume, H10–Z24).
- **Back-adjusted 1!** has neither problem.

## Card odds

- **Reach** = logistic(a + b·logit(2Φ(−d/(κ√h)))), d = distance in ATR(14), h = trading days. Fit 2010–26 on the nearest live gap:
  - above: κ 0.625, a 0.2108, b 0.9973;
  - below: κ 1.05, a −1.0257, b 1.0638.
- **Walk-forward 2014–26, 5 days:**
  - above 6→5, 21→22, 41→36, 60→57, 81→79, 95→94%;
  - below 6→10, 21→22, 40→41, 60→61, 80→82, 95→95%.
  - Years 0.85–1.20× (2025 above 0.90).
- **Holds** = logistic(a + b·ln w), w = width in ATR:

  | Kind | Touch day (a, b) | 10 days (a, b) |
  |---|---|---|
  | FVG | 1.9063, 1.4383 | −0.3164, 0.4153 |
  | Suspension block | 1.8216, 1.5525 | −0.0963, 0.6071 |
  | Volume imbalance | 1.1063, 1.0892 | −0.8334, 0.2189 |

- **Locked 2025–26 (fit on 2010–24), FVG touch day:** 11→14, 37→41, 59→57, 79→82%.

Historical frequencies, not guarantees. Not financial advice.
