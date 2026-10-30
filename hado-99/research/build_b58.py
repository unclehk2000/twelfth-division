"""Bakudō 58 v3 = the macro card (B58_v2_macro.pine) + the fractal module (fm_module.pine)."""
S = open('/home/claude/xa/B58_v2_macro.pine').read()
M = open('/home/claude/xa/fm_module.pine').read()
def rep(a, b, n=1):
    global S
    assert S.count(a) == n, (S.count(a), a[:90]); S = S.replace(a, b)
rep('indicator("Bakudō 58 · Macro Link", "Bakudō 58", overlay = true)',
    'indicator("Bakudō 58 · Macro Link + Fractal", "Bakudō 58", overlay = true, max_lines_count = 500, max_labels_count = 500, max_boxes_count = 100)')
rep('''// Which macro force the index is moving with today''', '''// Two parts. MACRO: which macro force the index is moving with today''')
rep('''// what to watch, and how much of today's move is the dollar and oil.
''', '''// what to watch, and how much of today's move is the dollar and oil.
// FRACTAL: the C2 → C3 model on the chart (see its section below), with odds tested the same way.
''')
rep('''cardSzI  = input.string("Small", "Card text", options = ["Tiny", "Small", "Normal"], group = g_V, display = display.none)
''', '''cardSzI  = input.string("Small", "Card text", options = ["Tiny", "Small", "Normal"], group = g_V, display = display.none)
cardShow = input.string("Both", "Card shows", options = ["Both", "Fractal", "Macro"], group = g_V, display = display.none)
''')
rep('''alertOn = input.bool(true, "Alert when the regime changes", group = g_R, tooltip = "Create one alert on \\"Any alert() function call\\".", display = display.none)
''', '''alertOn = input.bool(true, "Alert when the regime changes", group = g_R, tooltip = "Create one alert on \\"Any alert() function call\\".", display = display.none)

var g_F = "Fractal model (C2 → C3)"
fmOn     = input.bool(true, "Fractal model", group = g_F, tooltip = "C2 sweeps the previous higher-timeframe candle's low (high) and closes back inside; C3 and C4 follow. Odds on the card are from NQ, ES and RTY 1-minute data 2018–26.", display = display.none)
fmPairI  = input.string("Auto", "Pair", options = ["Auto", "1m – 15m", "1H – 1D"], group = g_F, tooltip = "Auto: 15-minute candles on charts of 5 minutes or less, CME trading days (18:00–17:00 ET) on longer intraday charts. The odds were tested on a 1-minute chart with 15-minute candles and on a 1-hour chart with daily candles; other chart timeframes say \\"untested\\".", display = display.none)
fmKeep   = input.int(2, "Setups kept", minval = 1, maxval = 10, group = g_F, display = display.none)
fmPrev   = input.bool(true, "Preview candles", inline = "pv", group = g_F, display = display.none)
fmPrevN  = input.int(4, "", minval = 2, maxval = 8, inline = "pv", group = g_F, display = display.none)
fmOff    = input.int(12, "offset", minval = 1, maxval = 200, inline = "pv", group = g_F, tooltip = "Bars right of price; 12 clears the target labels. SB Map's session candles sit 15–65 bars right of price: use 70 or more to place these beyond them.", display = display.none)
fmCisdI  = input.bool(true, "CISD and early CISD", group = g_F, display = display.none)
fmEqI    = input.bool(true, "C2 equilibrium and T-spot", group = g_F, display = display.none)
fmProjI  = input.bool(true, "Projections (+1, +2, +2.5, +4, +4.5)", group = g_F, display = display.none)
fmProtI  = input.bool(true, "Protected swings", group = g_F, display = display.none)
fmBull   = input.color(#2962ff, "Bullish", inline = "fc", group = g_F, display = display.none)
fmBear   = input.color(#f23645, "Bearish", inline = "fc", group = g_F, display = display.none)
fmAlertI = input.bool(true, "Alerts: C2, CISD, protected swing", group = g_F, display = display.none)
''')
rep('''// ═══════════════════════════════════════════════════════════════════
// CARD
// ═══════════════════════════════════════════════════════════════════
''', M + '''
// ═══════════════════════════════════════════════════════════════════
// CARD
// ═══════════════════════════════════════════════════════════════════
''')
rep('TC := table.new(posOf(cardPos), 3, 10, border_width = 0, frame_width = 1, frame_color = color.gray)', 'TC := table.new(posOf(cardPos), 3, 16, border_width = 0, frame_width = 1, frame_color = color.gray)')
rep('TC.clear(0, 0, 2, 9)', 'TC.clear(0, 0, 2, 15)')
rep('TC.cell(0, 0, mob ? "MACRO" : "BAKUDŌ 58 · MACRO",', 'string hdr = not fmAct or cardShow == "Macro" ? "MACRO" : cardShow == "Fractal" ? "FRACTAL" : ""\n    TC.cell(0, 0, mob ? (hdr == "" ? "B58" : hdr) : "BAKUDŌ 58" + (hdr == "" ? "" : " · " + hdr),')
rep('''    color nc = na
    // what to watch
''', '''    color nc = na
    // fractal: the latest setup
    bool both = fmAct and cardShow == "Both" and not mob
    if both
        addRow(K, V, W, P, C, "§FRACTAL · " + fmNm, "", "", "C2 → C3 on " + fmNm + " candles" + (fmTest ? " (tested pair)" : " (untested on this chart timeframe)") + ". The macro regime made no difference to these odds.", nc)
    if fmAct and cardShow != "Macro"
        string tst = fmTest ? "NQ + ES + RTY 2018–26, " + (fmP == 0 ? "1-minute chart, 15-minute candles (248k C2s)" : "1-hour chart, daily candles (3,089 C2s)") + ": " : "Untested pair on this chart timeframe; the odds shown are from the " + (fmP == 0 ? "1m–15m" : "1H–1D") + " test. "
        if fss.size() == 0
            addRow(K, V, W, P, C, "C2", "waiting for a " + fmNm + " sweep and close back", "", "No C2 among the kept candles yet.", nc)
        else
            FS s = fss.last()
            bool  bl = s.bull
            color sc = bl ? fmBull : fmBear
            string hs = bl ? "high" : "low"
            int    pc = math.round(s.clv * 100)
            addRow(K, V, W, P, C, "C2", (bl ? "▲ " : "▼ ") + (mob ? "" : (bl ? "bull · " : "bear · ") + fmNm + " ") + hhmm(s.t2) + " · closed " + str.tostring(pc) + "% " + (bl ? "up" : "down"), s.phase == 3 ? "in C3" : s.phase == 4 ? "in C4" : "done", tst + "where C2 closes in its own range decides C3. Closing in the top quarter toward the trade, C3 took C2's " + hs + " on " + str.tostring(fmTake(3)) + "%; in the bottom quarter on " + str.tostring(fmTake(0)) + "%. Against other candles that closed in the same place, a C2 was no more likely to see it (the pattern adds nothing beyond its close).", sc)
            string c3v = s.took ? "✓ took " + (mob ? "" : "C2's ") + hs + " " + hhmm(s.tookT) : s.phase == 3 ? (s.eqHit ? (mob ? "at EQ · " : "back at EQ · ") : "") + (mob ? hs + " " : "takes C2's " + hs + " ") + str.tostring(s.eqHit ? fmTakeEq(s.q) : fmTake(s.q)) + "%" : "✗ didn't take C2's " + hs
            addRow(K, V, W, P, C, "C3", c3v, mob ? "" : pxF(s.opp), tst + "C3 took C2's " + hs + " by where C2 closed (quarters of its range): " + str.tostring(fmTake(0)) + " / " + str.tostring(fmTake(1)) + " / " + str.tostring(fmTake(2)) + " / " + str.tostring(fmTake(3)) + "%. After C3 trades back to C2's midpoint (EQ): " + str.tostring(fmTakeEq(0)) + " / " + str.tostring(fmTakeEq(1)) + " / " + str.tostring(fmTakeEq(2)) + " / " + str.tostring(fmTakeEq(3)) + "%. Steady in 2018–24 and 2025–26 and on each symbol.", s.took ? sc : nc)
            string lv = s.dead ? "✗ taken " + hhmm(s.deadT) : s.phase == 3 ? "holds through C3 " + str.tostring(fmHold(s.q)) + "%" : "held"
            addRow(K, V, W, P, C, bl ? "C2 LOW" : "C2 HIGH", lv, pxF(s.ext), tst + "C2's swept " + (bl ? "low" : "high") + " held through C3 by where C2 closed: " + str.tostring(fmHold(0)) + " / " + str.tostring(fmHold(1)) + " / " + str.tostring(fmHold(2)) + " / " + str.tostring(fmHold(3)) + "%. That is " + (fmP == 0 ? "1.7" : "3.4") + " points more often than other candles' lows at the same close location, and " + (fmP == 0 ? "2.8" : "7.4") + " more when the CISD confirmed inside C2.", s.dead ? color.gray : nc)
            string cv = s.cisd ? "✓ " + (s.cisdC2 ? "in C2 (early)" : hhmm(s.cisdT)) : na(s.lvl) ? "—" : s.dead ? "✗ C2 broken first" : "waiting"
            addRow(K, V, W, P, C, "CISD", cv, pxF(s.lvl), "CISD: the highest open of the run of " + (bl ? "down" : "up") + "-closing bars that delivered C2's " + (bl ? "low" : "high") + " (up to 10 bars back), confirmed by the first close beyond it. " + tst + "it confirmed inside C2 on " + (fmP == 0 ? "66" : "74") + "% of C2s and by the end of C4 on " + (fmP == 0 ? "88" : "91") + "%. Once close location is accounted for, an early CISD does not raise the odds C3 takes C2's " + hs + ".", s.cisd ? sc : nc)
            if fmProjI and s.cisd and not na(s.pjHit)
                string tv = ""
                for [i, k] in PJ
                    if i < 4
                        tv += (tv == "" ? "" : " · ") + "+" + str.tostring(k) + (s.pjHit.get(i) ? " ✓" : fmTest ? " " + str.tostring(fmProj(i)) + "%" : "")
                addRow(K, V, W, P, C, "TARGETS", tv, "", tst + "after the CISD confirmed, price reached CISD + k × (CISD − C2's extreme) before C4 ended: +1 " + str.tostring(fmProj(0)) + "%, +2 " + str.tostring(fmProj(1)) + "%, +2.5 " + str.tostring(fmProj(2)) + "%, +4 " + str.tostring(fmProj(3)) + "%, +4.5 " + str.tostring(fmProj(4)) + "%. Steady in both periods and on each symbol.", nc)
            if fmProtI and s.cisd
                string pv = s.pDone ? (s.pTaken ? "✗ taken" : "holding " + pxF(s.pPx)) : s.dead ? "—" : "forming"
                string pw = not s.pDone or s.pTaken ? "" : s.phase == 0 ? "held" : fmP == 0 and fmTest ? "to C4 end " + str.tostring(fmProtHold(s.pLeft)) + "%" : "untested"
                addRow(K, V, W, P, C, "PROTECT", pv, pw, "Protected swing: after the CISD, the first " + (bl ? "down" : "up") + "-closing bar arms a level at its open (moved to the open of the run into each new " + (bl ? "low" : "high") + "); a close back beyond it marks the most extreme 3-bar swing in between. NQ + ES + RTY 2018–26, 1-minute chart, 15-minute candles: protected swings held to the end of C4 9.5 points more often than other 1-minute swings with the same bars left and distance (49% overall). By bars left in C4 when marked, ≤5 / 6–10 / 11–15 / 16–20 / 21+: 93 / 77 / 64 / 52 / 39%. Not tested on 1H–1D.", s.pDone and not s.pTaken ? sc : nc)
    // what to watch
''')
# macro rows only when the card shows them
i = S.index('    string wv = reg == 2 ? "DXY and CL, both against"')
j = S.index('    array<string> keep = mob ?')
block = S[i:j]
block = '    if both\n        addRow(K, V, W, P, C, "§MACRO", "", "", "The dollar and oil today, by regime.", nc)\n    if cardShow != "Fractal" or not fmAct\n' + '\n'.join(('    ' + l) if l.strip() else l for l in block.split('\n'))
S = S[:i] + block.rstrip(' ') + S[j:]
rep('''    array<string> keep = mob ? array.from("WATCH", "DXY", "OIL", "TODAY") : K''',
    '''    array<string> keep = mob ? (fmAct and cardShow != "Macro" ? array.from("C2", "C3", "CISD", cardShow == "Fractal" ? "PROTECT" : "WATCH") : array.from("WATCH", "DXY", "OIL", "TODAY")) : K''')
rep('if keep.includes(k) and r < 10', 'if keep.includes(k) and r < 16')
old = '''            color vc = C.get(i)
            TC.cell(0, r, k, text_color = cSub, text_size = cSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = fnt, tooltip = P.get(i))
            TC.cell(1, r, V.get(i), text_color = na(vc) ? cTxt : vc, text_size = cSz, text_halign = text.align_left, bgcolor = cBody, text_font_family = fnt, tooltip = P.get(i))
            TC.cell(2, r, W.get(i), text_color = na(vc) ? cTxt : vc, text_size = cSz, text_halign = text.align_right, bgcolor = cBody, text_font_family = fnt, tooltip = P.get(i))'''
new = '''            color vc = C.get(i)
            bool  sec = str.startswith(k, "§")
            color bg  = sec ? cSec : cBody
            TC.cell(0, r, sec ? str.replace_all(k, "§", "") : k, text_color = sec ? cTxt : cSub, text_size = cSz, text_halign = text.align_left, bgcolor = bg, text_font_family = fnt, tooltip = P.get(i))
            TC.cell(1, r, V.get(i), text_color = na(vc) ? cTxt : vc, text_size = cSz, text_halign = text.align_left, bgcolor = bg, text_font_family = fnt, tooltip = P.get(i))
            TC.cell(2, r, W.get(i), text_color = na(vc) ? cTxt : vc, text_size = cSz, text_halign = text.align_right, bgcolor = bg, text_font_family = fnt, tooltip = P.get(i))'''
rep(old, new)
rep('''cSub   = isDark ? #8a93a6 : #5d6476
''', '''cSub   = isDark ? #8a93a6 : #5d6476
cSec   = isDark ? #1f2430 : #e6eaf0
''')

# header: the regime colours it when the macro rows show; a neutral header when the card shows the fractal only
rep('''    TC.cell(0, 0, mob ? (hdr == "" ? "B58" : hdr) : "BAKUDŌ 58" + (hdr == "" ? "" : " · " + hdr), text_color = hdrTx(regC), bgcolor = regC,''',
    '''    bool  fOnly = hdr == "FRACTAL"
    color hC    = fOnly ? (isDark ? #2a2e39 : #c9ced8) : regC
    TC.cell(0, 0, mob ? (hdr == "" ? "B58" : hdr) : "BAKUDŌ 58" + (hdr == "" ? "" : " · " + hdr), text_color = hdrTx(hC), bgcolor = hC,''')
rep('''(mob ? "" : " ET"), text_color = hdrTx(regC), bgcolor = regC,''', '''(mob ? "" : " ET"), text_color = hdrTx(hC), bgcolor = hC,''')
rep('''    TC.cell(2, 0, regNm, text_color = regC, bgcolor = lumOf(regC) > 165 ? #131722 : #ffffff,''',
    '''    TC.cell(2, 0, fOnly ? fmNm + (fmTest ? "" : " · untested") : regNm, text_color = fOnly ? cTxt : regC, bgcolor = fOnly ? cBody : lumOf(regC) > 165 ? #131722 : #ffffff,''')
rep('    TC.set_frame_color(color.new(regC, 30))', '    TC.set_frame_color(color.new(hC, 30))')
# renamed Hadō 99 (16 Oct 2026)
S = S.replace('Bakudō 58', 'Hadō 99').replace('BAKUDŌ 58', 'HADŌ 99').replace('"B58"', '"H99"')
open('/home/claude/xa/Hado_99.pine', 'w').write(S)
print('ok', len(S.splitlines()))
