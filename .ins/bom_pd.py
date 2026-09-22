p = 'BOM.md'
s = open(p, encoding='utf-8').read()


def rep(o, n):
    global s
    assert s.count(o) == 1, (o[:80], s.count(o))
    s = s.replace(o, n)


rep('''| Optical photodiode (VEMD4110X02) | ~$0.35 ea | **not on LCSC**; use **X01**, same filter, **$0.58 @100+** | +$4.6/board; ⚠ 72 in stock vs 200 needed |''',
    '''| Optical photodiode (VEMD4110X02) | ~$0.35 ea | **REPLACED 2026-09-21 by the Everlight `PD15-22B/TR8` (C161211), $0.067 @200, 11,271 in stock** — filtered, 940 nm peak, ~3× the photocurrent; the sensor triplet was redesigned around its 3.3 × 2.8 body | **−$10.3/board**; stock block CLEARED |''')
rep('''| 1 | U6 | MCU — **STM32H743IIT6**, 20× 16-bit ADC ch, USB OTG_HS via ULPI | LQFP176 | 26.00 × 26.00 × 1.60 |''',
    '''| 1 | U6 | MCU — **STM32H743IIT6**, 5 SAI TDM lanes from the audio ADCs, USB OTG_HS via ULPI (its own ADCs unused since 2026-09-21) | LQFP176 | 26.00 × 26.00 × 1.60 |
| 5 | U14–U18 | **audio ADC — TI `TLV320ADC3140IRTWT`** (C1852021), 4 ch each, one per quad, 192 kHz, differential AC-coupled against MID. Replaced the H743's own ADCs 2026-09-21: they were the noise floor (77 dB single-ended), and a delta-sigma converter also filters the op-amps' out-of-band noise and samples all 20 channels on one edge | WQFN-24 (RTW) | 4.00 × 4.00 × 0.80 |
| 45 | Cs11–Cs59 | ADC supply / reference bypass — per converter 1 µF + 100 nF (AVDD), 10 µF + 100 nF (AREG, DREG, IOVDD), 1 µF (VREF), TI SBAS993B Fig. 165 | 0402 | 1.00 × 0.50 × 0.55 |
| 40 | Ci11–Cm54 | ADC input coupling — **10 nF C0G**, INxP from each TIA, INxM from MID | 0402 | 1.00 × 0.50 × 0.55 |
| 5 | R50–R54 | I2C2 / I2C4 pull-ups 4k7 ×4, converter SHDNZ pull-down 100k | 0402 | 1.00 × 0.50 × 0.55 |''')
rep('''| 20 | PD1A–PD10B | PIN photodiode — **Vishay VEMD4110X01**, daylight filter (740–1040 nm) | 0805 (opto) | 2.00 × 1.25 × 0.85 |
| 5 | R1–R5 | LED current-set — **180R** (21 mA) nominal, plain strings | 0603 | 1.60 × 0.80 × 0.95 |
| 5 | R6–R10 | LED current-set — **180R** (21 mA) nominal, wound strings | 0603 | 1.60 × 0.80 × 0.95 |''',
    '''| 20 | PD1A–PD10B | PIN photodiode — **Everlight PD15-22B/TR8** (C161211), black-epoxy daylight filter (730–1100 nm, **peak 940 nm**), ±2.375 across the string. Was the VEMD4110X01 (95 in stock) until 2026-09-21 | 3.3 × 2.8 (4 pads) | 3.30 × 2.80 × 1.10 |
| 5 | R1–R5 | LED current-set — **180R** (21 mA) nominal, plain strings | 0402 | 1.00 × 0.50 × 0.55 |
| 5 | R6–R10 | LED current-set — **180R** (21 mA) nominal, wound strings | 0402 | 1.00 × 0.50 × 0.55 |''')
rep('''| 20 | Rf11–Rf54 | TIA feedback resistor — **4M7** nominal, tuned per string | 0402 | 1.00 × 0.50 × 0.55 |''',
    '''| 20 | Rf11–Rf54 | TIA feedback resistor — **1M** nominal (was 4M7), tuned per string — the TIA must now pass the 48 kHz emitter carrier | 0402 | 1.00 × 0.50 × 0.55 |''')
rep('''| 20 | Cf11–Cf54 | TIA feedback cap — **2.2 pF** C0G, 15.4 kHz pole | 0402 | 1.00 × 0.50 × 0.55 |''',
    '''| 20 | Cf11–Cf54 | TIA feedback cap — **1 pF** C0G, ~160 kHz pole (was 2.2 pF / 15.4 kHz) | 0402 | 1.00 × 0.50 × 0.55 |''')
rep('''| PD1A–PD10B | `VEMD4110X01` | C3211080 | 20 | **$11.60** | filtered ✓ · ⚠ 95 in stock 2026-09-17, 200 needed · **no substitute exists** |''',
    '''| PD1A–PD10B | `PD15-22B/TR8` | C161211 | 20 | **$1.33** | filtered ✓ · 11,271 in stock 2026-09-21 · replaced the VEMD4110X01 ($11.60, 95 in stock) |
| U14–U18 | `TLV320ADC3140IRTWT` | C1852021 | 5 | **$18.23** | 4-ch audio ADC ✓ · 306 in stock 2026-09-21 (the IRTWR reel C882863 is ~$1 less each but had 67) |''')
rep('''## Optical pickup PCB (per-string sensing + on-board audio→MIDI)
''', '''## Optical pickup PCB (per-string sensing + on-board audio→MIDI)

> **⚠ 2026-09-21 — detector and converter changed; parts of this section predate it.**
> * **Photodiode → Everlight `PD15-22B/TR8`** (C161211, $0.067, 11,271 in stock). The
>   VEMD4110X01 had 95 in stock against 20 per board and no 0805 substitute; the full
>   catalogue (802 photodiodes) has filtered parts in bigger packages, and the triplet was
>   redesigned around this one: detectors at ±2.375 across the string, apertures 7.6 wide.
>   Peak sensitivity 940 nm (the emitter's), ~3× the photocurrent.
> * **Converters → 5× TI `TLV320ADC3140`** ($18.23/board). The H743's own ADCs were the
>   noise floor (77 dB single-ended). The converters run at 192 kHz, the emitters are
>   square-waved at 48 kHz locked to the frame, and firmware demodulates (lock-in) — the
>   old LEDs-on/LEDs-off sampling needs a sampler, which a delta-sigma part is not.
> * **TIA: 1M / 1 pF** (was 4M7 / 2.2 pF), to pass the carrier. The photodiode is now wired
>   cathode-to-summing-node: the old anode-in wiring drove the output DOWN from a 0.33 V MID.
> * **Noise floor = the light itself** (photon shot noise, ~67 dB on the thinnest string
>   with pulsed emitters, no ambient). Ambient IR (sun, halogen) adds shot noise the filter
>   cannot remove; LED/fluorescent stage light is rejected. Net board cost ~+$8.40.
> Older text below that quotes 67/75 dB, 4M7, 96 kHz pulsing, or the VEMD part is history.
''')
open(p, 'w', encoding='utf-8').write(s)
print('bom ok')
