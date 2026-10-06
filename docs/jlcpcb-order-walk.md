# JLCPCB order page: ten boards walked to the quote, 2026-10-06

Each package in `elec/out/fab/` was uploaded to JLCPCB's order page, assembly switched on,
its BOM and placement file loaded, the placement preview looked at and the quote read.
Nothing was added to the cart. Quantities are the form's 5 boards / 5 assembled unless a
line says otherwise, so every price below is FOR FIVE. The five lighting and UI boards
were walked separately (see `docs/pcb-quality-status.md`).

Footprint frames (the rotation and origin of each placement) come from the JLCEDA/EasyEDA
Official Library -- https://lceda.cn/ , https://easyeda.com -- read through the browser;
`elec/fab_frames.json` keeps only the rotation and offset measured from them.

## What the page showed, and what was done

| Finding | Boards | Done |
|---|---|---|
| Back-side parts previewed a half turn out | pi_cap | builder turns back-side placements half round; re-previewed correct |
| Two BOM rows with one part number: one row quantity 0, "unselected parts" | pi_cap, motor_ctrl, output_panel | builder writes one row per part number |
| Rows whose designators mix prefixes arrive unticked ("multiple types of parts") | optical (7 rows) | ORDER.txt lists the rows to tick; renaming does not clear it |
| Bottom-side assembly is Standard tier only | pi_cap | ORDER.txt says so; a cost item, see below |
| Black solder mask forces Standard tier (+8.00 colour) | optical | ORDER.txt says so; a cost item |
| Relay C326376 is "Standard only" | output_panel | ORDER.txt says so; a cost item |
| Parts with no fab model yet (+1 day, placeholder in preview) | optical R44 C5139521, pogo male C54799748 | ORDER.txt part note |
| 6.35 mm jack previewed 16 mm off its holes | output_panel | hand-entered frame; re-previewed in its outline |
| The form carried 19.87 of options into the next board | leg_pogo_male_bottom | already in ORDER.txt; seen live |
| Kycon KPJX-4S-S: the fab numbers pins 3 and 4 the other way round from our footprint | output_panel | closed 2026-10-06: our footprint is Kycon's land pattern pad for pad, and the fab's numbering is harmless (placed by position). The check found a real fault instead: the NETS followed Mean Well's pin numbers, which are not Kycon's, and shorted the supply. Netlist corrected, board re-routed |
| The 20 photodiodes, looked at zoomed in: every one was a half turn out. The fab's part has Everlight's numbering (lands 1 and 4 cathode, striped side); our footprint calls the anode pair 1, and the hand frame had matched by number | optical | closed 2026-10-06: frame turned half round (rot 270); re-previewed with the stripe on the summing-node lands, toward the op-amp |

## Totals for five of each (as designed today)

| Board | Tier | PCB | Assembly | Total | of which fees not parts |
|---|---|---|---|---|---|
| can_tee | Economic | 4.00 | 23.00 | 27.00 | setup 8.24, stencil 1.55, extended 3.09, hand-solder 3.61 |
| pi_cap | **Standard** (bottom side) | 8.00 | 71.73 | 79.73 | setup 25.75, stencil 8.27, loading 13.95, manual 5.02 |
| motor_ctrl | Economic | 8.00 | 126.28 | 134.28 | extended 55.62 (18 part types) |
| output_panel | **Standard** (relay) | 8.00 | 264.50 | 272.50 | setup 25.75, stencil 8.27, loading 79.05 |
| optical | **Standard** (black mask) | 41.30 | 355.82 | 397.12 | engineering 25.00, colour 8.00, setup 25.75, stencil 8.27, loading 66.65 |
| lever_sensor | Economic | 44.52 | 60.86 | 105.38 | 0.25 mm via 36.52, extended 24.72 |
| leg_pogo_male_bottom | Economic | 4.00 | 28.07 | 32.07 | setup 8.24, hand-solder 3.61 |
| leg_pogo_female_bottom | Economic | 4.00 | 24.47 | 28.47 | setup 8.24, extended 6.18 |
| leg_pogo_male_top | Economic | (as male_bottom) | | | walked to the preview |
| leg_pogo_female_top | Economic | (as female_bottom) | | | walked to the preview |

Shipping was quoted at 31.23 (DHL DDP) on a single small board and is not in these.

## Board by board

## can_tee  (qty 5 PCB / 5 PCBA; instrument needs 10)
detected 2 layer 16 x 49.5; BOM 4/4 matched, all selected; preview: J1, J2, SW1 on their pads, bodies on the silk outline
PCB 4.00 | PCBA 23.00 = setup 8.24, stencil 1.55, components(4) 4.51, extended fee 3.09, SMT 0.03, hand-solder 3.61, manual assembly 1.06, nitrogen reflow 0.91 | total 27.00
parts: J1 C157914 ext 0.8915 (5), J2 C157925 ext 0.6492 (6), R1 C22787 basic 0.0155, SW1 C3293141 ext 2.9510 (5)
notes: form opened with Deburring=Yes (+0.10) carried over; surface finish default HASL (with lead)

## pi_cap  (qty 5 / 5; needs 1) -- ALL PARTS ON THE BACK
detected 4 layer 34 x 56; Bottom-side assembly FORCES "Standard" PCBA (Economic is top-side only): setup 25.75 vs 8.24, stencil 8.27 vs 1.55, feeders loading fee 13.95, board padded to 70x70 with rails
BOM first pass: 13 rows, C307331 on two rows ("100nF" and "100nF/50V") -> one row qty 0 + "Project has unselected parts". FIXED in the builder (one row per part number): 12/12 confirmed
Preview first pass: every connector a half turn out (J3/J4 leads on the tab pads, J5 pins into the board). FIXED: back side = KiCad - frame + 180. Second pass: J1..J6, U1 all on their pads, mouths/pins off the board edge
PCB 8.00 | Standard PCBA 71.73 = setup 25.75, stencil 8.27, components(12) 14.03, feeders loading 13.95, SMT 0.60, hand-solder 3.61, manual assembly 5.02, packaging 0.50 | total 79.73
parts: C45783 basic 1.10(5) ; C98192 ext 1.05(11) ; C307331 basic 0.23(25) ; C52923 basic 0.21(20) ; C5124634 ext 1.64(5) ; C265405 ext 1.95(5) ; C161861 ext 3.48(10) ; C22438114 ext 0.96(5) ; C157925 ext 0.65(6) ; C163455 ext 0.05(30) ; C25897 ext 0.03(20) ; C55266 ext 2.69(5)

## motor_ctrl  (qty 5 / 5; needs 1)
detected 4 layer 55 x 61.8; BOM 35/35 confirmed, none unselected; preview: all connectors on their outlines, J2/J6 mouths off the +X edge, ICs on pads
FORM: opened with PCB build time "2-3 days $66.20" selected (not the free "3 days PCBA Only") -> PCB price showed 74.20. Free option makes it 8.00.
PCB 8.00 (+66.20 expedite as the form opened) | Economic PCBA 126.28 = setup 8.24, stencil 1.55, components(35) 51.86, EXTENDED FEE 55.62 (18 extended x 3.09), SMT 2.38, hand-solder 3.61, manual 2.11, nitrogen 0.91 | total 200.48 as opened, 134.28 without the expedite
parts (code|B/E|qty|$): C29823 B .84 ; C1548 B .04 ; C307331 B .73 ; C15850 B 1.30 ; C13585 B 3.98 ; C52923 B .11 ; C12891 B 1.73 ; C8598 B .14 ; C93623 E 25 .73 ; C5274293 E 20 .84 ; C148230 E 7 1.02 ; C83333 E 7 .78 ; C136343 E .39 ; C136349 E .58 ; C136347 E .54 ; C144395 E 11 .65 ; C265102 E 10 3.07 ; C144397 E 5 .46 ; C131334 E 6 .27 ; C131342 E 5 .36 ; C19634062 E 9 .67 ; C415364 E 6 .87 ; C25741 B .04 ; C2076806 E .12 ; C22787 B .02 ; C138027 E .03 ; C138058 E .06 ; C25744 B .12 ; C25897 E .03 ; C87080 E 5 2.86 ; C12084 E 10 5.25 ; C5142795 E 5 15.81 ; C841384 E 5 3.74 ; C55266 E 5 2.69 ; C403948 E 7 1.03

## output_panel  (qty 5 / 5; needs 1)
detected 4 layer 66 x 95.5; BOM 57/57 confirmed
K1 relay G6K-2F-Y C326376 is "Standard Only": arrives UNSELECTED under Economic; the page offers Switch to Standard PCBA (setup 25/side, board padded with 5 mm rails) or Do not place. Walked as Standard.
Preview first pass: J5 (6.35 jack, frame not measured) 16 mm off its holes -> hand frame (grid centre on centre); J6, U8(optical), PD15 also hand-fitted. Second pass: J5 in its outline, USB-C mouths off the edges, IC pin-1 dots on the silk marks.
"The system detects component that may be offset -- auto align?" dialog appears on entering the preview: Cancel (we place by our own frames).
CHECK: Kycon KPJX-4S-S -- the fab's footprint numbers pins 3 and 4 the other way round from ours. Confirm ours against the Kycon drawing before ordering.
PCB 8.00 | STANDARD PCBA 264.50 = setup 25.75, stencil 8.27, components(57) 138.50, FEEDERS LOADING 79.05, SMT 5.38, hand-solder 3.61, manual 2.52, packaging 0.51, nitrogen 0.91 | total 272.50
parts under Economic listing (code|B/E|$ for 5): C92775 E 5.41 ; C13585 B 1.33 ; C45783 B 2.20 ; C307331 B 1.27 ; C1548 B .08 ; C15850 B 3.58 ; C28323 B .80 ; C377773 B .53 ; C2987940 E .64 ; C52923 B .16 ; C170182 E 1.17 ; C1532 B .05 ; C8598 B .14 ; C5274293 E .84 ; C917006 E .21 ; C93623 E .44 ; C148230 E 1.02 ; C248313 E 1.52 ; C136343 E .39 ; C85833 E .36 ; C165948 E 3.71 ; C368502 E 16.66 ; C2875467 E 20.49 ; C144395 E .36 ; C5188434 E .40 ; C158012 E .24 ; C144397 E .46 ; C326376 E 9.39 (Standard only) ; C19634062 E .67 ; C20917 B .44 ; C3281500 E 5.41 ; C8545 B .09 ; C25905 B .05 ; C25076 B .01 ; C26083 B .01 ; C25741 B .11 ; C2076827 E .10 ; C25117 B .03 ; C25744 B .15 ; C25091 B .03 ; C190095 E .50 ; C25796 E .06 ; C25778 E .06 ; C25755 E .03 ; C25900 B .03 ; C21189 B .01 ; C5142795 E 15.81 ; C55513 E 3.50 ; C107671 E 7.22 ; C5187527 E 3.11 ; C87080 E 2.86 ; C51118 E .86 ; C185580 E 13.75 ; C398358 E 2.05 ; C46388 E 1.87 ; C403948 E 1.03 ; C133337 E .69

## optical  (qty 5 / 5; needs 1)
detected 4 layer 188.53 x 57.21 (over 100 mm: no special offer -> engineering fee 25.00 + board 8.30)
BLACK soldermask: +8.00 AND it forces Standard PCBA (with Green the form allows Economic; switching back to Black flips it to Standard)
BOM 43/43 matched, but SEVEN rows arrive with quantity 0, unticked, orange "!": "There may be multiple types of parts, but one type of part has been matched. Please check." They are the rows whose designators mix prefixes (C + Cd, Cf10A + Cf10B, Ci + Cm, PD10A + PD10B, R + Rs, Rf..A + Rf..B). Renaming the designators (CD1, PDA10 ...) did NOT clear it -- it is the mixed prefix, not the spelling. Ticking each row's box sets the quantity and price. (Rows: C307331, C52923, C325452, C22400107, C161211, C25744, C2076822.)
C5139521 (R44): "Footprints and models will be completed after the order paid ... adds one more day". Placeholder in the preview.
Preview: board renders; connectors J1/J2 at the edge, MCU and codecs on pads. Too small on screen to confirm the 20 photodiodes' polarity -- still to be looked at zoomed in (hand-entered frame).
PCB 41.30 = engineering 25.00, colour 8.00, board 8.30 | STANDARD PCBA 355.82 = setup 25.75, stencil 8.27, components(43) 245.26, FEEDERS LOADING 66.65, SMT 9.37, packaging 0.52 | total 397.12
big parts for 5: U14.. C1852021 (5 codecs/board) 100.43 ; U6 C89597 55.45 ; CI.. C22400107 (40 x 10nF C0G) 14.81 ; U13 C2071384 12.85 ; PD C161211 7.92 ; D LEDs C2683614 7.89 ; U21.. C398356 7.38 ; U7 C108383 7.28 ; R44 C5139521 3.22

## lever_sensor  (qty 5 / 5; needs 11 -> order 15)   [the 33.025 x 21.9 board with the tee's switch]
detected 4 layer 21.9 x 33.03; BOM 17/17 confirmed, none unselected; preview: every part on its pads, pin-1 dots on the silk marks, J1 mouth off the -X edge, SW1 on its lands with TERM beside it
0.25 mm via option: +16.60 via, +16.59 4-wire Kelvin (added by the form), +3.33 TG155 (added by the form) = 36.52 per order
PCB 44.52 = 8.00 + 3.33 + 16.59 + 16.60 | Economic PCBA 60.86 = setup 8.24, stencil 1.55, components(17) 24.40, EXTENDED FEE 24.72 (8 x 3.09), SMT 1.04, nitrogen 0.91 | total 105.38
parts for 5: C52923 B .11 ; C1548 B .04 ; C23733 B .08 ; C307331 B .27 ; C93623 E .44 ; C265121 E 2.26 ; C25744 B .02 ; C25079 B .02 ; C17168 B .01 ; C25900 B .03 ; C327251 E .06 ; C3293141 E 2.95 ; C51118 E .86 ; C12084 E 3.17 ; C5142280 E 3.58 ; C2913974 E 9.49 ; C403948 E 1.03

## leg_pogo_male_bottom  (qty 5 / 5)
detected 2 layer 19.3 x 13; BOM 2/2 confirmed, both ticked (the male pogo C54799748 is NOT the "unselected" one here); C54799748 has no fab model yet: placeholder in the preview, "adds one more day"
FORM CARRY-OVER seen live: opened with Material Type 3.31 and 4-Wire Kelvin Test 16.56 charged, left over from the lever sensor's 0.25 mm via order. Reset them (TG135, Kelvin No) -> PCB 4.00
Preview: J2 body off the top edge with its leads on the pads; pogo block on the bottom edge, pins off the board
PCB 4.00 (+19.87 carried over) | Economic PCBA 28.07 = setup 8.24, stencil 1.55, components(2) 10.21, extended fee 3.09, SMT 0.05, hand-solder 3.61, manual 0.41, nitrogen 0.91 | total 32.07 clean (51.94 as opened)
parts for 5: C54799748 E 8.67 ; C265102 E 1.53

## leg_pogo_female_bottom  (qty 5 / 5)
detected 2 layer 17.55 x 10; BOM 2/2 confirmed; opened with the same carried-over 19.86 (reset by hand: Kelvin No, TG135)
Preview: J2 body off the edge with its leads on the pads, the pad block beside it
PCB 4.00 | Economic PCBA 24.47 = setup 8.24, stencil 1.55, components(2) 7.50, extended fee 6.18, SMT 0.09, nitrogen 0.91 | total 28.47
parts for 5: C54930022 E 6.15 ; C485354 E 1.35

## leg_pogo_male_top, leg_pogo_female_top
the mirror images: 2/2 confirmed each, none unticked, previews the mirror of the two above (bodies off the board edge, leads on pads). Not taken to the quote.
