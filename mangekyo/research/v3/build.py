S = open('/home/claude/em/Mangekyo_src.pine').read().split('\n')
L = lambda a, b: '\n'.join(S[a - 1:b])          # 1-based inclusive
blk_helpers = L(98, 116) + '\n' + L(118, 136)     # palette, posOf, decOf, px, pc0, f2, nCdf, lgs (dmy replaced)
blk_hol = L(155, 195)
blk_data = L(198, 245).replace('// time of the first candle (daily bar time = its 18:00 ET session start)', '// time of the first candle (bar time = its 18:00 ET session start)').replace('// ATR(14) at formation', '// ATR(14) at formation (daily or weekly)').replace('// the middle candle\'s volume / the 20 days before', '// the middle candle\'s volume / the 20 candles before').replace('// trading days since it formed', '// candles (days or weeks) since it formed')
blk_engine = L(251, 344).replace('g.age >= 60', 'g.age >= maxAge').replace('// 1. drop what has left the longest look back, and gaps closed beyond before the newest completed day', '// 1. drop what has left the longest look back, and gaps closed beyond before the newest completed candle').replace('// 2. the newest completed day against every gap formed before it', '// 2. the newest completed candle against every gap formed before it').replace('// 3. new gaps formed by the newest completed day', '// 3. new gaps formed by the newest completed candle')
blk_swing = L(346, 366).replace('// the last daily swing candle', '// the last swing candle').replace('swingDay()', 'swingBar()')
blk_pick = L(386, 411) + '\n' + L(413, 425)
assert 'engine(int srcId)' in blk_engine and 'gs\n' in blk_engine + '\n' and 'swingBar()' in blk_swing and 'insideNow(Gap g)' in blk_pick
NEW = open('/home/claude/mg3/new_parts.pine').read()
out = NEW.replace('//@@HELPERS@@', blk_helpers).replace('//@@HOLIDAYS@@', blk_hol).replace('//@@DATA@@', blk_data).replace('//@@ENGINE@@', blk_engine).replace('//@@SWING@@', blk_swing).replace('//@@PICK@@', blk_pick)
assert '//@@' not in out
open('/home/claude/mg3/Mangekyo.pine', 'w').write(out); print('ok', out.count('\n'))
