W, N, O, H = open('/home/claude/sz/cells_pine.txt').read().split('\n')
P = r'''//@version=6
// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © Unclehk2000
// Suzumebachi · structure break odds. Market structure at a chosen sensitivity (swing strength 2, 3, 5 or 8), every break of
// structure labelled MSS (it turns the trend) or BOS (it continues it) with its scenario: what liquidity the leg raided (PWH/PWL,
// PDH/PDL, Asia, London, the day's extreme, the prior swing, or none), a fair value gap in the break leg, the stop in ATR, where it
// broke in the prior day's range and against the midnight open. Each scenario carries its tested 1R race: does price reach 1R in
// the break's direction before it returns to the leg extreme? Under any driftless price that is 50%, whatever the volatility.
// Trained on ES + YM 5- and 15-minute structure 2018–24; checked on 2025 – Oct 2026 and on NQ and RTY, never trained on.
// 739,504 breaks. Every scenario that passed the suite's rule is a break that fails more often than not: a sell BOS chasing the
// top quarter of the prior day's range returns to its extreme first 54–56% (56% overnight), a weak MSS (no raid; no FVG or a tight
// stop) 51–52%. The textbook MSS (raid + FVG + normal stop) is a coin flip: 50.5%. Not affiliated with or endorsed by ICT.
indicator("Suzumebachi · Structure Break Odds", "Suzumebachi", overlay = true, max_lines_count = 300, max_labels_count = 300, max_bars_back = 2000)

TZ = "America/New_York"

// ═══════════════════════════════════════════════════════════════ Inputs
gV = "View"
themeI  = input.string("Auto", "Card theme", options = ["Auto", "Dark", "Light"], group = gV, display = display.none)
lblSzI  = input.string("Small", "Text size", options = ["Tiny", "Small", "Normal"], group = gV, display = display.none)
showCrd = input.bool(true, "Card", group = gV, inline = "cd", display = display.none)
crdPos  = input.string("Top right", "", options = ["Top left", "Top center", "Top right", "Middle left", "Middle right", "Bottom left", "Bottom center", "Bottom right"], group = gV, inline = "cd", display = display.none)
layI    = input.string("Desktop", "Layout", options = ["Desktop", "Mobile"], group = gV, tooltip = "Desktop: the last break, its scenario and the setting's scenario table. Mobile: the last break and its odds.", display = display.none)

gS = "Structure"
kI    = input.string("3 · short-term", "Sensitivity (swing strength)", options = ["2 · internal", "3 · short-term", "5 · intermediate", "8 · swing"], group = gS, tooltip = "A swing high needs k candles each side lower (a pivot of strength k), confirmed k candles later. Lower k: more, smaller swings. Tested on 5-minute (2, 3, 5, 8) and 15-minute (2, 3) charts; at other settings the scenarios are drawn without odds.", display = display.none)
showAll = input.string("All breaks", "Breaks to draw", options = ["All breaks", "Only scenarios that passed"], group = gS, display = display.none)
showSw  = input.bool(false, "Mark swing highs / lows", group = gS, display = display.none)
showExt = input.bool(true, "Extreme and 1R lines on breaks that passed", group = gS, tooltip = "From the break: the leg extreme (where the break's stop sits, and what a failed break returns to) and 1R in the break's direction, until one is touched.", display = display.none)
maxBr   = input.int(40, "Breaks kept", minval = 5, maxval = 120, group = gS, display = display.none)
cBear = input.color(#ef5350, "Sell break", group = gS, inline = "c", display = display.none)
cBull = input.color(#26a69a, "Buy break", group = gS, inline = "c", display = display.none)
cFail = input.color(#ffb300, "Fails more often", group = gS, inline = "c", display = display.none)

gA = "Alerts · create one with \"Any alert() function call\""
alP = input.bool(true, "A break in a scenario that passed", group = gA, display = display.none)

// ═══════════════════════════════════════════════════════════════ Helpers
bgLum  = 0.299 * color.r(chart.bg_color) + 0.587 * color.g(chart.bg_color) + 0.114 * color.b(chart.bg_color)
isDark = themeI == "Dark" or (themeI == "Auto" and bgLum < 128)
cTxt   = isDark ? #d1d4dc : #131722
cBody  = isDark ? #161a23 : #f4f6f9
cSub   = isDark ? #8a93a6 : #5d6476
cHdr   = #f9a825
tSz = lblSzI == "Tiny" ? size.tiny : lblSzI == "Normal" ? size.normal : size.small
px(float v) => str.tostring(v, format.mintick)
pc(float v) => na(v) ? "—" : str.tostring(v, "0.0") + "%"
posOf(string p) =>
    switch p
        "Top left"      => position.top_left
        "Top center"    => position.top_center
        "Top right"     => position.top_right
        "Middle left"   => position.middle_left
        "Middle right"  => position.middle_right
        "Bottom left"   => position.bottom_left
        "Bottom center" => position.bottom_center
        => position.bottom_right
relOf(int t) => ((hour(t, TZ) * 60 + minute(t, TZ)) - 1080 + 1440) % 1440
hm(int t) => str.format("{0,number,00}:{1,number,00}", hour(t, TZ), minute(t, TZ))

// ═══════════════════════════════════════════════════════════════ Tested scenario table
// 17 cells per setting (5m k2, k3, k5, k8; 15m k2, k3). MSS: raid × FVG × tight stop (0–7). BOS: prior-day-range location
// (low quarter, middle, top quarter or beyond, for the break's side) × midnight open (before 00:00, ICT side, wrong side) (8–16).
// win = the 1R race for the break's direction, 2018–26, ES + YM + NQ + RTY pooled; ok = passed the suite's rule
// (p < 0.05 clustered by day, the same sign in 2018–24 and 2025–26 and on each market); h = 2025–26 alone.
var array<float> WIN = array.from(__W__)
var array<int>   NN  = array.from(__N__)
var array<int>   OK  = array.from(__O__)
var array<float> HH  = array.from(__H__)
// the two setups that passed the suite's rule as groups, per setting (fade = back to the leg extreme before 1R, 2018–26, four markets)
// chasing sell BOS: a sell BOS closing in the top quarter of the prior day's range or above it, before 00:00 or below the midnight open
var array<float> CH  = array.from(54.4, 54.8, 55.0, 55.6, 55.6, 55.2)
var array<float> CHH = array.from(53.3, 54.9, 53.3, 55.2, 57.0, 54.7)
var array<int>   CHN = array.from(9413, 6705, 4136, 2333, 2277, 1448)
// weak MSS: no raid, and no FVG or a tight stop (passed on 5-minute k2, k3, k5 only; 49.4–49.9% at k8 and on 15 minutes)
var array<float> WK  = array.from(51.6, 52.2, 51.3)
var array<float> WKH = array.from(51.8, 53.1, 53.1)
var array<int>   WKN = array.from(42200, 24685, 10535)
cellName(int c) =>
    c == 0 ? "MSS · no raid · no FVG" : c == 1 ? "MSS · no raid · no FVG · tight stop" : c == 2 ? "MSS · no raid · FVG" : c == 3 ? "MSS · no raid · FVG · tight stop" : c == 4 ? "MSS · raid · no FVG" : c == 5 ? "MSS · raid · no FVG · tight stop" : c == 6 ? "MSS · raid · FVG (textbook)" : c == 7 ? "MSS · raid · FVG · tight stop" : "BOS · " + (c < 11 ? "PD low quarter" : c < 14 ? "PD middle" : "PD top quarter+") + " · " + ((c - 8) % 3 == 0 ? "before 00:00" : (c - 8) % 3 == 1 ? "ICT side of 00:00 open" : "wrong side of 00:00 open")
int kS = kI == "2 · internal" ? 2 : kI == "3 · short-term" ? 3 : kI == "5 · intermediate" ? 5 : 8
int tfM = timeframe.isintraday ? int(timeframe.in_seconds() / 60) : 0
int cfg = tfM == 5 ? (kS == 2 ? 0 : kS == 3 ? 1 : kS == 5 ? 2 : 3) : tfM == 15 and kS <= 3 ? (kS == 2 ? 4 : 5) : -1
// the second level: inside the passing groups, pooled 5-minute k2 / k3 / k5, all four markets 2018–26 (fade = back to the extreme first)
subFade(bool chase, bool weak, int d, int r) =>
    float f = na
    string t = ""
    if chase
        f := CH.get(cfg)
        t := "Sell BOS in the top quarter of the prior day's range or above it, before 00:00 or below the midnight open: back to the extreme first " + str.tostring(f, "0.0") + "% at this setting (n " + str.tostring(CHN.get(cfg)) + "; 2025–26 " + str.tostring(CHH.get(cfg), "0.0") + "%). 54.4–55.6% at all six settings; ES, YM, NQ and RTY 53.1–58.1% each. The buy side (a buy BOS in the low quarter or below) is 48.7–50.1%."
        if cfg <= 2 and r >= 120 and r < 660
            f := 55.9
            t := "Sell BOS chasing the prior day's top quarter, 20:00–05:00: back to the extreme first 55.9% (5m k2–k5 pooled, n 11,955; Asia 57.6%, London 55.6%; 2018–24 56.2%, 2025–26 54.8%; ES 56.7, YM 54.0, NQ 54.6, RTY 58.5). Other sell BOS overnight: 51.6%, so +4.5 ± 1.2 points beyond the overnight drift."
        else if cfg <= 2 and r >= 1050 and r < 1170
            f := 57.9
            t := "Sell BOS chasing the prior day's top quarter, NY lunch 11:30–13:30: back to the extreme first 57.9% (5m k2–k5 pooled, n 656; 2018–24 58.4%, 2025–26 55.7%)."
    else if weak
        f := WK.get(cfg)
        t := "Weak MSS (no raid; no FVG or a tight stop): back to the extreme first " + str.tostring(f, "0.0") + "% at this setting (n " + str.tostring(WKN.get(cfg)) + "; 2025–26 " + str.tostring(WKH.get(cfg), "0.0") + "%). Sell side 52.6%, buy side 50.9% (5m k2–k5 pooled). All MSS: sell 51.1%, buy 49.6%."
        if d == -1 and r >= 360 and r < 480
            f := 53.8
            t := "Weak sell MSS, 00:00–02:00: back to the extreme first 53.8% (5m k2–k5 pooled, n 3,841; 2018–24 53.2%, 2025–26 57.3%)."
        else if d == -1 and r >= 1170 and r < 1320
            f := 53.8
            t := "Weak sell MSS, NY PM 13:30–16:00: back to the extreme first 53.8% (5m k2–k5 pooled, n 4,124; 2018–24 54.2%, 2025–26 52.2%)."
        else if d == -1
            f := 52.6
            t := "Weak sell MSS: back to the extreme first 52.6% (5m k2–k5 pooled, n 38,424; 2018–24 52.6%, 2025–26 52.4%; every market 52.2–53.2%). All sell MSS: 51.1%."
        else
            f := 50.9
            t := "Weak buy MSS: back to the extreme first 50.9% (5m k2–k5 pooled, n 38,996; passes, but small). All buy MSS: 49.6%."
    [f, t]

// ═══════════════════════════════════════════════════════════════ Day, week, sessions (18:00 ET trading day)
int relM = relOf(time)
bool newD = ta.change(time_tradingday) != 0
int wkN = int(math.floor((time_tradingday / 86400000 + 3) / 7))
bool newW = ta.change(wkN) != 0
var float dHi = na
var float dLo = na
var float wHi = na
var float wLo = na
var float pdh = na
var float pdl = na
var float pwh = na
var float pwl = na
var float asH = na
var float asL = na
var float loH = na
var float loL = na
var float aHi = na
var float aLo = na
var float lHi = na
var float lLo = na
var float moO = na
if newW
    pwh := wHi
    pwl := wLo
    wHi := na
    wLo := na
if newD
    pdh := dHi
    pdl := dLo
    dHi := na
    dLo := na
    asH := na
    asL := na
    loH := na
    loL := na
    aHi := na
    aLo := na
    lHi := na
    lLo := na
    moO := na
// values before this candle (what the tests call "before the bar")
float dHb = dHi
float dLb = dLo
float wHb = wHi
float wLb = wLo
float aHb = relM >= 360 ? aHi : na
float aLb = relM >= 360 ? aLo : na
float lHb = relM >= 660 ? lHi : na
float lLb = relM >= 660 ? lLo : na
if relM >= 360 and na(moO)
    moO := open
float ASH = relM >= 360 ? asH : na
float ASL = relM >= 360 ? asL : na
float LOH = relM >= 660 ? loH : na
float LOL = relM >= 660 ? loL : na
float MO  = relM >= 360 ? moO : na
// update with this candle
dHi := math.max(nz(dHi, high), high)
dLo := math.min(nz(dLo, low), low)
wHi := math.max(nz(wHi, high), high)
wLo := math.min(nz(wLo, low), low)
if relM >= 120 and relM < 360
    asH := math.max(nz(asH, high), high)
    asL := math.min(nz(asL, low), low)
if relM >= 480 and relM < 660
    loH := math.max(nz(loH, high), high)
    loL := math.min(nz(loL, low), low)
if relM >= 360
    aHi := math.max(nz(aHi, high), high)
    aLo := math.min(nz(aLo, low), low)
if relM >= 660
    lHi := math.max(nz(lHi, high), high)
    lLo := math.min(nz(lLo, low), low)
float a5 = ta.sma(high - low, 14)[1]

// ═══════════════════════════════════════════════════════════════ Structure
type Brk
    line  ln
    label lb
    line  lx
    line  l1
    label tx
    label t1
    float ext
    float oneR
    int   d
    bool  live

var float shv = na
var int   shb = -1
var float slv = na
var int   slb = -1
var bool  bH = true
var bool  bL = true
var int   trd = 0
var array<float> HV = array.new<float>()
var array<int>   HB = array.new<int>()
var array<int>   HC = array.new<int>()
var array<float> LV = array.new<float>()
var array<int>   LB = array.new<int>()
var array<int>   LC = array.new<int>()
var array<Brk>   BR = array.new<Brk>()
// the last break, for the card
var int    lTime = na
var int    lDir = 0
var int    lCell = -1
var bool   lMss = false
var string lRaid = ""
var bool   lFvg = false
var float  lRA = na
var float  lPdx = na
var int    lMos = 0
var float  lExt = na
var float  lOneR = na
var float  lWin = na
var bool   lOk = false
var float  lSub = na
var string lSubT = ""
var int    lRes = 0      // 0 live, 1 extreme first, 2 1R first
var bool   lTested = false

int bi = bar_index
// confirm a pivot of strength k at bar bi − k
if bi >= 2 * kS
    bool hi = true
    bool lo = true
    for q = 1 to kS
        if high[kS + q] >= high[kS]
            hi := false
        if low[kS + q] <= low[kS]
            lo := false
        if high[kS - q] > high[kS]
            hi := false
        if low[kS - q] < low[kS]
            lo := false
    if hi
        shv := high[kS]
        shb := bi - kS
        bH := false
        HV.push(shv), HB.push(shb), HC.push(bi)
        if HV.size() > 60
            HV.shift(), HB.shift(), HC.shift()
        if showSw
            label.new(shb, shv, "", style = label.style_triangledown, color = color.new(cBear, 40), size = size.tiny)
    if lo
        slv := low[kS]
        slb := bi - kS
        bL := false
        LV.push(slv), LB.push(slb), LC.push(bi)
        if LV.size() > 60
            LV.shift(), LB.shift(), LC.shift()
        if showSw
            label.new(slb, slv, "", style = label.style_triangleup, yloc = yloc.price, color = color.new(cBull, 40), size = size.tiny)

// what a break's leg raided, its FVG and its cell; d = -1 sell break (of a swing low), +1 buy break
evalBreak(int d, int sb, float sv) =>
    // the leg extreme between the broken swing and this candle (the earliest if tied)
    int n0 = math.min(bi - sb, 1500)
    int xo = n0
    for q = n0 to 0
        if (d == -1 and high[q] > high[xo]) or (d == 1 and low[q] < low[xo])
            xo := q
    int xb = bi - xo
    float x = d == -1 ? high[xo] : low[xo]
    // the prior swing on the extreme's side, confirmed before the extreme
    float pv = na
    if d == -1 and HV.size() > 0
        for z = HV.size() - 1 to 0
            if HC.get(z) <= xb and HB.get(z) < xb
                pv := HV.get(z)
                break
    else if d == 1 and LV.size() > 0
        for z = LV.size() - 1 to 0
            if LC.get(z) <= xb and LB.get(z) < xb
                pv := LV.get(z)
                break
    // fresh raids: the level traded through for the first time inside this leg (not before the leg began)
    int so  = bi - sb
    int so1 = so > 0 and time_tradingday[so - 1] == time_tradingday[so] ? so - 1 : so
    bool fPW = d == -1 ? (x > pwh[xo] and not (wHb[so1] > pwh[xo])) : (x < pwl[xo] and not (wLb[so1] < pwl[xo]))
    bool fPD = d == -1 ? (x > pdh[xo] and not (dHb[so1] > pdh[xo])) : (x < pdl[xo] and not (dLb[so1] < pdl[xo]))
    bool fAS = d == -1 ? (x > ASH[xo] and not (aHb[so1] > ASH[xo])) : (x < ASL[xo] and not (aLb[so1] < ASL[xo]))
    bool fLO = d == -1 ? (x > LOH[xo] and not (lHb[so1] > LOH[xo])) : (x < LOL[xo] and not (lLb[so1] < LOL[xo]))
    bool fDay = d == -1 ? x > dHb[xo] : x < dLb[xo]
    bool fSw = d == -1 ? x > pv : x < pv
    string raid = fPW ? (d == -1 ? "PWH" : "PWL") : fPD ? (d == -1 ? "PDH" : "PDL") : fAS ? (d == -1 ? "Asia H" : "Asia L") : fLO ? (d == -1 ? "London H" : "London L") : fDay ? (d == -1 ? "day high" : "day low") : fSw ? "prior swing" : ""
    // an FVG in the break leg: a sell break needs high[j] < low[j−2] somewhere from the extreme on
    bool fvg = false
    if xo >= 2
        for o = math.min(xo - 2, 1500) to 0
            if (d == -1 and high[o] < low[o + 2]) or (d == 1 and low[o] > high[o + 2])
                fvg := true
                break
    float risk = (x - close) * (-d)
    float rA = a5 > 0 ? risk / a5 : na
    float pdr = pdh > pdl ? (close - pdl) / (pdh - pdl) : na
    float pdx = na(pdr) ? na : d == -1 ? pdr : 1 - pdr
    int loc = na(pdx) ? 1 : pdx >= 0.75 ? 2 : pdx < 0.25 ? 0 : 1
    int mos = na(MO) ? 0 : (-d) * (close - MO) > 0 ? 1 : 2
    [x, xb, raid, fvg, risk, rA, pdx, loc, mos]

newBreak(int d, int sb, float sv, bool mss) =>
    [x, xb, raid, fvg, risk, rA, pdx, loc, mos] = evalBreak(d, sb, sv)
    bool tight = rA < 1.5
    int cell = mss ? (raid != "" ? 4 : 0) + (fvg ? 2 : 0) + (tight ? 1 : 0) : 8 + loc * 3 + mos
    bool tested = cfg >= 0 and risk > 0 and rA >= 0.5 and rA <= 12
    int ix = cfg * 17 + cell
    float win = tested ? WIN.get(ix) : na
    bool chase = cfg >= 0 and not mss and d == -1 and (cell == 14 or cell == 16)
    bool weak = mss and raid == "" and (not fvg or tight) and cfg >= 0 and cfg <= 2
    bool ok = tested and (chase or weak)
    [f, t] = subFade(chase, weak, d, relM)
    string tt = not tested ? "" : ok ? t : not mss and d == 1 and (cell == 14 or cell == 16) ? "Buy BOS in the low quarter of the prior day's range or below: 48.7–50.1% back to the extreme first. Only the sell side fails." : ""
    [x, xb, raid, fvg, risk, rA, pdx, mos, cell, tested, win, ok, (ok ? f : na), tt]

string alMsg = ""
// sell break first, as in the tests
if not bL and slb >= 0 and close < slv
    bL := true
    bool mss = trd == 1
    [x, xb, raid, fvg, risk, rA, pdx, mos, cell, tested, win, ok, sub, subT] = newBreak(-1, slb, slv, mss)
    trd := -1
    lTime := time, lDir := -1, lCell := cell, lMss := mss, lRaid := raid, lFvg := fvg, lRA := rA, lPdx := pdx, lMos := mos
    lExt := x, lOneR := close - risk, lWin := win, lOk := ok, lSub := sub, lSubT := subT, lRes := 0, lTested := tested
    if showAll == "All breaks" or ok
        color cc = ok ? cFail : cBear
        float fade = ok ? sub : na
        string tx = (mss ? "MSS" : "BOS") + " ▼" + (ok ? " · fails " + str.tostring(fade, "0") + "%" : "")
        string tip = cellName(cell) + (raid != "" ? " · raided " + raid : "") + "\nStop " + (na(rA) ? "—" : str.tostring(rA, "0.0")) + " ATR" + (tested ? "\nThis cell, 1R before the extreme: " + pc(win) + (ok ? "\nPassed: back to the extreme first " + pc(fade) : " · not a passing setup (≈ a coin flip)") : "\nNot tested at this setting.") + (subT != "" ? "\n" + subT : "")
        Brk b = Brk.new(line.new(slb, slv, bi, slv, color = cc, style = mss ? line.style_solid : line.style_dashed, width = 1), label.new(int(math.round((slb + bi) / 2)), slv, tx, style = label.style_label_up, color = #00000000, textcolor = cc, size = tSz, tooltip = tip), na, na, na, na, x, close - risk, -1, ok and showExt)
        if ok and showExt
            b.lx := line.new(bi, x, bi + 1, x, color = cFail, style = line.style_dotted, width = 2)
            b.l1 := line.new(bi, close - risk, bi + 1, close - risk, color = color.new(cBear, 30), style = line.style_dotted)
            b.tx := label.new(bi + 1, x, "extreme · " + str.tostring(fade, "0") + "% first", style = label.style_label_left, color = #00000000, textcolor = cFail, size = size.tiny)
            b.t1 := label.new(bi + 1, close - risk, "1R · " + str.tostring(100 - fade, "0") + "%", style = label.style_label_left, color = #00000000, textcolor = cBear, size = size.tiny)
        BR.push(b)
    if ok
        alMsg += (mss ? "MSS" : "BOS") + " ▼ " + cellName(cell) + ": back to the extreme " + px(x) + " first " + str.tostring(sub, "0.0") + "%. "
if not bH and shb >= 0 and close > shv
    bH := true
    bool mss = trd == -1
    [x, xb, raid, fvg, risk, rA, pdx, mos, cell, tested, win, ok, sub, subT] = newBreak(1, shb, shv, mss)
    trd := 1
    lTime := time, lDir := 1, lCell := cell, lMss := mss, lRaid := raid, lFvg := fvg, lRA := rA, lPdx := pdx, lMos := mos
    lExt := x, lOneR := close + risk, lWin := win, lOk := ok, lSub := sub, lSubT := subT, lRes := 0, lTested := tested
    if showAll == "All breaks" or ok
        color cc = ok ? cFail : cBull
        float fade = ok ? sub : na
        string tx = (mss ? "MSS" : "BOS") + " ▲" + (ok ? " · fails " + str.tostring(fade, "0") + "%" : "")
        string tip = cellName(cell) + (raid != "" ? " · raided " + raid : "") + "\nStop " + (na(rA) ? "—" : str.tostring(rA, "0.0")) + " ATR" + (tested ? "\nThis cell, 1R before the extreme: " + pc(win) + (ok ? "\nPassed: back to the extreme first " + pc(fade) : " · not a passing setup (≈ a coin flip)") : "\nNot tested at this setting.") + (subT != "" ? "\n" + subT : "")
        Brk b = Brk.new(line.new(shb, shv, bi, shv, color = cc, style = mss ? line.style_solid : line.style_dashed, width = 1), label.new(int(math.round((shb + bi) / 2)), shv, tx, style = label.style_label_down, color = #00000000, textcolor = cc, size = tSz, tooltip = tip), na, na, na, na, x, close + risk, 1, ok and showExt)
        if ok and showExt
            b.lx := line.new(bi, x, bi + 1, x, color = cFail, style = line.style_dotted, width = 2)
            b.l1 := line.new(bi, close + risk, bi + 1, close + risk, color = color.new(cBull, 30), style = line.style_dotted)
            b.tx := label.new(bi + 1, x, "extreme · " + str.tostring(fade, "0") + "% first", style = label.style_label_left, color = #00000000, textcolor = cFail, size = size.tiny)
            b.t1 := label.new(bi + 1, close + risk, "1R · " + str.tostring(100 - fade, "0") + "%", style = label.style_label_left, color = #00000000, textcolor = cBull, size = size.tiny)
        BR.push(b)
    if ok
        alMsg += (mss ? "MSS" : "BOS") + " ▲ " + cellName(cell) + ": back to the extreme " + px(x) + " first " + str.tostring(sub, "0.0") + "%. "
if alP and alMsg != "" and barstate.isconfirmed
    alert("Suzumebachi · " + syminfo.ticker + " · " + alMsg, alert.freq_once_per_bar_close)

// extend live extreme / 1R lines until one is touched (on the candles after the break)
if BR.size() > 0
    for b in BR
        if b.live and not na(b.lx) and b.lx.get_x1() < bi
            bool hx = b.d == -1 ? high >= b.ext : low <= b.ext
            bool h1 = b.d == -1 ? low <= b.oneR : high >= b.oneR
            b.lx.set_x2(bi)
            b.l1.set_x2(bi)
            b.tx.set_x(bi)
            b.t1.set_x(bi)
            if hx or h1
                b.live := false
                b.tx.set_text(b.tx.get_text() + (hx and not h1 ? " ✓" : ""))
                b.t1.set_text(b.t1.get_text() + (h1 and not hx ? " ✓" : ""))
while BR.size() > maxBr
    Brk o = BR.shift()
    o.ln.delete(), o.lb.delete(), o.lx.delete(), o.l1.delete(), o.tx.delete(), o.t1.delete()
// the last break's state for the card
if not na(lTime) and lRes == 0 and time > lTime
    bool hx = lDir == -1 ? high >= lExt : low <= lExt
    bool h1 = lDir == -1 ? low <= lOneR : high >= lOneR
    lRes := hx and not h1 ? 1 : h1 and not hx ? 2 : hx and h1 ? 3 : 0

// ═══════════════════════════════════════════════════════════════ Card (last bar)
var table TC = na
tipT = "Breaks of structure on ES + YM 5- and 15-minute charts 2018–24 (trained), checked on 2025 – Oct 2026 and on NQ and RTY (never trained on): 739,504 breaks at six settings. The 1R race: from the break candle's close, does price reach 1R in the break's direction (1R = the distance to the leg extreme) before it returns to the extreme? Under any driftless price it is 50%, whatever the volatility.\nOf 641 single-context tests, 165 were significant on ES + YM 2018–24 and 8 held in 2025–26 (about 4 by chance). Of the 101 scenario cells with data, 17 passed the suite's rule (p < 0.05 clustered by day, the same sign in 2018–24 and 2025–26 and on ES, YM, NQ and RTY); all 17 fail more often than not. No cell passed on the winning side: the textbook MSS (raid + FVG + normal stop) is 50.5% (n 29,565 at k3)."
cRow(int r, string k, string v, color vc, string w, string tip) =>
    TC.cell(0, r, k, text_color = cSub, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(1, r, v, text_color = vc, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(2, r, w, text_color = cSub, text_size = tSz, text_halign = text.align_right, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
if barstate.islast and showCrd
    if na(TC)
        TC := table.new(posOf(crdPos), 3, 14, border_width = 0, frame_width = 1, frame_color = cHdr, force_overlay = true)
    TC.clear(0, 0, 2, 13)
    bool mob = layI == "Mobile"
    TC.cell(0, 0, "SUZUMEBACHI", text_color = #131722, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
    TC.cell(1, 0, mob ? "" : "STRUCTURE BREAK ODDS", text_color = #131722, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
    TC.cell(2, 0, (tfM > 0 ? str.tostring(tfM) + "m" : timeframe.period) + " · k" + str.tostring(kS), text_color = #131722, bgcolor = cHdr, text_size = tSz, text_halign = text.align_right, text_font_family = font.family_monospace)
    int r = 1
    if na(lTime)
        cRow(r, "last break", "none yet", cTxt, "", tipT)
    else
        float fade = lOk ? lSub : na
        color dc = lOk ? cFail : lDir == -1 ? cBear : cBull
        cRow(r, "last break", (lMss ? "MSS" : "BOS") + (lDir == -1 ? " ▼ " : " ▲ ") + hm(lTime), dc, lRes == 0 ? "live" : lRes == 1 ? "extreme ✓" : lRes == 2 ? "1R ✓" : "both", tipT)
        r += 1
        cRow(r, "scenario", cellName(lCell), cTxt, "", lSubT != "" ? lSubT : tipT)
        r += 1
        if lTested
            cRow(r, lOk ? "fails" : "odds", lOk ? "extreme first " + pc(fade) : "1R first " + pc(lWin), dc, lOk ? "1R " + pc(100 - fade) : "≈ coin flip", lSubT != "" ? lSubT : tipT)
        else
            cRow(r, "odds", "untested at " + (tfM > 0 ? str.tostring(tfM) + "m" : timeframe.period) + " k" + str.tostring(kS), cSub, "5m k2–8 · 15m k2–3", tipT)
        r += 1
        cRow(r, "levels", "extreme " + px(lExt), cTxt, "1R " + px(lOneR), "The leg extreme (where the break's stop sits, and what a failed break returns to) and 1R in the break's direction.")
        r += 1
        if not mob
            cRow(r, "leg", "raid: " + (lRaid != "" ? lRaid : "none") + " · " + (lFvg ? "FVG" : "no FVG"), cTxt, "stop " + (na(lRA) ? "—" : str.tostring(lRA, "0.0")) + " ATR", "Raid: the first trade through PWH/PWL, PDH/PDL, the Asia or London high/low inside this leg, a new day extreme, or the prior swing. FVG: a fair value gap in the break leg. Stop: the distance to the extreme in 14-candle average ranges; under 1.5 is tight.")
            r += 1
            cRow(r, "location", na(lPdx) ? "—" : "prior day " + str.tostring(math.round(lPdx * 100)) + "% to its side", cTxt, lMos == 0 ? "before 00:00" : lMos == 1 ? "ICT side of 00:00" : "wrong side of 00:00", "Where the break candle closed in the prior day's range, measured toward the break's own extreme side (a sell break at PDH = 100%), and against the midnight open.")
            r += 1
    if not mob and cfg >= 0
        cRow(r, "PASSED", "setups at this setting", cHdr, "extreme first", tipT)
        r += 1
        cRow(r, "", "sell BOS chasing PD top ¼", cFail, pc(CH.get(cfg)) + " · 25–26 " + pc(CHH.get(cfg)), "A sell BOS closing in the top quarter of the prior day's range or above it, before 00:00 or below the midnight open. n " + str.tostring(CHN.get(cfg)) + " at this setting, 2018–26, four markets. The buy side is 48.7–50.1%.")
        r += 1
        if cfg <= 2
            cRow(r, "", "  … 20:00–05:00", cFail, "55.9%", "5m k2–k5 pooled, n 11,955; Asia 57.6%, London 55.6%; 2018–24 56.2%, 2025–26 54.8%. +4.5 ± 1.2 points beyond other sell BOS overnight (51.6%).")
            r += 1
            cRow(r, "", "weak MSS (no raid; no FVG / tight)", cFail, pc(WK.get(cfg)) + " · 25–26 " + pc(WKH.get(cfg)), "n " + str.tostring(WKN.get(cfg)) + " at this setting. Sell side 52.6%, buy side 50.9%; weak sell MSS 00:00–02:00 and NY PM 53.8% (5m k2–k5 pooled). Not at k8 or on 15 minutes (49.4–49.9%).")
            r += 1
        cRow(r, "textbook", "MSS · raid · FVG · normal stop", cSub, "1R " + pc(WIN.get(cfg * 17 + 6)), "The ICT model's strong MSS (a liquidity raid, displacement with an FVG, a normal stop) is a coin flip at 1R: it neither fails nor wins more often than chance.")
'''
P = P.replace('__W__', W).replace('__N__', N).replace('__O__', O).replace('__H__', H)
open('/home/claude/sz/Suzumebachi.pine', 'w').write(P)
print('ok', P.count('\n'))
