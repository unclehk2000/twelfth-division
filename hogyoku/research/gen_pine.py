import json
J = json.load(open('/home/claude/pdm/pine_params.json'))
f = lambda a: ', '.join(str(x) for x in a)
MK = ['nq', 'es', 'ym', 'rty']; SYMV = ['sNQ', 'sES', 'sYM', 'sRTY']; TFS = ['15', '60', '240', 'D']
req = []
for t, tf in enumerate(TFS):
    for k, m in enumerate(MK):
        v = f'{m}{t}'
        req.append(f'[{v}o1, {v}h1, {v}l1, {v}c1, {v}o2, {v}h2, {v}l2, {v}c2, {v}a, {v}t1, {v}t2] = request.security({SYMV[k]}, "{tf}", [open[2], high[2], low[2], close[2], open[1], high[1], low[1], close[1], ta.sma(high - low, 14)[2], time[2], time[1]], lookahead = barmerge.lookahead_on, ignore_invalid_symbol = true)')
        req.append(f'[{v}o3, {v}h3, {v}l3, {v}c3, {v}t3] = request.security({SYMV[k]}, "{tf}", [open, high, low, close, time], ignore_invalid_symbol = true)')
pack = []
for t in range(4):
    for k, m in enumerate(MK):
        v = f'{m}{t}'; i = t * 4 + k
        pack.append(f'put({i}, {v}o1, {v}h1, {v}l1, {v}c1, {v}o2, {v}h2, {v}l2, {v}c2, {v}a, {v}o3, {v}h3, {v}l3, {v}c3, {v}t1, {v}t2, {v}t3)')
P = r'''//@version=6
// This source code is subject to the terms of the Mozilla Public License 2.0 at https://mozilla.org/MPL/2.0/
// © Unclehk2000
// Hōgyoku · four-market HTF profiler. NQ, ES, YM and RTY on 15m, 1H, 4H and D at once: the price delivery matrix (each market's
// C2 against its C1: bull C2, bear C2, expansion, inside, outside), the four markets' C1-C2-C3 candles side by side, aligned on
// C1 so SMT and PSP show at a glance, the forming candle's reach odds (C3 through C2's / C1's high and low) with each market's own
// calibration, and the matrix readings that passed HYDRA against the drift. Built from scratch; the GXV HTF Profiler-PRO
// (Gregorius_XV & cdikici71, MPL-2.0; El3mentss rework) was studied for its concepts (C1-C2-C3, SMT, PSP) — none of its code is used.
// Tested on NQ, ES, YM, RTY 1-minute 2018 – Oct 2026 (fit 2018–24, scored 2025–26): the reach odds are off by 2–5 points on
// average; direction is mostly drift (the next candle closes up 51–53.5%); 15 of 72 matrix readings passed the suite's rule, worth
// 0.5–2.5 points each over the drift. Not affiliated with or endorsed by ICT or GXV.
indicator("Hōgyoku · Four-Market HTF Profiler", "Hōgyoku", overlay = true, max_lines_count = 160, max_labels_count = 80, max_boxes_count = 40)

// ═══════════════════════════════════════════════════════════════ Inputs
gV = "View"
themeI  = input.string("Auto", "Card theme", options = ["Auto", "Dark", "Light"], group = gV, display = display.none)
lblSzI  = input.string("Small", "Text size", options = ["Tiny", "Small", "Normal"], group = gV, display = display.none)
showCrd = input.bool(true, "Matrix card", group = gV, inline = "cd", display = display.none)
crdPos  = input.string("Top right", "", options = ["Top left", "Top center", "Top right", "Middle left", "Middle right", "Bottom left", "Bottom center", "Bottom right"], group = gV, inline = "cd", display = display.none)
layI    = input.string("Desktop", "Layout", options = ["Desktop", "Mobile"], group = gV, tooltip = "Desktop: the full matrix, the reach odds and the readings for every timeframe. Mobile: the profile timeframe only.", display = display.none)

gM = "Markets · individual sensitivity"
sNQ  = input.symbol("CME_MINI:NQ1!", "NQ", group = gM, inline = "m1", display = display.none)
tNQ  = input.int(0, "sweep ticks", minval = 0, maxval = 200, group = gM, inline = "m1", display = display.none)
sES  = input.symbol("CME_MINI:ES1!", "ES", group = gM, inline = "m2", display = display.none)
tES  = input.int(0, "sweep ticks", minval = 0, maxval = 200, group = gM, inline = "m2", display = display.none)
sYM  = input.symbol("CBOT_MINI:YM1!", "YM", group = gM, inline = "m3", display = display.none)
tYM  = input.int(0, "sweep ticks", minval = 0, maxval = 200, group = gM, inline = "m3", display = display.none)
sRTY = input.symbol("CME_MINI:RTY1!", "RTY", group = gM, inline = "m4", display = display.none)
tRTY = input.int(0, "sweep ticks", minval = 0, maxval = 200, group = gM, inline = "m4", display = display.none, tooltip = "How far C2 must trade beyond C1's high / low, in that market's ticks, to count as a sweep. The odds were tested at 0 (any trade beyond); at other settings the matrix still draws, but the readings say untested. Each market also carries its own fitted reach calibration.")

gT = "Timeframes"
on0 = input.bool(true, "15m", group = gT, inline = "t", display = display.none)
on1 = input.bool(true, "1H", group = gT, inline = "t", display = display.none)
on2 = input.bool(true, "4H", group = gT, inline = "t", display = display.none)
on3 = input.bool(true, "D", group = gT, inline = "t", display = display.none)
prfI = input.string("4H", "Profile candles", options = ["15m", "1H", "4H", "D", "Off"], group = gT, tooltip = "The four markets' C1-C2-C3 for this timeframe, drawn right of price and aligned on C1 (each market's C1 high and low land on the chart market's), so a sweep in one market and not another (SMT) or opposite candle colours (PSP) show at a glance.", display = display.none)
cUp  = input.color(#26a69a, "Up", group = gT, inline = "c", tooltip = "Matrix and Model candle colours; the chart market's own colour marks it in the matrix and the profile.", display = display.none)
cDn  = input.color(#ef5350, "Down", group = gT, inline = "c", display = display.none)
cHi  = input.color(#ab47bc, "Chart market", group = gT, inline = "c", display = display.none)

gP = "Profile candles (PO3) · as Hadō 99"
offI   = input.int(12, "Offset (bars right of price)", minval = 1, maxval = 300, group = gP, display = display.none)
pWI    = input.int(0, "Width", minval = 0, maxval = 30, inline = "pw", group = gP, display = display.none)
pGI    = input.int(0, "gap", minval = 0, maxval = 30, inline = "pw", group = gP, tooltip = "Each candle's width and the gap between candles, in chart bars. 0 = auto: 6 and 3 on 1–2 minute charts, 4 and 2 up to 5 minutes, 2 and 2 above. The four markets sit a double gap apart.", display = display.none)
pStyI  = input.string("Model (up / down)", "Colours", options = ["Model (up / down)", "ICT (green / black)", "Custom"], group = gP, tooltip = "Model: the up / down colours above, see-through bodies. ICT: green up bodies, black down bodies, black borders and wicks, as on ICT's charts (white instead of black on a dark chart). Custom: the six colours below, up then down. The same candle system as Hadō 99.", display = display.none)
bool pCu  = pStyI == "Custom"
bool pIct = pStyI == "ICT (green / black)"
pBdU   = input.color(#a5d6a7, "Body", inline = "pb", group = gP, active = pCu, display = display.none)
pBdD   = input.color(#2e2e2e, "", inline = "pb", group = gP, active = pCu, display = display.none)
pBrU   = input.color(#2e2e2e, "Border", inline = "pr", group = gP, active = pCu, display = display.none)
pBrD   = input.color(#2e2e2e, "", inline = "pr", group = gP, active = pCu, display = display.none)
pWkU   = input.color(#2e2e2e, "Wick", inline = "pk", group = gP, active = pCu, display = display.none)
pWkD   = input.color(#2e2e2e, "", inline = "pk", group = gP, active = pCu, display = display.none)
pWkW   = input.int(1, "Wick width", minval = 1, maxval = 4, group = gP, display = display.none)
pTagI  = input.bool(true, "C1–C3 tags", inline = "pt", group = gP, tooltip = "Tags: C1, C2 and the forming C3 under each market's candles. Times: each candle's open (day on D) under it. Countdown: the profile timeframe and the time left in C3, over the candles.", display = display.none)
pStmI  = input.bool(true, "Times", inline = "pt", group = gP, display = display.none)
pCdI   = input.bool(true, "Countdown", inline = "pt", group = gP, display = display.none)
pLivI  = input.bool(true, "Forming candle dashed", group = gP, tooltip = "C3, still forming, gets a dashed border.", display = display.none)

gA = "Alerts · create one with \"Any alert() function call\""
alR = input.bool(true, "A tested reading on the profile timeframe", group = gA, display = display.none)

// ═══════════════════════════════════════════════════════════════ Helpers
bgLum  = 0.299 * color.r(chart.bg_color) + 0.587 * color.g(chart.bg_color) + 0.114 * color.b(chart.bg_color)
isDark = themeI == "Dark" or (themeI == "Auto" and bgLum < 128)
cTxt   = isDark ? #d1d4dc : #131722
cBody  = isDark ? #161a23 : #f4f6f9
cSub   = isDark ? #8a93a6 : #5d6476
cHdr   = #7e57c2
tSz = lblSzI == "Tiny" ? size.tiny : lblSzI == "Normal" ? size.normal : size.small
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
pc(float v) => na(v) ? "—" : str.tostring(math.round(v * 100)) + "%"
sgn(float v) => v > 0 ? 1 : v < 0 ? -1 : 0
fgAuto = bgLum < 128 ? #d1d4dc : #131722
// profile candle colours (Hadō 99's system): part 0 body · 1 border · 2 wick
pCol(bool up, int part) =>
    color mc = up ? cUp : cDn
    part == 0 ? (pCu ? (up ? pBdU : pBdD) : pIct ? (up ? #a5d6a7 : fgAuto) : color.new(mc, 70)) : part == 1 ? (pCu ? (up ? pBrU : pBrD) : pIct ? fgAuto : color.new(mc, 30)) : (pCu ? (up ? pWkU : pWkD) : pIct ? fgAuto : color.new(mc, 30))
leftTx(int ms) =>
    int m = math.max(ms, 0)
    int dd = int(m / 86400000)
    int hh = int((m % 86400000) / 3600000)
    int mm = int((m % 3600000) / 60000)
    (dd > 0 ? str.tostring(dd) + "d " : "") + str.tostring(hh, "00") + "h " + str.tostring(mm, "00") + "m"
ncdf(float x) =>
    float t = 1.0 / (1.0 + 0.2316419 * math.abs(x))
    float d = 0.3989423 * math.exp(-x * x / 2.0)
    float p = d * t * (0.3193815 + t * (-0.3565638 + t * (1.781478 + t * (-1.821256 + t * 1.330274))))
    x > 0 ? 1.0 - p : p
lgt(float p) =>
    float q = math.max(1e-6, math.min(1 - 1e-6, p))
    math.log(q / (1 - q))
var array<string> MN = array.from("NQ", "ES", "YM", "RTY")
var array<string> TN = array.from("15m", "1H", "4H", "D")
var array<string> TFS = array.from("15", "60", "240", "D")
string rt = syminfo.root
int me = rt == "NQ" or rt == "MNQ" ? 0 : rt == "ES" or rt == "MES" ? 1 : rt == "YM" or rt == "MYM" ? 2 : rt == "RTY" or rt == "M2K" ? 3 : -1
onT(int t) => t == 0 ? on0 : t == 1 ? on1 : t == 2 ? on2 : on3
thrOf(int k) => k == 0 ? tNQ : k == 1 ? tES : k == 2 ? tYM : tRTY
bool sensDefault = tNQ == 0 and tES == 0 and tYM == 0 and tRTY == 0
// a timeframe below the chart's is not a higher timeframe here
validT(int t) => (t == 0 ? 900 : t == 1 ? 3600 : t == 2 ? 14400 : 86400) >= timeframe.in_seconds()

// ═══════════════════════════════════════════════════════════════ Tested parameters (fit 2018–24, scored 2025–26)
// reach: p = logistic(a + b·logit(2Φ(−d))), d = distance from C2's close to the level in C2's ATR (mean range of the 14 candles before);
// index ((tf · 4 + market) · 4 + level), levels C2 high, C2 low, C1 high, C1 low
var array<float> RA = array.from(__RA__)
var array<float> RB = array.from(__RB__)
// drift: the share of candles that closed up from the previous close, 2018–26, per (tf · 4 + market)
var array<float> BASE = array.from(__BASE__)
// the laggard / leader fifths of (own C2 return − the other three's mean), in ATR, per timeframe (2018–24)
var array<float> Q20 = array.from(__Q20__)
var array<float> Q80 = array.from(__Q80__)

// ═══════════════════════════════════════════════════════════════ The matrix: C1 = [2], C2 = [1] (completed), C3 forming
__REQ__
var array<float> O1 = array.new<float>(16, na)
var array<float> H1 = array.new<float>(16, na)
var array<float> L1 = array.new<float>(16, na)
var array<float> C1 = array.new<float>(16, na)
var array<float> O2 = array.new<float>(16, na)
var array<float> H2 = array.new<float>(16, na)
var array<float> L2 = array.new<float>(16, na)
var array<float> C2 = array.new<float>(16, na)
var array<float> AT = array.new<float>(16, na)
var array<float> O3 = array.new<float>(16, na)
var array<float> H3 = array.new<float>(16, na)
var array<float> L3 = array.new<float>(16, na)
var array<float> C3 = array.new<float>(16, na)
var array<int>   T1 = array.new<int>(16, na)
var array<int>   T2 = array.new<int>(16, na)
var array<int>   T3 = array.new<int>(16, na)
put(int i, float o1, float h1, float l1, float c1, float o2, float h2, float l2, float c2, float a, float o3, float h3, float l3, float c3, int t1, int t2, int t3) =>
    O1.set(i, o1), H1.set(i, h1), L1.set(i, l1), C1.set(i, c1), O2.set(i, o2), H2.set(i, h2), L2.set(i, l2), C2.set(i, c2), AT.set(i, a)
    O3.set(i, o3), H3.set(i, h3), L3.set(i, l3), C3.set(i, c3), T1.set(i, t1), T2.set(i, t2), T3.set(i, t3)
__PACK__
// formation of C2 against C1: 1 bull C2 (swept the low, closed back above it), 2 bear C2, 3 expansion up, 4 expansion down, 5 inside, 6 outside
sweptHi(int i) =>
    int k = i % 4
    H2.get(i) > H1.get(i) + thrOf(k) * (k == me ? syminfo.mintick : (k == 0 ? 0.25 : k == 1 ? 0.25 : k == 2 ? 1.0 : 0.1))
sweptLo(int i) =>
    int k = i % 4
    L2.get(i) < L1.get(i) - thrOf(k) * (k == me ? syminfo.mintick : (k == 0 ? 0.25 : k == 1 ? 0.25 : k == 2 ? 1.0 : 0.1))
formOf(int i) =>
    int f = 0
    if not na(C2.get(i)) and not na(H1.get(i))
        bool sh = sweptHi(i)
        bool sl = sweptLo(i)
        f := sl and not sh and C2.get(i) > L1.get(i) ? 1 : sh and not sl and C2.get(i) < H1.get(i) ? 2 : C2.get(i) > H1.get(i) ? 3 : C2.get(i) < L1.get(i) ? 4 : not sh and not sl ? 5 : 6
    f
glyph(int f) => f == 1 ? "▲ C2" : f == 2 ? "▼ C2" : f == 3 ? "⇧ exp" : f == 4 ? "⇩ exp" : f == 5 ? "◆ in" : f == 6 ? "✕ out" : "—"
glyphC(int f) => f == 1 or f == 3 ? cUp : f == 2 or f == 4 ? cDn : cSub
r2Of(int i) => AT.get(i) > 0 ? (C2.get(i) - C1.get(i)) / AT.get(i) : na
reachP(int t, int k, int lv, float d) =>
    int ix = (t * 4 + k) * 4 + lv
    d <= 0 ? 1.0 : 1.0 / (1.0 + math.exp(-(RA.get(ix) + RB.get(ix) * lgt(2.0 * ncdf(-d)))))

// the readings that passed HYDRA for the chart market on timeframe t: text and the C3-up excess (points over the drift) for this market
readings(int t) =>
    string s = ""
    float best = 0.0
    if me >= 0 and validT(t)
        int i = t * 4 + me
        int f = formOf(i)
        int nPlo = 0
        int nPhi = 0
        int nPbull = 0
        bool psp = false
        float pr2 = 0.0
        for k = 0 to 3
            if k != me
                int j = t * 4 + k
                nPlo += sweptLo(j) ? 1 : 0
                nPhi += sweptHi(j) ? 1 : 0
                nPbull += formOf(j) == 1 ? 1 : 0
                psp := psp or sgn(C2.get(j) - O2.get(j)) != sgn(C2.get(i) - O2.get(i))
                pr2 += r2Of(j) / 3.0
        float spr = r2Of(i) - pr2
        bool green = C2.get(i) > O2.get(i)
        bool red = C2.get(i) < O2.get(i)
        bool heldHi = not sweptHi(i) and nPhi >= 1
        if t == 0
            if f == 3
                float e = array.from(-1.6, -1.8, -2.5, -2.2).get(me)
                s += "⇧ exp → C3 up " + str.tostring(e, "+0.0;-0.0") + " · "
                best := e
            if f == 4
                float e = array.from(1.6, 1.9, 2.5, 2.2).get(me)
                s += "⇩ exp → C3 up " + str.tostring(e, "+0.0;-0.0") + " · "
                best := e
            if psp and green
                s += "PSP green " + str.tostring(array.from(-0.6, -0.7, -1.1, -0.9).get(me), "+0.0;-0.0") + " · "
            if psp and red
                s += "PSP red " + str.tostring(array.from(0.7, 1.4, 1.1, 1.3).get(me), "+0.0;-0.0") + " · "
            if spr <= Q20.get(0)
                s += "laggard " + str.tostring(array.from(0.3, 1.9, 0.8, 1.3).get(me), "+0.0;-0.0") + " · "
            if spr >= Q80.get(0)
                s += "leader " + str.tostring(array.from(-0.6, -1.1, -1.3, -1.5).get(me), "+0.0;-0.0") + " · "
            if heldHi
                s += "held high (partner swept) " + str.tostring(array.from(0.2, 0.8, 0.6, 0.4).get(me), "+0.0;-0.0") + " · "
        else if t == 1
            if f == 1 and nPbull == 3
                s += "all four ▲C2 " + str.tostring(array.from(2.1, 2.4, 1.7, 2.1).get(me), "+0.0;-0.0") + " · "
            else if f == 1 and nPlo == 3
                s += "▲C2, all four swept the low " + str.tostring(array.from(1.5, 1.7, 1.0, 1.4).get(me), "+0.0;-0.0") + " · "
            else if f == 1
                s += "▲C2 " + str.tostring(array.from(1.4, 1.8, 1.4, 0.3).get(me), "+0.0;-0.0") + " · "
            if f == 3
                s += "⇧ exp " + str.tostring(array.from(-1.6, -1.4, -2.0, -2.1).get(me), "+0.0;-0.0") + " · "
            if heldHi
                s += "held high (partner swept) " + str.tostring(array.from(0.8, 1.8, 0.8, 0.7).get(me), "+0.0;-0.0") + " · "
            if psp and red
                s += "PSP red " + str.tostring(array.from(1.0, 1.4, 0.7, 1.1).get(me), "+0.0;-0.0") + " · "
            if spr <= Q20.get(1)
                s += "laggard " + str.tostring(array.from(0.5, 1.8, 0.9, 0.7).get(me), "+0.0;-0.0") + " · "
        else if t == 2
            if f == 1 and nPlo < 3
                s += "▲C2 + SMT " + str.tostring(array.from(2.0, 3.4, 1.4, 3.1).get(me), "+0.0;-0.0") + " · "
    [s == "" ? "" : str.substring(s, 0, str.length(s) - 3), best]

// ═══════════════════════════════════════════════════════════════ Profile candles (four markets, aligned on C1)
int prf = prfI == "15m" ? 0 : prfI == "1H" ? 1 : prfI == "4H" ? 2 : prfI == "D" ? 3 : -1
string prfTF = prfI == "15m" ? "15" : prfI == "1H" ? "60" : prfI == "4H" ? "240" : "D"
var array<line>  PL = array.new<line>()
var array<box>   PB = array.new<box>()
var array<label> PT = array.new<label>()
var table TC = na
tipT = "Tested on NQ, ES, YM and RTY 1-minute 2018 – Oct 2026: 1,973 aligned daily, 12,541 4H, 48,542 1H and 193,482 15m candles in all four markets. Fit 2018–24, scored 2025–26.\nReach: the forming candle (C3) through C2's high / low and C1's high / low, from the distance at C3's open in ATR, one calibration per market and timeframe (out-of-sample gain 85–227 millinats over the base rate; off by 2.3–2.5 points on average on 15m and 4H, 4.8 on 1H, timid above 65% there).\nDirection: the next candle closed up 51–53.5% of the time (the drift). Machine-learned own + cross-market models added nothing out of sample on 1H / 4H. 15 of 72 matrix readings passed the suite's rule (p < 0.05 clustered by day, the same sign in 2018–24 and 2025–26 and on all four markets), each worth 0.5–2.5 points over the drift; combined, they still add almost no out-of-sample skill. They are shown as tested context, not signals."
cRow(int r, string a, string b, color bc, string c, string tip) =>
    TC.cell(0, r, a, text_color = cSub, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.cell(1, r, b, text_color = bc, text_size = tSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = font.family_monospace, tooltip = tip)
    TC.merge_cells(1, r, 4, r)
string alMsg = ""
if barstate.islast
    while PL.size() > 0
        PL.pop().delete()
    while PT.size() > 0
        PT.pop().delete()
    while PB.size() > 0
        PB.pop().delete()
    if prf >= 0 and validT(prf)
        int a0 = prf * 4 + math.max(me, 0)
        float aH = H1.get(a0)
        float aL = L1.get(a0)
        if not na(aH) and aH > aL
            int tfS = timeframe.in_seconds()
            int w   = pWI > 0 ? pWI : tfS <= 120 ? 6 : tfS <= 300 ? 4 : 2
            int g   = pGI > 0 ? pGI : tfS <= 120 ? 3 : 2
            int gw  = 3 * (w + g) - g
            int x0  = bar_index + offI
            int xEnd = x0 + 4 * (gw + 2 * g) - 2 * g
            float topAll = aH
            string fmt = prf == 3 ? "EEE" : "HH:mm"
            for k = 0 to 3
                int i = prf * 4 + k
                float h1 = H1.get(i)
                float l1 = L1.get(i)
                if not na(h1) and h1 > l1
                    // map this market's prices so its C1 high / low land on the anchor's
                    float sc = (aH - aL) / (h1 - l1)
                    int xb = x0 + k * (gw + 2 * g)
                    float gTop = na
                    for c = 0 to 2
                        float o = c == 0 ? O1.get(i) : c == 1 ? O2.get(i) : O3.get(i)
                        float hh = c == 0 ? H1.get(i) : c == 1 ? H2.get(i) : H3.get(i)
                        float ll = c == 0 ? L1.get(i) : c == 1 ? L2.get(i) : L3.get(i)
                        float cc = c == 0 ? C1.get(i) : c == 1 ? C2.get(i) : C3.get(i)
                        int   tt = c == 0 ? T1.get(i) : c == 1 ? T2.get(i) : T3.get(i)
                        if not na(o)
                            float yo = aL + (o - l1) * sc
                            float yh = aL + (hh - l1) * sc
                            float yl = aL + (ll - l1) * sc
                            float yc = aL + (cc - l1) * sc
                            bool  up = cc >= o
                            float bt = math.max(yo, yc)
                            float bb = math.min(yo, yc)
                            int x1 = xb + c * (w + g)
                            int xm = x1 + int(w / 2)
                            // the wicks stop at the body, as in Hadō 99
                            if yh > bt
                                PL.push(line.new(xm, yh, xm, bt, color = pCol(up, 2), width = pWkW))
                            if yl < bb
                                PL.push(line.new(xm, bb, xm, yl, color = pCol(up, 2), width = pWkW))
                            PB.push(box.new(x1, bt, x1 + w, bt == bb ? bb - syminfo.mintick : bb, border_color = pCol(up, 1), bgcolor = pCol(up, 0), border_style = c == 2 and pLivI ? line.style_dashed : line.style_solid))
                            string tg = pTagI ? (c == 0 ? "C1" : c == 1 ? "C2" : "C3") : ""
                            string tm = pStmI and not na(tt) ? str.format_time(prf == 3 ? tt + 6 * 3600000 : tt, fmt, "America/New_York") : ""
                            string dn = tm + (tm != "" and tg != "" ? "\n" : "") + tg
                            if dn != ""
                                PT.push(label.new(xm, yl, dn, style = label.style_label_up, color = #00000000, textcolor = cSub, size = size.tiny))
                            gTop := na(gTop) ? yh : math.max(gTop, yh)
                    int f = formOf(i)
                    topAll := math.max(topAll, nz(gTop, aH))
                    PT.push(label.new(xb + int(gw / 2), nz(gTop, aH), MN.get(k) + " " + glyph(f), style = label.style_label_down, color = #00000000, textcolor = k == me ? cHi : glyphC(f), size = tSz, tooltip = MN.get(k) + " " + TN.get(prf) + ": C1 → C2 " + glyph(f) + (sweptHi(i) ? " · swept C1's high" : "") + (sweptLo(i) ? " · swept C1's low" : "") + "\nCandles scaled so C1's high and low match the chart market's."))
            PL.push(line.new(x0 - 2, aH, xEnd + 2, aH, color = color.new(cSub, 30), style = line.style_dotted))
            PL.push(line.new(x0 - 2, aL, xEnd + 2, aL, color = color.new(cSub, 30), style = line.style_dotted))
            PT.push(label.new(xEnd + 2, aH, "C1 high", style = label.style_label_left, color = #00000000, textcolor = cSub, size = size.tiny))
            PT.push(label.new(xEnd + 2, aL, "C1 low", style = label.style_label_left, color = #00000000, textcolor = cSub, size = size.tiny))
            if pCdI
                int tcl = time_close(prfTF)
                PT.push(label.new(int((x0 + xEnd) / 2), topAll + (aH - aL) * 0.18, TN.get(prf) + " · " + leftTx(na(tcl) ? 0 : tcl - (barstate.isrealtime ? timenow : time_close)), style = label.style_label_down, color = #00000000, textcolor = fgAuto, size = size.tiny, tooltip = "Time left in the forming " + TN.get(prf) + " candle (C3)."))
    if showCrd
        if not na(TC)
            TC.delete()
        TC := table.new(posOf(crdPos), 5, 16, border_width = 0, frame_width = 1, frame_color = cHdr)
        bool mob = layI == "Mobile"
        TC.cell(0, 0, "HŌGYOKU", text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
        int col = 1
        for t = 0 to 3
            if onT(t) and (not mob or t == prf)
                TC.cell(col, 0, TN.get(t), text_color = #ffffff, bgcolor = cHdr, text_size = tSz, text_halign = text.align_center, text_font_family = font.family_monospace)
                col += 1
        for k = 0 to 3
            TC.cell(0, k + 1, MN.get(k) + (k == me ? " ◂" : ""), text_color = k == me ? cHi : cTxt, bgcolor = cBody, text_size = tSz, text_halign = text.align_left, text_font_family = font.family_monospace)
            int cc = 1
            for t = 0 to 3
                if onT(t) and (not mob or t == prf)
                    int i = t * 4 + k
                    int f = validT(t) ? formOf(i) : 0
                    float cl = H1.get(i) > L1.get(i) ? (C2.get(i) - L1.get(i)) / (H1.get(i) - L1.get(i)) : na
                    TC.cell(cc, k + 1, glyph(f), text_color = glyphC(f), bgcolor = cBody, text_size = tSz, text_halign = text.align_center, text_font_family = font.family_monospace, tooltip = MN.get(k) + " " + TN.get(t) + ": " + glyph(f) + (validT(t) ? (sweptHi(i) ? " · swept C1's high" : "") + (sweptLo(i) ? " · swept C1's low" : "") + "\nC2 closed at " + pc(cl) + " of C1's range · C2 move " + str.tostring(r2Of(i), "+0.00;-0.00") + " ATR" : "\nBelow the chart's timeframe."))
                    cc += 1
        int r = 5
        if me >= 0
            for t = 0 to 3
                if onT(t) and validT(t) and (not mob or t == prf)
                    int i = t * 4 + me
                    float a = AT.get(i)
                    if a > 0 and not na(C2.get(i))
                        float c2 = C2.get(i)
                        string rs = ""
                        for lv = 0 to 3
                            float lvl = lv == 0 ? H2.get(i) : lv == 1 ? L2.get(i) : lv == 2 ? H1.get(i) : L1.get(i)
                            float d = lv == 0 or lv == 2 ? (lvl - c2) / a : (c2 - lvl) / a
                            bool hit = lv == 0 or lv == 2 ? H3.get(i) > lvl : L3.get(i) < lvl
                            string nm = lv == 0 ? "C2H " : lv == 1 ? "C2L " : lv == 2 ? "C1H " : "C1L "
                            rs += nm + (d <= 0 ? "thru" : pc(reachP(t, me, lv, d))) + (hit and d > 0 ? "✓" : "") + (lv < 3 ? " · " : "")
                        cRow(r, TN.get(t) + " C3 reach", rs, cTxt, "", "The forming " + TN.get(t) + " candle (C3) trading through C2's high / low and C1's high / low, from the distance at C3's open (fixed for the candle; ✓ = traded). " + MN.get(me) + "'s own calibration.\n" + tipT)
                        r += 1
                        [s, best] = readings(t)
                        float b = BASE.get(t * 4 + me)
                        cRow(r, TN.get(t) + " C3 up", "drift " + str.tostring(b, "0.0") + "%" + (s != "" ? (sensDefault ? " · " + s + " pts" : " · readings untested at this sweep setting") : " · no tested reading"), s != "" and sensDefault ? cHi : cSub, "", "The share of " + MN.get(me) + " " + TN.get(t) + " candles that closed up from the previous close (2018–26), and any matrix reading active now that passed the suite's rule, with its excess for " + MN.get(me) + " in points over that drift (each tested on its own).\n" + tipT)
                        r += 1
                        if t == prf and s != "" and alR and sensDefault
                            alMsg := MN.get(me) + " " + TN.get(t) + ": " + s
        else
            cRow(r, "chart", "not NQ / ES / YM / RTY: matrix only", cSub, "", tipT)
            r += 1
        if not mob
            cRow(r, "tested", "reach calibrated · direction ≈ drift · 15 / 72 readings passed", cSub, "", tipT)
// alert once per new profile candle
bool newPrf = prf >= 0 and timeframe.change(prfTF)
if alMsg != "" and newPrf and barstate.isrealtime
    alert("Hōgyoku · " + syminfo.ticker + " · " + alMsg, alert.freq_once_per_bar)
'''
P = P.replace('__RA__', f(J['RA'])).replace('__RB__', f(J['RB'])).replace('__BASE__', f(J['BASE'])).replace('__Q20__', f(J['Q20'])).replace('__Q80__', f(J['Q80']))
P = P.replace('__REQ__', '\n'.join(req)).replace('__PACK__', '\n'.join(pack))
open('/home/claude/pdm/Hogyoku.pine', 'w').write(P)
print('ok', P.count('\n'))
