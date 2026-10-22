"""Benihime v2: live fill model (distance now, retracement so far, open's place in the overnight range), tally-style
card with a fill bar, Desktop / Mobile layouts, alerts. Reads ../Benihime_RTH_Gaps.pine, writes Benihime_RTH_Gaps.pine."""
import re

src = open('/home/claude/rg/v2/Benihime_v1_backup.pine').read()


def rep(old, new, count=1):
    global src
    assert src.count(old) == count, (src.count(old), old[:80])
    src = src.replace(old, new)


# ── header comment
rep("""// with odds from NQ + ES + RTY 1-minute 2018–26 (6,169 gaps). Release days (CPI, NFP, PPI, GDP, PCE, retail sales,
// your own dates) switch the day's regime. Works on ETH and RTH charts. Use a back-adjusted (B-ADJ) continuous chart
// so roll days do not show as gaps.""",
    """// with odds from NQ + ES + RTY 1-minute 2018–26 (6,169 gaps). Live fill and CE odds follow the gap's size, the time,
// how far price is from the fill now, how far it has come back so far, and where the open sat in the overnight range.
// A tally-style card (Desktop / Mobile) with a fill bar, and alerts. Release days (CPI, NFP, PPI, GDP, PCE, retail
// sales, your own dates) switch the day's regime. Works on ETH and RTH charts. Use a back-adjusted (B-ADJ) continuous
// chart so roll days do not show as gaps.""")

# ── View inputs: layout and fill-bar colours
rep("""cardPos  = input.string("Top right", "", options = ["Top left", "Top center", "Top right", "Middle left", "Middle right", "Bottom left", "Bottom center", "Bottom right"], group = gV, inline = "cd", display = display.none)
""", """cardPos  = input.string("Top right", "", options = ["Top left", "Top center", "Top right", "Middle left", "Middle right", "Bottom left", "Bottom center", "Bottom right"], group = gV, inline = "cd", display = display.none)
layI     = input.string("Desktop", "Layout", options = ["Desktop", "Mobile"], group = gV, tooltip = "Desktop: every row. Mobile: one narrow card for a phone screen: the gap, the fill bar, the CE and ±1 SD (outside RTH: the close, if it opened now, and the next session). Every row keeps its full explanation in the tooltip. For a phone, use a separate chart layout set to Mobile, since layouts sync across devices.", display = display.none)
barCI    = input.string("Gap direction", "Fill bar", options = ["Gap direction", "Progress"], group = gV, inline = "fb", tooltip = "The FILL bar fills as price trades back from the open toward the prior close; the mark in the middle is the CE.\\nGap direction: the first colour for a gap up, the second for a gap down.\\nProgress: the second colour until the gap fills, then the first.", display = display.none)
colBU    = input.color(#26a69a, "", group = gV, inline = "fb", display = display.none)
colBD    = input.color(#ef5350, "", group = gV, inline = "fb", display = display.none)
""")

# ── Alerts group, before the release dates
rep("""// ═══════════════════════════════════════════════════════════════ Release dates (ET, 08:30)""",
    """gA = "Alerts · create one with \\"Any alert() function call\\""
alNew = input.bool(true, "New gap at 09:30", group = gA, tooltip = "Each fires once, on the bar it happens, with the numbers in the message: the gap's size against the average and its fill odds; the CE; the fill and the odds of −1 SD after it; ±1 SD.", display = display.none)
alCE  = input.bool(true, "CE reached", group = gA, display = display.none)
alFL  = input.bool(true, "Filled", group = gA, display = display.none)
alSD  = input.bool(false, "±1 SD reached", group = gA, display = display.none)

// ═══════════════════════════════════════════════════════════════ Release dates (ET, 08:30)""")

# ── Odds: replace the live tables with the fitted models
old_odds = src[src.index("// FL / CE: % that filled"):src.index("// ═══════════════════════════════════════════════════════════════ Colours and helpers")]
new_odds = """// Live odds (logistic models fitted on the 6,169 gaps, checked out of sample: fitted on 2018–24, scored on 2025–26).
// Each uses the gap's size (log of |gap| ÷ the 20-session average), the minutes since 09:30, and:
//   fill: how far price is from the prior close now and how far it has come back so far (both in gap sizes), and where
//         the open sat in the overnight range (18:00–09:29, 1 = at its extreme in the gap's direction);
//   CE:   how far price is from the CE now, and the open's place in the overnight range;
//   −1 SD after the fill: size, the minutes to the fill, and the open's place in the overnight range.
// Each term held pooled (p < 0.05, errors clustered by date), in 2018–24 and 2025–26, and on NQ, ES and RTY.
var array<int>   CKM = array.from(0, 15, 30, 45, 60, 90, 120, 180, 240, 300, 360, 405)
var array<float> FCK = array.from(0.0, -0.514, -0.694, -0.884, -0.987, -1.245, -1.446, -1.779, -2.128, -2.595, -3.284, -3.801)
var array<float> CCK = array.from(0.0, -0.139, -0.258, -0.412, -0.519, -0.725, -0.882, -1.158, -1.499, -1.960, -2.718, -3.286)
ONL_AVG = 0.705    // the average open location, used when the overnight range is not available
var array<float> SC1 = array.from(87.0, 63, 45, 32, 18)    // +1 SD beyond the open, by 16:14
var array<float> SO1 = array.from(79.0, 40, 20, 12, 5)     // 1 SD beyond the prior close, by 16:14
var array<float> W5F = array.from(97.0, 86, 80, 73, 63)    // filled while one of the last 5 (to the 5th next open)
var array<float> W5C = array.from(98.0, 93, 89, 84, 78)    // CE reached while one of the last 5
var array<float> A5F = array.from(70.0, 60, 60, 56, 53)    // not filled by 16:14 → filled by the 5th next open
bkOf(float r) => r < 0.5 ? 0 : r < 1.0 ? 1 : r < 1.5 ? 2 : r < 2.5 ? 3 : 4
bkNm(int b) => b == 0 ? "small" : b == 1 ? "below avg" : b == 2 ? "above avg" : b == 3 ? "large" : "very large"
clamp(float v, float lo, float hi) => math.max(lo, math.min(hi, v))
sigP(float z) => 100.0 / (1.0 + math.exp(-z))
ckOff(array<float> A, float mins) =>
    float m = clamp(mins, 0, 405)
    int i = 0
    while i < 10 and CKM.get(i + 1) <= m
        i += 1
    float f = (m - CKM.get(i)) / (CKM.get(i + 1) - CKM.get(i))
    A.get(i) * (1 - f) + A.get(i + 1) * f
onlOr(float v) => na(v) ? ONL_AVG : clamp(v, 0, 1.2)
// odds (%) of a fill by 16:14 / of the CE by 16:14 / of −1 SD by 16:14 once filled
pFill(float mins, float lr, float dist, float retr, float onl) => sigP(2.026 + ckOff(FCK, mins) - 1.071 * lr - 1.174 * clamp(dist, 0, 3) + 1.323 * clamp(retr, 0, 1) - 0.815 * onlOr(onl))
pCE(float mins, float lr, float dist, float onl) => sigP(2.523 + ckOff(CCK, mins) - 1.022 * lr - 1.389 * clamp(dist - 0.5, 0, 3) - 0.864 * onlOr(onl))
pAfter(float lr, float fillMin, float onl) => sigP(1.660 - 0.996 * lr - 0.296 * math.log(1 + math.max(0, fillMin)) - 0.662 * onlOr(onl))

"""
src = src.replace(old_odds, new_odds)

rep("""// Size = |gap| ÷ the average |gap| of the previous 20 sessions. Columns: <0.5, 0.5–1, 1–1.5, 1.5–2.5, 2.5+ (33 / 26 / 17 / 15 / 8% of gaps).
""", """// Size = |gap| ÷ the average |gap| of the previous 20 sessions. Buckets: <0.5, 0.5–1, 1–1.5, 1.5–2.5, 2.5+ (33 / 26 / 17 / 15 / 8% of gaps).
""")

# ── text gauges (helpers)
rep("""hhmm(int t) => str.format_time(t, "HH:mm", TZ)
""", """hhmm(int t) => str.format_time(t, "HH:mm", TZ)
gauge(float f, int n) =>
    int k = na(f) ? 0 : int(math.round(clamp(f, 0, 1) * n))
    str.repeat("█", k) + str.repeat("░", n - k)
// 10 cells, the CE mark after the 5th
fillBar(float f) =>
    string s = gauge(f, 10)
    str.substring(s, 0, 5) + "│" + str.substring(s, 5)
pc0(float p) => na(p) ? "—" : str.tostring(math.round(p)) + "%"
""")

# ── overnight range from 15-minute ETH bars (works on RTH charts too)
rep("""// ═══════════════════════════════════════════════════════════════ The chart's own RTH: today's touches to the minute""",
    """// ═══════════════════════════════════════════════════════════════ Overnight range (18:00–09:29 ET)
// From finished 15-minute bars of the extended session, so it is the same on ETH and RTH charts and sees no future data.
// Pre-market it is the range so far; from 09:30 it is the whole overnight.
onCtx() =>
    var float h = na
    var float l = na
    if bar_index > 1
        int  m1 = hour(time[1], TZ) * 60 + minute(time[1], TZ)
        int  m2 = hour(time[2], TZ) * 60 + minute(time[2], TZ)
        bool o1 = m1 >= 1080 or m1 < 570
        bool o2 = m2 >= 1080 or m2 < 570
        if o1 and not o2
            h := high[1]
            l := low[1]
        else if o1
            h := na(h) ? high[1] : math.max(h, high[1])
            l := na(l) ? low[1] : math.min(l, low[1])
    [h, l]
[onH, onL] = request.security(ticker.modify(syminfo.tickerid, session.extended), "15", onCtx(), lookahead = barmerge.lookahead_on)
// the open's place in the overnight range, 1 = at its extreme in the gap's direction
onlOf(float o, float c, float h, float l) => na(h) or na(l) or h <= l ? na : o > c ? (o - l) / (h - l) : (h - o) / (h - l)

// ═══════════════════════════════════════════════════════════════ The chart's own RTH: today's touches to the minute""")

# ── today's state: extreme toward the fill, size, open location; alerts
rep("""var int u2T = na
int  nA = na(gK) ? 0 : gK.size()""", """var int u2T = na
var float exT = na    // today's extreme toward the fill since 09:30 (low for a gap up, high for a gap down)
var float tLr = na    // log(|gap| ÷ 20-session average)
var float tOnl = na   // the open's place in the overnight range
var float tA20 = na
int  nA = na(gK) ? 0 : gK.size()""")
rep("""    s2T := na
    u1T := na
    u2T := na
if gapToday""", """    s2T := na
    u1T := na
    u2T := na
    exT := na
    tLr := na
    tOnl := na
    tA20 := na
if gapToday""")
rep("""        if na(s2T) and low <= bot - 2 * g
            s2T := time
""", """        if na(s2T) and low <= bot - 2 * g
            s2T := time
        exT := up ? (na(exT) ? low : math.min(exT, low)) : (na(exT) ? high : math.max(exT, high))
        if na(tA20)
            tA20 := avgPrev(20, nA - 1)
            tLr  := na(tA20) or tA20 <= 0 ? na : math.log(g / tA20)
            tOnl := onlOf(gOt, gCt, onH, onL)
        // alerts: once, on the bar it happens
        float  minsA = (time - t930(tdKey)) / 60000.0
        string pre   = "Benihime · " + syminfo.ticker + " · "
        float  lrA   = nz(tLr, 0.0)
        if alNew and rthBeg
            string tgA = tagOf(tdKey)
            alert(pre + "RTH gap " + (up ? "▲ " : "▼ ") + pts(g) + " pts" + (na(tA20) ? "" : " (" + str.tostring(g / tA20, "0.0") + "× avg, " + bkNm(bkOf(g / tA20)) + ")") + (tgA != "" ? " · " + tgA : "") + " · fill by 16:14 " + pc0(pFill(0, lrA, 1, 0, tOnl)) + " · CE " + px((gOt + gCt) / 2), alert.freq_once_per_bar)
        if alCE and ceT == time and (na(flT) or flT != time)
            alert(pre + "CE " + px((gOt + gCt) / 2) + " reached " + hhmm(time) + " · fill by 16:14 " + pc0(pFill(minsA, lrA, up ? (close - gCt) / g : (gCt - close) / g, up ? (gOt - exT) / g : (exT - gOt) / g, tOnl)), alert.freq_once_per_bar)
        if alFL and flT == time
            alert(pre + "RTH gap filled " + hhmm(time) + " at " + px(gCt) + " · −1 SD " + px(up ? bot - g : top + g) + " by 16:14 " + pc0(pAfter(lrA, minsA, tOnl)), alert.freq_once_per_bar)
        if alSD and (u1T == time or s1T == time)
            alert(pre + (u1T == time ? "+1 SD " + px(top + g) : "−1 SD " + px(bot - g)) + " reached " + hhmm(time), alert.freq_once_per_bar)
""")
# t930 / pts / px / tagOf / bkNm are defined above the RTH block already; avgPrev is defined below it → move avgPrev up
avg_block = """avgPrev(int n, int last) =>
    // average |gap| of the n sessions before index `last` (zero gaps count); na with fewer than 5
    float s = 0.0
    int   c = 0
    int   i = last - 1
    while i >= 0 and c < n
        s += math.abs(gO.get(i) - gC.get(i))
        c += 1
        i -= 1
    c >= 5 ? s / c : na

"""
rep(avg_block, "")
rep("""// ═══════════════════════════════════════════════════════════════ The chart's own RTH: today's touches to the minute""",
    avg_block + """// ═══════════════════════════════════════════════════════════════ The chart's own RTH: today's touches to the minute""")

# ── the card
card_old = src[src.index("// ═══════════════════════════════════════════════════════════════ Card: today's gap against the average"):]
card_new = open('/home/claude/rg/v2/card_v2.pine').read()
src = src.replace(card_old, card_new)
open('/home/claude/rg/v2/Benihime_RTH_Gaps.pine', 'w').write(src)
print('ok', len(src))
