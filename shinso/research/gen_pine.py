cum5 = open('/home/claude/sk/cum5.txt').read()
evd, evr = open('/home/claude/sk/ev.txt').read().split('\n')
trees = open('/home/claude/sn/trees.pine').read()
P = r'''//@version=6
// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © Unclehk2000
// Shinsō · draw on liquidity, with machine-learned odds. ICT's liquidity pools: the previous day's, week's and month's highs and
// lows (PDH / PDL, PWH / PWL, PMH / PML) and the Asia (20:00–00:00 ET) and London (02:00–05:00) ranges. Each live pool carries
// the chance it trades before 16:59 today, and the nearest buy-side and sell-side pools carry the odds of which trades first.
// Both come from gradient-boosted trees run inside Pine, trained on NQ + ES + RTY 1-minute 2018–24 and scored once on
// 2025 – Oct 2026. Pools (598,185 samples): Brier 0.088 against 0.167 for a flat rate and 0.090 for a Brownian distance-and-
// time model (log-loss gain 0.004, 95% CI 0.002–0.007). Race (66,417): Brier 0.166 against 0.168 for price's position between
// the two pools (gain 0.007, CI 0.002–0.011). The draw-on-liquidity readings (the other side already taken, pools stacked
// together, pools in the direction of the day's move) moved the odds by 1 point or less beyond distance and time.
// Concepts: liquidity pools, buy-side / sell-side liquidity, draw on liquidity and the killzone ranges are ICT's (Michael J.
// Huddleston). Not affiliated with or endorsed by ICT.
indicator("Shinsō · Draw on Liquidity Odds", "Shinsō", overlay = true, max_lines_count = 100, max_labels_count = 100, behind_chart = false)

TZ = "America/New_York"

// ═══════════════════════════════════════════════════════════════ Inputs
gV = "View"
themeI  = input.string("Auto", "Card theme", options = ["Auto", "Dark", "Light"], group = gV, display = display.none)
lblSzI  = input.string("Small", "Text size", options = ["Tiny", "Small", "Normal"], group = gV, display = display.none)
showCrd = input.bool(true, "Card", group = gV, inline = "cd", display = display.none)
crdPos  = input.string("Top right", "", options = ["Top left", "Top center", "Top right", "Middle left", "Middle right", "Bottom left", "Bottom center", "Bottom right"], group = gV, inline = "cd", display = display.none)
layI    = input.string("Desktop", "Layout", options = ["Desktop", "Mobile"], group = gV, tooltip = "Desktop: every pool, the race and the tested rows. Mobile: the race and the two most likely pools.", display = display.none)

gP = "Pools"
onD = input.bool(true, "PDH / PDL", group = gP, inline = "p1", display = display.none)
onW = input.bool(true, "PWH / PWL", group = gP, inline = "p1", display = display.none)
onM = input.bool(true, "PMH / PML", group = gP, inline = "p1", display = display.none)
onA = input.bool(true, "Asia 20:00–00:00", group = gP, inline = "p2", display = display.none)
onL = input.bool(true, "London 02:00–05:00", group = gP, inline = "p2", tooltip = "The session ranges go live once the session ends (00:00 and 05:00 ET). All pools reset at 18:00.", display = display.none)
shTk = input.bool(true, "Keep taken pools (faded)", group = gP, display = display.none)
extN = input.int(12, "Extend right (bars)", minval = 0, maxval = 100, group = gP, display = display.none)
cBSL = input.color(#ef5350, "Buy-side", group = gP, inline = "c", display = display.none)
cSSL = input.color(#26a69a, "Sell-side", group = gP, inline = "c", display = display.none)

gA = "Alerts · create one with \"Any alert() function call\""
alT = input.bool(true, "Pool taken", group = gA, display = display.none)

// ═══════════════════════════════════════════════════════════════ Helpers
bgLum  = 0.299 * color.r(chart.bg_color) + 0.587 * color.g(chart.bg_color) + 0.114 * color.b(chart.bg_color)
isDark = themeI == "Dark" or (themeI == "Auto" and bgLum < 128)
cTxt   = isDark ? #d1d4dc : #131722
cBody  = isDark ? #161a23 : #f4f6f9
cSub   = isDark ? #8a93a6 : #5d6476
cHdr   = #ad1457
tSz = lblSzI == "Tiny" ? size.tiny : lblSzI == "Normal" ? size.normal : size.small
px(float v) => str.tostring(v, format.mintick)
pc0(float p) => na(p) ? "—" : str.tostring(math.round(100 * p)) + "%"
clamp(float v, float a, float b) => math.max(a, math.min(b, v))
gauge(float f, int n) =>
    int k = na(f) ? 0 : int(math.round(clamp(f, 0, 1) * n))
    str.repeat("█", k) + str.repeat("░", n - k)
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
nCdf(float x) =>
    float z = math.abs(x)
    float t = 1.0 / (1.0 + 0.2316419 * z)
    float p = 1.0 - 0.3989422804 * math.exp(-0.5 * z * z) * t * (0.319381530 + t * (-0.356563782 + t * (1.781477937 + t * (-1.821255978 + t * 1.330274429))))
    x >= 0 ? p : 1.0 - p
lgt(float p) =>
    float q = clamp(p, 0.000001, 0.999999)
    math.log(q / (1.0 - q))
hm(int r) =>
    int t = (r + 1080) % 1440
    str.tostring(int(t / 60), "00") + ":" + str.tostring(t % 60, "00")

// ═══════════════════════════════════════════════════════════════ Model constants
var array<float> CUM5 = array.from(__CUM5__)
vRem(float r) =>
    float rr = clamp(r, 0, 1380)
    int   b  = math.min(int(rr / 5), 275)
    float f  = (rr - 5 * b) / 5.0
    CUM5.get(b) + f * (CUM5.get(b + 1) - CUM5.get(b))
var array<int> EVD = __EVD__
var array<int> EVR = __EVR__
__TREES__

// ═══════════════════════════════════════════════════════════════ Data
[atrD, pdh, pdl] = request.security(syminfo.tickerid, "D", [ta.atr(14)[1], high[1], low[1]], lookahead = barmerge.lookahead_on)
[pwh, pwl] = request.security(syminfo.tickerid, "W", [high[1], low[1]], lookahead = barmerge.lookahead_on)
[pmh, pml] = request.security(syminfo.tickerid, "M", [high[1], low[1]], lookahead = barmerge.lookahead_on)
bool act   = timeframe.isintraday and timeframe.in_seconds() <= 3600
int  tfMin = int(timeframe.in_seconds() / 60)
int  relM  = ((hour(time, TZ) * 60 + minute(time, TZ)) - 1080 + 1440) % 1440
bool newD  = timeframe.change("D")
int  tdD   = time_tradingday
int  ymd   = year(tdD, "UTC") * 10000 + month(tdD, "UTC") * 100 + dayofmonth(tdD, "UTC")
int  dow0  = (dayofweek(tdD, "UTC") + 5) % 7

// pools: 0 PDH 1 PDL 2 PWH 3 PWL 4 PMH 5 PML 6 Asia H 7 Asia L 8 London H 9 London L · type 0 day 1 week 2 month 3 Asia 4 London
var array<string> PN  = array.from("PDH", "PDL", "PWH", "PWL", "PMH", "PML", "Asia H", "Asia L", "London H", "London L")
var array<float>  LV  = array.new<float>(10, na)
var array<int>    LIV = array.new<int>(10, na)     // time the pool went live today
var array<int>    TK  = array.new<int>(10, na)     // time it was taken
var float dO = na
var int   dT = na
var float aH = na
var float aL = na
var float lH = na
var float lL = na
string tkMsg = ""
sideOf(int j) => j % 2 == 0 ? 1 : -1
typOf(int j) => int(j / 2)
onOf(int j) => j < 2 ? onD : j < 4 ? onW : j < 6 ? onM : j < 8 ? onA : onL
if act
    if newD or na(dO)
        dO := open
        dT := time
        aH := na
        aL := na
        lH := na
        lL := na
        for j = 0 to 9
            LV.set(j, na)
            LIV.set(j, na)
            TK.set(j, na)
        LV.set(0, pdh)
        LV.set(1, pdl)
        LV.set(2, pwh)
        LV.set(3, pwl)
        LV.set(4, pmh)
        LV.set(5, pml)
        for j = 0 to 5
            LIV.set(j, time)
    if relM >= 120 and relM < 360
        aH := na(aH) ? high : math.max(aH, high)
        aL := na(aL) ? low : math.min(aL, low)
    if relM >= 480 and relM < 660
        lH := na(lH) ? high : math.max(lH, high)
        lL := na(lL) ? low : math.min(lL, low)
    if relM >= 360 and na(LIV.get(6)) and not na(aH)
        LV.set(6, aH)
        LV.set(7, aL)
        LIV.set(6, time)
        LIV.set(7, time)
    if relM >= 660 and na(LIV.get(8)) and not na(lH)
        LV.set(8, lH)
        LV.set(9, lL)
        LIV.set(8, time)
        LIV.set(9, time)
    for j = 0 to 9
        float lv = LV.get(j)
        if not na(LIV.get(j)) and na(TK.get(j)) and not na(lv)
            if (sideOf(j) == 1 and high >= lv) or (sideOf(j) == -1 and low <= lv)
                TK.set(j, time)
                if onOf(j)
                    tkMsg += PN.get(j) + " " + px(lv) + " taken. "
if alT and tkMsg != "" and barstate.isconfirmed
    alert("Shinsō · " + syminfo.ticker + " · " + tkMsg, alert.freq_once_per_bar_close)

// ═══════════════════════════════════════════════════════════════ Odds (last bar)
evAhead(int rNow) =>
    bool out = false
    int  k   = EVD.binary_search_leftmost(ymd)
    while k < EVD.size() and k >= 0
        if EVD.get(k) != ymd
            break
        if EVR.get(k) > rNow - 1
            out := true
        k += 1
    out
liveU(int j) => not na(LIV.get(j)) and na(TK.get(j)) and not na(LV.get(j))
var array<line>  LN = array.new<line>()
var array<label> LB = array.new<label>()
var table TC = na
cRow(int r, string k, string g, color gc, string v, string w, string tip) =>
    TC.cell(0, r, k, text_color = cSub, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(1, r, g, text_color = gc, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(2, r, v, text_color = cTxt, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(3, r, w, text_color = cSub, text_size = tSz, text_halign = text.align_right, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
tipP = "The chance this pool trades before 16:59 today, from gradient-boosted trees (50, depth 3) on: a Brownian touch probability (distance in daily ATR(14) over the square root of the volatility still to come today, from the intraday profile), the pool's type and side, the time, how many pools sit between price and it, other pools stacked within 0.15 ATR, how many pools on each side are already taken, the day's move toward it, a CPI / NFP / FOMC release still ahead and the weekday.\nScored on 2025 – Oct 2026 (fit 2018–24): predicted → actual 2→2, 15→12, 25→23, 35→32, 45→42, 55→55, 65→65, 75→75, 85→85, 93→93%. Brier 0.088 vs 0.167 flat."
tipR = "Which trades first today, the nearest buy-side pool or the nearest sell-side pool, from gradient-boosted trees (40, depth 3) on price's position between them (the gambler's-ruin odds), the pools' types, how many are taken on each side, the day's move and the time. Scored on 2025 – Oct 2026: 6→5, 15→14, 25→24, 35→32, 45→41, 55→51, 65→61, 75→75, 85→85, 94→96%; Brier 0.166 vs 0.168 for the position alone. Position does nearly all the work: ICT's draw reasoning (the other side already taken, the day's direction) added a point or less."
if barstate.islast and act and atrD > 0
    while LN.size() > 0
        LN.pop().delete()
    while LB.size() > 0
        LB.pop().delete()
    int   rNow = relM + tfMin
    float v    = math.max(vRem(rNow), 1e-6)
    bool  ev   = evAhead(rNow)
    int   nTB  = 0
    int   nTS  = 0
    for j = 0 to 9
        if not na(TK.get(j))
            if sideOf(j) == 1
                nTB += 1
            else
                nTS += 1
    array<float> PP = array.new<float>(10, na)
    int jB = -1
    int jS = -1
    float dB = 1e18
    float dS = 1e18
    for j = 0 to 9
        if liveU(j) and onOf(j)
            int   sd = sideOf(j)
            float lv = LV.get(j)
            float d  = (lv - close) * sd / atrD
            if d > 0
                int nb = 0
                int cf = 0
                for i = 0 to 9
                    if i != j and liveU(i) and sideOf(i) == sd
                        float di = (LV.get(i) - close) * sd / atrD
                        if di > 0 and di < d
                            nb += 1
                        if math.abs(LV.get(i) - lv) / atrD < 0.15
                            cf += 1
                float lz = lgt(2.0 * nCdf(-0.95 * d / math.sqrt(v)))
                PP.set(j, poolTrees(lz, typOf(j), sd, rNow, nb, cf, sd == 1 ? nTS : nTB, sd == 1 ? nTB : nTS, sd * (close - dO) / atrD, ev ? 1.0 : 0.0, dow0))
                if sd == 1 and d < dB
                    dB := d
                    jB := j
                if sd == -1 and d < dS
                    dS := d
                    jS := j
    float pRace = na
    if jB >= 0 and jS >= 0
        pRace := raceTrees(lgt(dS / (dB + dS)), typOf(jB), typOf(jS), nTB, nTS, (close - dO) / atrD, rNow)
    int xr = time + extN * timeframe.in_seconds() * 1000
    // chart: every pool from the start of the trading day (the session ranges from when they went live)
    for j = 0 to 9
        float lv = LV.get(j)
        if onOf(j) and not na(lv) and not na(LIV.get(j)) and (na(TK.get(j)) or shTk)
            bool  tk = not na(TK.get(j))
            color c  = sideOf(j) == 1 ? cBSL : cSSL
            int   x1 = j < 6 ? dT : LIV.get(j)
            bool  top = (jB == j or jS == j)
            LN.push(line.new(x1, lv, tk ? TK.get(j) : xr, lv, xloc = xloc.bar_time, color = tk ? color.new(c, 70) : c, width = top ? 2 : 1, style = j < 6 ? line.style_solid : line.style_dashed))
            string tx = PN.get(j) + " " + px(lv) + (tk ? " ✓ " + str.format_time(TK.get(j), "HH:mm", TZ) : " · " + pc0(PP.get(j)) + " today")
            LB.push(label.new(tk ? TK.get(j) : xr, lv, tx, xloc = xloc.bar_time, style = sideOf(j) == 1 ? label.style_label_lower_left : label.style_label_upper_left, color = #00000000, textcolor = tk ? color.new(c, 50) : c, size = tSz, tooltip = tk ? PN.get(j) + " traded today at " + str.format_time(TK.get(j), "HH:mm", TZ) + " ET." : tipP))
    if showCrd
        bool mob = layI == "Mobile"
        if na(TC)
            TC := table.new(posOf(crdPos), 4, 18, border_width = 0, frame_width = 1, frame_color = cHdr)
        TC.clear(0, 0, 3, 17)
        TC.cell(0, 0, "SHINSŌ", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(1, 0, mob ? "" : "DRAW ON LIQUIDITY", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(2, 0, "today", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(3, 0, hm(relM), text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_right, text_font_family = font.family_monospace)
        int r = 1
        if not na(pRace)
            cRow(r, "FIRST", "▲ " + PN.get(jB), cBSL, pc0(pRace), PN.get(jS) + " ▼ " + pc0(1 - pRace), tipR)
            r += 1
        // pools above (farthest first), then below, each with its odds
        array<int> ord = array.new<int>()
        for j = 0 to 9
            if liveU(j) and onOf(j) and not na(PP.get(j))
                ord.push(j)
        // sort by price, descending
        int nO = ord.size()
        if nO > 1
            for a = 0 to nO - 2
                for b = 0 to nO - 2 - a
                    if LV.get(ord.get(b)) < LV.get(ord.get(b + 1))
                        int t = ord.get(b)
                        ord.set(b, ord.get(b + 1))
                        ord.set(b + 1, t)
        bool priceDone = false
        for k = 0 to (nO > 0 ? nO - 1 : 0)
            if nO == 0
                break
            int j = ord.get(k)
            if not priceDone and sideOf(j) == -1
                cRow(r, "— price", "", cSub, px(close), "", "")
                r += 1
                priceDone := true
            if not mob or j == jB or j == jS
                float d = (LV.get(j) - close) * sideOf(j) / atrD
                cRow(r, PN.get(j), gauge(PP.get(j), mob ? 6 : 10), sideOf(j) == 1 ? cBSL : cSSL, pc0(PP.get(j)), px(LV.get(j)) + " · " + str.tostring(d, "0.0") + " ATR", tipP)
                r += 1
        if not priceDone
            cRow(r, "— price", "", cSub, px(close), "", "")
            r += 1
        if not mob
            int nTk = nTB + nTS
            cRow(r, "taken today", "", cSub, str.tostring(nTk) + " pool" + (nTk == 1 ? "" : "s"), "▲ " + str.tostring(nTB) + " · ▼ " + str.tostring(nTS), "Pools traded since they went live today (all ten, including those switched off).")
            r += 1
            cRow(r, "draw rules", "", cSub, "≤ 1 pt", "beyond distance", "ICT's draw-on-liquidity readings, tested against the distance-and-time odds on 2025–26 (outcome minus the Brownian prediction, errors clustered by day): the other side already taken today −0.3 ± 0.5 points; nothing taken on the other side −1.0 ± 0.8; another pool stacked within 0.15 ATR +0.2 ± 1.3; the pool in the direction of the day's move −0.7 ± 0.7; against it −0.3 ± 0.6. None moved the odds. The trees use them anyway, for the small amount they add together.")
            r += 1
            cRow(r, "tested", "", cSub, "Brier 0.088", "flat 0.167", "Pools, 2025 – Oct 2026 out of sample: Brier 0.088, log-loss 0.276; distance-and-time alone 0.090 / 0.280; flat 0.167 / 0.517. Gain of the trees 0.004 log-loss (95% CI 0.002–0.007, day-clustered), on NQ, ES and RTY each.\nTaken by 16:59, per live pool sample: PDH / PDL 29%, PWH / PWL 11%, PMH / PML 5%, Asia 57%, London 50%.")
'''
P = P.replace('__CUM5__', cum5).replace('__EVD__', evd).replace('__EVR__', evr).replace('__TREES__', trees)
open('/home/claude/sn/Shinso.pine', 'w').write(P)
print('ok', P.count('\n'))
