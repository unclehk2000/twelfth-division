coef, qs = open('/home/claude/rj/coef.txt').read().split('\n')
evd, evt = open('/home/claude/rj/ev.txt').read().split('\n')
P = r'''//@version=6
// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © Unclehk2000
// Ryūjin Jakka · session range forecasts. The expected high-to-low range of each session (Asia 20:00–00:00, London 02:00–05:00,
// NY AM 09:30–12:00, NY PM 13:30–16:00 ET) with its 25–75% and 10–90% bands, forecast at the session's start from the same
// session's recent ranges (1, 5 and 20 days), today's range and move so far, the session before it, daily ATR against its 60-day
// mean, VIX against its 20-day mean, CPI / NFP / FOMC days and the weekday. While a session runs, the forecast ranges are
// projected up from its low and down from its high, and the card shows how much of the expected range is used.
// One linear model per session, fitted on NQ + ES + RTY 1-minute 2018–24 and scored once on 2025 – Oct 2026: R² 0.30 (Asia),
// 0.34 (London), 0.29 (NY AM), 0.38 (NY PM) on the log range, against 0.00–0.07 for the plain 20-day average; the 25–75% band held
// 47–52% of sessions and the 10–90% band 76–80%. Gradient-boosted trees were tried and did worse (R² 0.26–0.33).
// Release days, beyond the rest of the model: FOMC afternoons ran 2.5× (t 12.8), FOMC mornings 17% smaller; ranges before CPI and NFP
// were 7–10% smaller in Asia and London.
// ICT teaches the killzones; how far each one runs is what this forecasts. Not affiliated with or endorsed by ICT.
indicator("Ryūjin Jakka · Session Range Forecasts", "Ryūjin Jakka", overlay = true, max_lines_count = 100, max_labels_count = 100, max_boxes_count = 20, behind_chart = false)

TZ = "America/New_York"

// ═══════════════════════════════════════════════════════════════ Inputs
gV = "View"
themeI  = input.string("Auto", "Card theme", options = ["Auto", "Dark", "Light"], group = gV, display = display.none)
lblSzI  = input.string("Small", "Text size", options = ["Tiny", "Small", "Normal"], group = gV, display = display.none)
showCrd = input.bool(true, "Card", group = gV, inline = "cd", display = display.none)
crdPos  = input.string("Top right", "", options = ["Top left", "Top center", "Top right", "Middle left", "Middle right", "Bottom left", "Bottom center", "Bottom right"], group = gV, inline = "cd", display = display.none)
layI    = input.string("Desktop", "Layout", options = ["Desktop", "Mobile"], group = gV, tooltip = "Desktop: the four sessions and the tested rows. Mobile: the four sessions, narrow.", display = display.none)

gS = "Sessions"
on0 = input.bool(true, "Asia 20:00–00:00", group = gS, inline = "s1", display = display.none)
on1 = input.bool(true, "London 02:00–05:00", group = gS, inline = "s1", display = display.none)
on2 = input.bool(true, "NY AM 09:30–12:00", group = gS, inline = "s2", display = display.none)
on3 = input.bool(true, "NY PM 13:30–16:00", group = gS, inline = "s2", display = display.none)
prjI = input.string("50 / 75 / 90%", "Projections while a session runs", options = ["50 / 75 / 90%", "50% only", "Off"], group = gS, tooltip = "The forecast ranges, measured up from the session's low and down from its high: where the session's high (low) would sit if its low (high) is in and the range reaches its median, 75th or 90th percentile.", display = display.none)
boxI = input.bool(true, "Shade each session", group = gS, display = display.none)
cBx  = input.color(color.new(#ff6d00, 92), "Session", group = gS, inline = "c", display = display.none)
cPj  = input.color(#ff6d00, "Projections", group = gS, inline = "c", display = display.none)
vixI = input.symbol("CBOE:VIX", "VIX", group = gS, tooltip = "VIX against its 20-day mean is one of the inputs (the model was fitted with the CBOE VIX for NQ, ES and RTY).", display = display.none)

gA = "Alerts · create one with \"Any alert() function call\""
alX = input.bool(true, "Session passes its 90% range", group = gA, display = display.none)

// ═══════════════════════════════════════════════════════════════ Helpers
bgLum  = 0.299 * color.r(chart.bg_color) + 0.587 * color.g(chart.bg_color) + 0.114 * color.b(chart.bg_color)
isDark = themeI == "Dark" or (themeI == "Auto" and bgLum < 128)
cTxt   = isDark ? #d1d4dc : #131722
cBody  = isDark ? #161a23 : #f4f6f9
cSub   = isDark ? #8a93a6 : #5d6476
cHdr   = #e65100
tSz = lblSzI == "Tiny" ? size.tiny : lblSzI == "Normal" ? size.normal : size.small
px(float v) => str.tostring(v, format.mintick)
pts(float v) => na(v) ? "—" : str.tostring(v, "#,##0.#")
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
relOf(int t) => ((hour(t, TZ) * 60 + minute(t, TZ)) - 1080 + 1440) % 1440

// ═══════════════════════════════════════════════════════════════ Model
// sessions in minutes after 18:00 ET: start, end
var array<int>    SA = array.from(120, 480, 930, 1170)
var array<int>    SB = array.from(360, 660, 1080, 1320)
var array<string> SN = array.from("ASIA", "LONDON", "NY AM", "NY PM")
var array<string> ST = array.from("20:00–00:00", "02:00–05:00", "09:30–12:00", "13:30–16:00")
// one linear model per session for log(range / daily ATR): b0, then l1, l5, l20, range so far, move so far, previous session,
// ATR vs its 60-day mean, VIX vs its 20-day mean, weekday, CPI, NFP, FOMC, release in the session (fit 2018–24)
var array<float> CF = array.from(__COEF__)
// residual quantiles 10 / 25 / 50 / 75 / 90% per session (2018–24)
var array<float> QQ = array.from(__Q__)
var array<int> EVD = __EVD__
var array<int> EVT = __EVT__
onS(int s) => s == 0 ? on0 : s == 1 ? on1 : s == 2 ? on2 : on3

// ═══════════════════════════════════════════════════════════════ History on 30-minute candles
// each session's log(range / daily ATR) for the last 20 days, with a daily ATR(14) kept inside the 30-minute series
hist() =>
    var array<float> H0 = array.new<float>()
    var array<float> H1 = array.new<float>()
    var array<float> H2 = array.new<float>()
    var array<float> H3 = array.new<float>()
    var float atrX = na
    var float dh = na
    var float dl = na
    var float dc = na
    var float pc = na
    var array<float> sh = array.new<float>(4, na)
    var array<float> sl = array.new<float>(4, na)
    int r = relOf(time)
    if time_tradingday != time_tradingday[1]
        sh.fill(na)
        sl.fill(na)
        if not na(dh)
            float tr = na(pc) ? dh - dl : math.max(dh - dl, math.max(math.abs(dh - pc), math.abs(dl - pc)))
            atrX := na(atrX) ? tr : atrX + (tr - atrX) / 14.0
            pc := dc
        dh := high
        dl := low
    else
        dh := math.max(nz(dh, high), high)
        dl := math.min(nz(dl, low), low)
    dc := close
    for s = 0 to 3
        int a = s == 0 ? 120 : s == 1 ? 480 : s == 2 ? 930 : 1170
        int b = s == 0 ? 360 : s == 1 ? 660 : s == 2 ? 1080 : 1320
        if r >= a and r < b
            sh.set(s, na(sh.get(s)) or r == a ? high : math.max(sh.get(s), high))
            sl.set(s, na(sl.get(s)) or r == a ? low : math.min(sl.get(s), low))
            if r + 30 >= b and atrX > 0
                float v = math.log(math.max(sh.get(s) - sl.get(s), syminfo.mintick) / atrX)
                array<float> A = s == 0 ? H0 : s == 1 ? H1 : s == 2 ? H2 : H3
                A.push(v)
                if A.size() > 20
                    A.shift()
    // l1, l5, l20 per session
    float a1 = H0.size() > 0 ? H0.last() : na
    float a5 = H0.size() >= 5 ? H0.slice(H0.size() - 5, H0.size()).avg() : na
    float a20 = H0.size() >= 20 ? H0.avg() : na
    float b1 = H1.size() > 0 ? H1.last() : na
    float b5 = H1.size() >= 5 ? H1.slice(H1.size() - 5, H1.size()).avg() : na
    float b20 = H1.size() >= 20 ? H1.avg() : na
    float c1 = H2.size() > 0 ? H2.last() : na
    float c5 = H2.size() >= 5 ? H2.slice(H2.size() - 5, H2.size()).avg() : na
    float c20 = H2.size() >= 20 ? H2.avg() : na
    float d1 = H3.size() > 0 ? H3.last() : na
    float d5 = H3.size() >= 5 ? H3.slice(H3.size() - 5, H3.size()).avg() : na
    float d20 = H3.size() >= 20 ? H3.avg() : na
    [a1, a5, a20, b1, b5, b20, c1, c5, c20, d1, d5, d20]

bool act = timeframe.isintraday and timeframe.in_seconds() <= 1800
[a1, a5, a20, b1, b5, b20, c1, c5, c20, d1, d5, d20] = request.security(syminfo.tickerid, "30", hist(), calc_bars_count = 6000)
[atrD, atr60] = request.security(syminfo.tickerid, "D", [ta.atr(14)[1], ta.sma(ta.atr(14), 60)[1]], lookahead = barmerge.lookahead_on)
[vx, vx20] = request.security(vixI, "D", [close[1], ta.sma(close, 20)[1]], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)

lOf(int s, int k) =>
    s == 0 ? (k == 0 ? a1 : k == 1 ? a5 : a20) : s == 1 ? (k == 0 ? b1 : k == 1 ? b5 : b20) : s == 2 ? (k == 0 ? c1 : k == 1 ? c5 : c20) : (k == 0 ? d1 : k == 1 ? d5 : d20)

// ═══════════════════════════════════════════════════════════════ Today
int  relM = relOf(time)
bool newD = timeframe.change("D")
int  tdD  = time_tradingday
int  ymd  = year(tdD, "UTC") * 10000 + month(tdD, "UTC") * 100 + dayofmonth(tdD, "UTC")
int  dow0 = (dayofweek(tdD, "UTC") + 5) % 7
var float dO = na
var float dHi = na
var float dLo = na
var array<float> sH  = array.new<float>(4, na)    // session high / low today
var array<float> sL  = array.new<float>(4, na)
var array<int>   sT  = array.new<int>(4, na)      // session start time today
var array<float> mu  = array.new<float>(4, na)    // forecast log(range / ATR), fixed at the session's start
var array<float> aD  = array.new<float>(4, na)    // the ATR it was made with
var array<bool>  x90 = array.new<bool>(4, false)
evType(int typ) =>
    bool out = false
    int  k   = EVD.binary_search_leftmost(ymd)
    while k < EVD.size() and k >= 0
        if EVD.get(k) != ymd
            break
        if EVT.get(k) == typ
            out := true
        k += 1
    out
// the forecast for session s from what is known now
fc(int s, float soRg, float soMv, float prv) =>
    bool cpi = evType(1)
    bool nfp = evType(2)
    bool fom = evType(3)
    float evS = s == 2 ? (cpi or nfp ? 1.0 : 0.0) : s == 3 ? (fom ? 1.0 : 0.0) : 0.0
    float aR = atr60 > 0 ? math.log(atrD / atr60) : 0.0
    float vR = vx20 > 0 ? math.log(vx / vx20) : 0.0
    int o = s * 14
    CF.get(o) + CF.get(o + 1) * lOf(s, 0) + CF.get(o + 2) * lOf(s, 1) + CF.get(o + 3) * lOf(s, 2) + CF.get(o + 4) * soRg + CF.get(o + 5) * soMv + CF.get(o + 6) * prv + CF.get(o + 7) * aR + CF.get(o + 8) * vR + CF.get(o + 9) * dow0 + CF.get(o + 10) * (cpi ? 1 : 0) + CF.get(o + 11) * (nfp ? 1 : 0) + CF.get(o + 12) * (fom ? 1 : 0) + CF.get(o + 13) * evS
rngQ(int s, float m, int qi, float a) => a * math.exp(m + QQ.get(s * 5 + qi))
prevOf(int s) =>
    s == 0 ? lOf(0, 0) : not na(sH.get(s - 1)) and atrD > 0 ? math.log(math.max(sH.get(s - 1) - sL.get(s - 1), syminfo.mintick) / atrD) : lOf(s - 1, 0)
string xMsg = ""
if act
    if newD or na(dO)
        dO  := open
        dHi := high
        dLo := low
        for s = 0 to 3
            sH.set(s, na)
            sL.set(s, na)
            sT.set(s, na)
            mu.set(s, na)
            aD.set(s, na)
            x90.set(s, false)
    for s = 0 to 3
        if relM >= SA.get(s) and relM < SB.get(s)
            if na(sT.get(s))
                // the forecast is fixed at the session's first candle, from the day so far before it
                float soRg = dHi > dLo and atrD > 0 ? math.log((dHi - dLo) / atrD) : math.log(0.05)
                float soMv = atrD > 0 ? math.abs(close[1] - dO) / atrD : 0.0
                sT.set(s, time)
                mu.set(s, fc(s, soRg, soMv, prevOf(s)))
                aD.set(s, atrD)
                sH.set(s, high)
                sL.set(s, low)
            else
                sH.set(s, math.max(sH.get(s), high))
                sL.set(s, math.min(sL.get(s), low))
            if not x90.get(s) and not na(mu.get(s)) and sH.get(s) - sL.get(s) > rngQ(s, mu.get(s), 4, aD.get(s))
                x90.set(s, true)
                if onS(s)
                    xMsg += SN.get(s) + " passed its 90% range (" + pts(rngQ(s, mu.get(s), 4, aD.get(s))) + " pts). "
    dHi := math.max(dHi, high)
    dLo := math.min(dLo, low)
if alX and xMsg != "" and barstate.isconfirmed
    alert("Ryūjin Jakka · " + syminfo.ticker + " · " + xMsg, alert.freq_once_per_bar_close)

// ═══════════════════════════════════════════════════════════════ Drawing and card (last bar)
var array<line>  LN = array.new<line>()
var array<label> LB = array.new<label>()
var array<box>   BX = array.new<box>()
var table TC = na
tipF = "Forecast at the session's start from: the same session's log range over the last 1, 5 and 20 days (in daily ATR), today's range and move so far, the session before it, daily ATR(14) against its 60-day mean, VIX against its 20-day mean, CPI / NFP / FOMC days and the weekday. One linear model per session, fit on NQ + ES + RTY 1-minute 2018–24.\nScored once on 2025 – Oct 2026: the 25–75% band held 48.8% (Asia), 49.5% (London), 52.2% (NY AM) and 46.6% (NY PM) of sessions; the 10–90% band 76.8%, 77.4%, 80.4%, 76.2%. R² on the log range 0.30, 0.34, 0.29, 0.38, against 0.00–0.07 for the plain 20-day average. Gradient-boosted trees did worse (0.26–0.33), so the linear model is used."
cRow(int r, string k, string g, color gc, string v, string w, string tip) =>
    TC.cell(0, r, k, text_color = cSub, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(1, r, g, text_color = gc, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(2, r, v, text_color = cTxt, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(3, r, w, text_color = cSub, text_size = tSz, text_halign = text.align_right, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
if barstate.islast and not act and showCrd
    if na(TC)
        TC := table.new(posOf(crdPos), 1, 1, border_width = 0, frame_width = 1, frame_color = cHdr)
    TC.cell(0, 0, "Ryūjin Jakka · use a chart of 30 minutes or less", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_font_family = font.family_monospace)
if barstate.islast and act and atrD > 0
    while LN.size() > 0
        LN.pop().delete()
    while LB.size() > 0
        LB.pop().delete()
    while BX.size() > 0
        BX.pop().delete()
    float soRgN = dHi > dLo ? math.log((dHi - dLo) / atrD) : math.log(0.05)
    float soMvN = math.abs(close - dO) / atrD
    int ms = 60000
    if showCrd
        if na(TC)
            TC := table.new(posOf(crdPos), 4, 12, border_width = 0, frame_width = 1, frame_color = cHdr)
        TC.clear(0, 0, 3, 11)
        bool mob = layI == "Mobile"
        TC.cell(0, 0, "RYŪJIN JAKKA", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(1, 0, mob ? "" : "SESSION RANGES", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(2, 0, "p50 · p25–p75", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        TC.cell(3, 0, "pts", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_right, text_font_family = font.family_monospace)
    for s = 0 to 3
        if onS(s)
            bool  started = not na(sT.get(s))
            bool  live    = started and relM < SB.get(s) and relM >= SA.get(s)
            float m = started ? mu.get(s) : fc(s, soRgN, soMvN, prevOf(s))
            float a = started ? aD.get(s) : atrD
            float r50 = rngQ(s, m, 2, a)
            float r25 = rngQ(s, m, 1, a)
            float r75 = rngQ(s, m, 3, a)
            float r90 = rngQ(s, m, 4, a)
            float r10 = rngQ(s, m, 0, a)
            float rg  = started ? sH.get(s) - sL.get(s) : na
            if started
                int t0 = sT.get(s)
                int t1 = t0 + (SB.get(s) - SA.get(s)) * ms
                if boxI
                    BX.push(box.new(t0, sH.get(s), t1, sL.get(s), xloc = xloc.bar_time, bgcolor = cBx, border_color = color.new(cPj, 70)))
                if live and prjI != "Off"
                    for qi = 2 to 4
                        if qi == 2 or prjI == "50 / 75 / 90%"
                            float R = rngQ(s, m, qi, a)
                            string nm = qi == 2 ? "p50" : qi == 3 ? "p75" : "p90"
                            int    w  = qi == 2 ? 2 : 1
                            string stl = qi == 2 ? line.style_dashed : line.style_dotted
                            LN.push(line.new(time, sL.get(s) + R, t1, sL.get(s) + R, xloc = xloc.bar_time, color = cPj, style = stl, width = w))
                            LN.push(line.new(time, sH.get(s) - R, t1, sH.get(s) - R, xloc = xloc.bar_time, color = cPj, style = stl, width = w))
                            LB.push(label.new(t1, sL.get(s) + R, nm + " from the low · " + pts(R), xloc = xloc.bar_time, style = label.style_label_left, color = #00000000, textcolor = cPj, size = size.tiny, tooltip = "If " + SN.get(s) + "'s low is in, its high would sit here at the forecast's " + nm + " range (" + pts(R) + " pts)."))
                            LB.push(label.new(t1, sH.get(s) - R, nm + " from the high · " + pts(R), xloc = xloc.bar_time, style = label.style_label_left, color = #00000000, textcolor = cPj, size = size.tiny, tooltip = "If " + SN.get(s) + "'s high is in, its low would sit here at the forecast's " + nm + " range (" + pts(R) + " pts)."))
                LB.push(label.new(t0, sH.get(s), SN.get(s) + " · p50 " + pts(r50) + (r50 > 0 ? " · " + str.tostring(math.round(100 * rg / r50)) + "% used" : ""), xloc = xloc.bar_time, style = label.style_label_lower_left, color = #00000000, textcolor = cPj, size = tSz, tooltip = tipF))
            if showCrd
                string st = live ? "live " + pts(rg) : started ? "done " + pts(rg) + (rg > r90 ? " >p90" : rg < r10 ? " <p10" : "") : "at " + str.substring(ST.get(s), 0, 5)
                cRow(s + 1, SN.get(s) + " " + ST.get(s), started ? gauge(rg / r90, layI == "Mobile" ? 6 : 10) : "", cPj, pts(r50) + " · " + pts(r25) + "–" + pts(r75), st, tipF + (started ? "" : "\nNot started: provisional, from what is known now; fixed at " + str.substring(ST.get(s), 0, 5) + "."))
    if showCrd and layI != "Mobile"
        bool eC = evType(1)
        bool eN = evType(2)
        bool eF = evType(3)
        string evTx = eF ? "FOMC 14:00" : eC and eN ? "CPI + NFP 08:30" : eC ? "CPI 08:30" : eN ? "NFP 08:30" : ""
        string evFx = eF ? "NY PM ×2.5 · NY AM −17%" : eN ? "Asia −8% · London −9% · NY AM +9%" : eC ? "Asia −10% · London −7%" : ""
        if evTx != ""
            cRow(5, "today", "", cPj, evTx, evFx, "Session ranges on release days against the same model without the release flags (fit 2018–24, errors clustered by day; same sign in 2018–24 and 2025–26 and on NQ, ES and RTY each):\nFOMC: NY PM +149% (t 12.8; 2025–26 +164%), NY AM −17% (t −7.4), London −16%, Asia −12%.\nNFP: Asia −8%, London −9%, NY AM +9%.\nCPI: Asia −10%, London −7% (NY AM +6%, t 1.8, did not pass).\nThe forecasts above already include this.")
        cRow(6, "inputs", "", cSub, "ATR " + pts(atrD), "VIX " + (na(vx) ? "—" : str.tostring(vx, "0.0")) + (vx20 > 0 ? " (" + str.tostring(100 * (vx / vx20 - 1), "+0;-0") + "% vs 20d)" : ""), "Daily ATR(14) of the prior days and the prior VIX close against its 20-day mean. A VIX 10% above its 20-day mean lifts the forecast range by about 9% in Asia and London and 5–6% in New York.")
        cRow(7, "tested", "", cSub, "bands 47–52%", "of 50", tipF)
'''
P = P.replace('__COEF__', coef).replace('__Q__', qs).replace('__EVD__', evd).replace('__EVT__', evt)
open('/home/claude/rj/Ryujin_Jakka.pine', 'w').write(P)
print('ok', P.count('\n'))
