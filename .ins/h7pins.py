import re, sys
s = open(r'C:/Program Files/KiCad/10.0/share/kicad/symbols/MCU_ST_STM32H7.kicad_sym', encoding='utf-8').read()
i = s.index('(symbol "STM32H743IITx"')
j = s.find('\n\t(symbol "', i + 10)
blk = s[i:j]
# symbol may 'extends' another; resolve
m = re.search(r'\(extends "([^"]+)"\)', blk)
if m:
    i = s.index('(symbol "%s"' % m.group(1)); j = s.find('\n\t(symbol "', i + 10); blk = s[i:j]; print('extends', m.group(1))
pins = {}
for pm in re.finditer(r'\(pin \w+ \w+.*?\(name "([^"]+)".*?\(number "([^"]+)"(.*?)\n\t\t\t\)', blk, re.S):
    name, num, rest = pm.groups()
    alts = re.findall(r'\(alternate "([^"]+)"', rest)
    pins[int(num)] = (name, alts)
pat = sys.argv[1]
for n in sorted(pins):
    name, alts = pins[n]
    hit = [a for a in alts if re.search(pat, a)]
    if hit or re.search(pat, name): print(n, name, hit)
