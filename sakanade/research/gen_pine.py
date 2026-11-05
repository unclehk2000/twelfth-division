cum5 = open('/home/claude/sk/cum5.txt').read()
evd, evr = open('/home/claude/sk/ev.txt').read().split('\n')
trees = open('/home/claude/sk/day_trees.pine').read()
P = r'''//@version=6
// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © Unclehk2000
// Sakanade · is the high or low already in? Live odds that the day's high and low (18:00–17:00 ET) and the week's high and low
// hold to the close of the day and of the week. The day odds come from gradient-boosted trees (50 trees, depth 3) built on a
// Brownian touch probability that knows the intraday volatility profile, plus the time of day, the range used, the extreme
// against PDH / PDL, where and when the extreme was set and whether a CPI / NFP / FOMC release is still ahead today. Trained on
// NQ + ES + RTY 1-minute 2018–24 (911,630 samples), scored once on 2025 – Oct 2026 (237,142): Brier 0.135 against 0.239 for a
// flat rate and 0.138 for the Brownian model alone (log-loss gain 0.007, 95% CI 0.003–0.011, better on all three markets).
// The week odds use the Brownian model alone: the trees did not beat it out of sample (gain −0.003, CI −0.011 to 0.006).
// The odds are drawn on price at each extreme and as lines in the pane, with a card.
// ICT teaches the time of day and the weekly profiles where highs and lows form; the tests found the extremes pile up at the
// edges of each window (NY PM and Asia for the day, Friday and Monday for the week), as the arcsine law says they should.
// Not affiliated with or endorsed by ICT.
indicator("Sakanade · Is the High or Low In?", "Sakanade", overlay = false, max_lines_count = 50, max_labels_count = 50, precision = 0)

TZ = "America/New_York"

// ═══════════════════════════════════════════════════════════════ Inputs
gV = "View"
themeI  = input.string("Auto", "Card theme", options = ["Auto", "Dark", "Light"], group = gV, display = display.none)
lblSzI  = input.string("Small", "Text size", options = ["Tiny", "Small", "Normal"], group = gV, display = display.none)
showCrd = input.bool(true, "Card", group = gV, inline = "cd", display = display.none)
crdPos  = input.string("Top right", "", options = ["Top left", "Top center", "Top right", "Middle left", "Middle right", "Bottom left", "Bottom center", "Bottom right"], group = gV, inline = "cd", display = display.none)
layI    = input.string("Desktop", "Layout", options = ["Desktop", "Mobile"], group = gV, tooltip = "Desktop: the four extremes and the tested rows. Mobile: the four extremes only.", display = display.none)

gL = "On price"
dayOn = input.bool(true, "Day high / low with odds", group = gL, inline = "d", display = display.none)
wkOn  = input.bool(true, "Week high / low with odds", group = gL, inline = "d", display = display.none)
extN  = input.int(10, "Extend right (bars)", minval = 0, maxval = 100, group = gL, display = display.none)
cHi   = input.color(#ef5350, "Highs", group = gL, inline = "c", display = display.none)
cLo   = input.color(#26a69a, "Lows", group = gL, inline = "c", display = display.none)

gP = "Pane"
pDay = input.bool(true, "Day odds", group = gP, inline = "p", tooltip = "The chance the day's high (red) and low (green) hold to 16:59, bar by bar.", display = display.none)
pWk  = input.bool(true, "Week odds", group = gP, inline = "p", tooltip = "The chance the week's high and low hold to Friday 16:59, dotted.", display = display.none)

gA = "Alerts · create one with \"Any alert() function call\""
alT = input.int(80, "Day odds cross above (%)", minval = 50, maxval = 99, group = gA, tooltip = "An alert when the chance the day's high, or low, holds first rises through this level.", display = display.none)
alOn = input.bool(false, "Alert", group = gA, display = display.none)

// ═══════════════════════════════════════════════════════════════ Helpers
bgLum  = 0.299 * color.r(chart.bg_color) + 0.587 * color.g(chart.bg_color) + 0.114 * color.b(chart.bg_color)
isDark = themeI == "Dark" or (themeI == "Auto" and bgLum < 128)
cTxt   = isDark ? #d1d4dc : #131722
cBody  = isDark ? #161a23 : #f4f6f9
cSub   = isDark ? #8a93a6 : #5d6476
cHdr   = #6d4c41
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
lgs(float z) => 1.0 / (1.0 + math.exp(-z))
hm(int r) =>
    int t = (r + 1080) % 1440
    str.format("{0}:{1}", str.tostring(int(t / 60), "00"), str.tostring(t % 60, "00"))

// ═══════════════════════════════════════════════════════════════ Model constants
// expected variance still to come in the trading day, in daily ATR² units, from each 5-minute mark after 18:00 (NQ + ES + RTY 2018–24:
// the mean squared 1-minute range over the daily ATR(14), summed to 16:59); linear between marks
var array<float> CUM5 = array.from(__CUM5__)
var float PMDAY = CUM5.get(0)
vRem(float r) =>
    float rr = clamp(r, 0, 1380)
    int   b  = math.min(int(rr / 5), 275)
    float f  = (rr - 5 * b) / 5.0
    CUM5.get(b) + f * (CUM5.get(b + 1) - CUM5.get(b))
// CPI and NFP (08:30) and FOMC (14:00) days, 2025–27, with the release in minutes after 18:00
var array<int> EVD = __EVD__
var array<int> EVR = __EVR__
__TREES__

// week model: Brownian, p = logistic(a + b·logit(2Φ(k·z) − 1)), z = distance / √(variance left in the week)
pWeek(float z) => lgs(0.514 + 1.017 * lgt(2.0 * nCdf(1.30 * z) - 1.0))

// ═══════════════════════════════════════════════════════════════ Data
[atrD, pdh, pdl] = request.security(syminfo.tickerid, "D", [ta.atr(14)[1], high[1], low[1]], lookahead = barmerge.lookahead_on)
[pwh, pwl] = request.security(syminfo.tickerid, "W", [high[1], low[1]], lookahead = barmerge.lookahead_on)
bool act   = timeframe.isintraday and timeframe.in_seconds() <= 3600
int  tfMin = int(timeframe.in_seconds() / 60)
int  relM  = ((hour(time, TZ) * 60 + minute(time, TZ)) - 1080 + 1440) % 1440
bool newD  = timeframe.change("D")
bool newW  = timeframe.change("W")
var float dO  = na
var float dH  = na
var float dL  = na
var int   dHr = na
var int   dLr = na
var int   dHt = na
var int   dLt = na
var float wH  = na
var float wL  = na
var int   wHt = na
var int   wLt = na
if newD or na(dH)
    dO  := open
    dH  := high
    dL  := low
    dHr := relM
    dLr := relM
    dHt := time
    dLt := time
else
    if high > dH
        dH  := high
        dHr := relM
        dHt := time
    if low < dL
        dL  := low
        dLr := relM
        dLt := time
if newW or na(wH)
    wH  := high
    wL  := low
    wHt := time
    wLt := time
else
    if high > wH
        wH  := high
        wHt := time
    if low < wL
        wL  := low
        wLt := time

// the trading day's date, weekday and the next release still ahead today
int  tdD  = time_tradingday
// time_tradingday is the trading day's date at 00:00 UTC (a Sunday-evening session belongs to Monday)
int  ymd  = year(tdD, "UTC") * 10000 + month(tdD, "UTC") * 100 + dayofmonth(tdD, "UTC")
int  dow0 = (dayofweek(tdD, "UTC") + 5) % 7
int  rNow = relM + tfMin
evAhead() =>
    float out = -1.0
    int   k   = EVD.binary_search_leftmost(ymd)
    while k < EVD.size() and k >= 0
        if EVD.get(k) != ymd
            break
        if EVR.get(k) > rNow - 1
            out := out < 0 ? EVR.get(k) : math.min(out, EVR.get(k))
        k += 1
    out

// ═══════════════════════════════════════════════════════════════ Odds
float pHD = na
float pLD = na
float pHW = na
float pLW = na
if act and atrD > 0 and not na(pdh) and rNow < 1380
    float v   = math.max(vRem(rNow), 1e-6)
    float rg  = dH - dL
    float ev  = evAhead()
    float zH  = (dH - close) / atrD / math.sqrt(v)
    float zL  = (close - dL) / atrD / math.sqrt(v)
    pHD := dayTrees(lgt(2.0 * nCdf(1.10 * zH) - 1.0), 1.0, rNow, rg / atrD, relM - dHr, rg > 0 ? (close - dL) / rg : 0.5, (dH - pdh) / atrD, (close - dO) / atrD, dHr, ev, dow0)
    pLD := dayTrees(lgt(2.0 * nCdf(1.10 * zL) - 1.0), -1.0, rNow, rg / atrD, relM - dLr, rg > 0 ? (dH - close) / rg : 0.5, (pdl - dL) / atrD, (dO - close) / atrD, dLr, ev, dow0)
    // week: the rest of today plus each full day left to Friday
    int   dLeft = math.max(4 - dow0, 0)
    float vw    = math.max(v + dLeft * PMDAY, 1e-6)
    pHW := pWeek((wH - close) / atrD / math.sqrt(vw))
    pLW := pWeek((close - wL) / atrD / math.sqrt(vw))

plot(pDay ? 100 * pHD : na, "Day high holds", color = cHi, linewidth = 2)
plot(pDay ? 100 * pLD : na, "Day low holds", color = cLo, linewidth = 2)
plot(pWk ? 100 * pHW : na, "Week high holds", color = color.new(cHi, 40), style = plot.style_circles, linewidth = 1)
plot(pWk ? 100 * pLW : na, "Week low holds", color = color.new(cLo, 40), style = plot.style_circles, linewidth = 1)
hline(50, "50%", color = color.new(cSub, 60), linestyle = hline.style_dotted)
hline(80, "80%", color = color.new(cSub, 80), linestyle = hline.style_dotted)

if alOn and act and barstate.isconfirmed
    if pHD >= alT / 100.0 and nz(pHD[1]) < alT / 100.0
        alert("Sakanade · " + syminfo.ticker + " · the day's high " + px(dH) + " now holds " + pc0(pHD) + " of the time to 16:59", alert.freq_once_per_bar_close)
    if pLD >= alT / 100.0 and nz(pLD[1]) < alT / 100.0
        alert("Sakanade · " + syminfo.ticker + " · the day's low " + px(dL) + " now holds " + pc0(pLD) + " of the time to 16:59", alert.freq_once_per_bar_close)

// ═══════════════════════════════════════════════════════════════ On price and the card (last bar)
var line  lHD = na
var line  lLD = na
var line  lHW = na
var line  lLW = na
var label bHD = na
var label bLD = na
var label bHW = na
var label bLW = na
var table TC = na
tipD = "Day: 18:00–17:00 ET. The chance the extreme is not exceeded before 16:59, from gradient-boosted trees on: a Brownian touch probability (distance in daily ATR(14) over the square root of the volatility still to come today, from the intraday profile), the time, the range used, where price sits in the range, the extreme against PDH / PDL, the move since 18:00, when the extreme was set, how long ago, a CPI / NFP / FOMC release still ahead and the weekday.\nScored on 2025 – Oct 2026 (fit 2018–24): predicted → actual 6→6, 15→15, 25→26, 35→36, 45→47, 55→57, 65→66, 75→78, 85→88, 96→98%. Brier 0.135 vs 0.239 flat."
tipW = "Week: Sunday 18:00 – Friday 17:00 ET. The chance the extreme is not exceeded before Friday 16:59, from the Brownian model alone: distance in daily ATR(14) over the square root of the volatility left in the week. Scored on 2025 – Oct 2026: 5→5, 15→12, 25→22, 35→33, 45→39, 55→48, 65→62, 75→74, 85→86, 97→97%; Brier 0.143 vs 0.248 flat. Gradient-boosted trees did not do better here, so they are not used."
cRow(int r, string k, string g, color gc, string v, string w, string tip) =>
    TC.cell(0, r, k, text_color = cSub, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(1, r, g, text_color = gc, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(2, r, v, text_color = cTxt, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(3, r, w, text_color = cSub, text_size = tSz, text_halign = text.align_right, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
setLv(line l, label b, int t0, float y, int xr, string tx, string tip, color c, bool hi) =>
    line.set_xy1(l, t0, y)
    line.set_xy2(l, xr, y)
    label.set_xy(b, xr, y)
    label.set_text(b, tx)
    label.set_tooltip(b, tip)
    label.set_textcolor(b, c)
    label.set_style(b, hi ? label.style_label_lower_left : label.style_label_upper_left)

if barstate.islast and act
    int xr = time + extN * timeframe.in_seconds() * 1000
    if na(lHD)
        lHD := line.new(na, na, na, na, xloc = xloc.bar_time, color = cHi, width = 1, force_overlay = true)
        lLD := line.new(na, na, na, na, xloc = xloc.bar_time, color = cLo, width = 1, force_overlay = true)
        lHW := line.new(na, na, na, na, xloc = xloc.bar_time, color = color.new(cHi, 30), style = line.style_dashed, width = 1, force_overlay = true)
        lLW := line.new(na, na, na, na, xloc = xloc.bar_time, color = color.new(cLo, 30), style = line.style_dashed, width = 1, force_overlay = true)
        bHD := label.new(na, na, "", xloc = xloc.bar_time, color = #00000000, size = tSz, force_overlay = true)
        bLD := label.new(na, na, "", xloc = xloc.bar_time, color = #00000000, size = tSz, force_overlay = true)
        bHW := label.new(na, na, "", xloc = xloc.bar_time, color = #00000000, size = tSz, force_overlay = true)
        bLW := label.new(na, na, "", xloc = xloc.bar_time, color = #00000000, size = tSz, force_overlay = true)
    if dayOn
        setLv(lHD, bHD, dHt, dH, xr, "Day high " + px(dH) + " · holds " + pc0(pHD), tipD, cHi, true)
        setLv(lLD, bLD, dLt, dL, xr, "Day low " + px(dL) + " · holds " + pc0(pLD), tipD, cLo, false)
    if wkOn
        bool sameH = dayOn and wH == dH
        bool sameL = dayOn and wL == dL
        setLv(lHW, bHW, wHt, wH, xr, (sameH ? "  = week high · holds " : "Week high " + px(wH) + " · holds ") + pc0(pHW), tipW, color.new(cHi, 20), not sameH)
        setLv(lLW, bLW, wLt, wL, xr, (sameL ? "  = week low · holds " : "Week low " + px(wL) + " · holds ") + pc0(pLW), tipW, color.new(cLo, 20), sameL)
    if showCrd
        bool mob = layI == "Mobile"
        if na(TC)
            TC := table.new(posOf(crdPos), 4, 12, border_width = 0, frame_width = 1, frame_color = cHdr, force_overlay = true)
        TC.clear(0, 0, 3, 11)
        TC.cell(0, 0, "SAKANADE", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(1, 0, mob ? "" : "IS IT IN?", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(2, 0, "holds", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(3, 0, hm(relM), text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_right, text_font_family = font.family_monospace)
        cRow(1, "DAY HIGH", gauge(pHD, mob ? 6 : 10), cHi, pc0(pHD), px(dH) + " · " + hm(dHr), tipD)
        cRow(2, "DAY LOW", gauge(pLD, mob ? 6 : 10), cLo, pc0(pLD), px(dL) + " · " + hm(dLr), tipD)
        cRow(3, "WEEK HIGH", gauge(pHW, mob ? 6 : 10), cHi, pc0(pHW), px(wH), tipW)
        cRow(4, "WEEK LOW", gauge(pLW, mob ? 6 : 10), cLo, pc0(pLW), px(wL), tipW)
        if not mob
            float ev = evAhead()
            cRow(5, "release ahead", "", cSub, ev < 0 ? "none today" : hm(int(ev)), "", "A CPI / NFP (08:30) or FOMC (14:00) release still ahead today is one of the model's inputs.", )
            cRow(6, "day H forms", "", cSub, "NY PM 35%", "AM 27 · Asia 17", "When the trading day's final high was made, NQ + ES + RTY 2018–26: Asia (18:00–00:00) 16.4%, London (00:00–06:00) 10.3%, 06:00–09:30 9.4%, NY AM (09:30–13:00) 27.1%, NY PM (13:00–17:00) 36.7% (2025–26: 17.1, 10.2, 12.1, 26.9, 33.6). The final low: Asia 22.5%, London 11.0%, 06:00–09:30 8.7%, NY AM 28.7%, NY PM 29.2%. Extremes pile up at the two ends of the day, as a random walk's do (the arcsine law).")
            cRow(7, "week H forms", "", cSub, "Fri 34%", "Mon 18", "The weekday of the week's high, 2018–24: Mon 18.3%, Tue 18.9, Wed 12.0, Thu 16.9, Fri 33.9 (2025–26: 20.9, 11.4, 18.6, 17.1, 31.9). The week's low: Mon 32.6%, Tue 16.1, Wed 10.9, Thu 16.5, Fri 23.9 (2025–26: 29.3, 16.3, 16.0, 8.7, 29.7). Monday and Friday hold the most, the ends of the window; no midweek day stands out the way the 'Tuesday low' teaching says.")
            cRow(8, "tested", "", cSub, "Brier 0.135", "flat 0.239", "Day model, 2025 – Oct 2026 out of sample: Brier 0.135, log-loss 0.420; the Brownian part alone 0.138 / 0.427; a flat rate 0.239 / 0.671. The trees' gain over the Brownian model: 0.007 log-loss (95% CI 0.003–0.011, day-clustered bootstrap), on NQ, ES and RTY each. The Brownian part carries 94% of the trees' splits; the time of day, the extreme against PDH / PDL, the range used, when the extreme was set and a release ahead carry the rest.")
'''
P = P.replace('__CUM5__', cum5).replace('__EVD__', evd).replace('__EVR__', evr).replace('__TREES__', trees)
P = P.replace('"A CPI / NFP (08:30) or FOMC (14:00) release still ahead today is one of the model\'s inputs.", )', '"A CPI / NFP (08:30) or FOMC (14:00) release still ahead today is one of the model\'s inputs.")')
open('/home/claude/sk/Sakanade.pine', 'w').write(P)
print('ok', P.count('\n'))
