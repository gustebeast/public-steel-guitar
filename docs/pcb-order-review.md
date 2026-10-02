# PCB order review: what we would wish we had done (2026-10-02)

Asked by the user before the first full order, after seeing a friend's board with a
silkscreen label on every component. Ten routed boards were surveyed (optical, motor_ctrl,
output_panel, pi_cap, can_tee, lever_sensor, four leg pogo boards) against the usual
design-for-manufacture and design-for-bring-up lists and JLCPCB's own assembly pages.

## Found missing, and fixed

| gap | why it would have hurt | fix |
|---|---|---|
| **No board carried any text at all.** No name, no revision. | The four leg pogo boards are two mirror pairs; a top and a bottom were indistinguishable. A second order with changed copper could not be told from the first. | `elec/silk.py`: every board now prints its name and `r1`. Bump `REV` when copper changes on a re-order. |
| **Bare test pads had no labels.** | The bring-up guide says "probe SWCLK"; the board did not say which pad that was. | Each test pad is labelled with its net (`SWDIO`, `+3V3A`, `BOOT0`...) where there is room, its `TP` number where the net name will not fit. |
| **Connector pins had no legend.** | The harness is crimped by hand against these pins. | Each connector of 8 pins or fewer gets its pinout printed, on the back where the through-hole tails are. |
| **The fab's order number** would have been printed wherever the fab chose. | On the optical board that can be beside the sensors, which the design keeps free of ink on purpose. | Every fab package's `ORDER.txt` now says "Remove Mark", with three other order-form settings. |
| **Two parts on the output panel and one on the Pi cap had no part number in the order files**, so their packages did not build. | The order would have stopped at the upload. | MCP4261 and SN74LVC1G3157 sourced (codes were found 2026-10-01 but never entered); the Pi cap's 2x7 ribbon header is declared OPEN. |
| `fab.py` deleted the four pogo packages on every run. | They would have been missing from the order folder. | Fixed. |

Labels are searched for a free site and dropped when there is none; none moves copper, and
the DRC result of every board is identical before and after. What did not fit:
motor_ctrl TP3, lever_sensor TP4, output_panel J6's pinout, and on the 10 x 17 mm leg
boards everything but the name (plus one pinout on the male bottom board).

## Checked, and already in place

* **Placement rotation** (the classic way to lose a JLCPCB assembly run): each package
  carries `ROTATION-CHECK.txt`, the placements a rotation difference can damage.
* **ESD and surge**: TVS on both CAN buses, the 24 V rail on both boards that take it, the 5 V rail, every USB port
  and the panel jacks.
* **Programming access**: SWD pads on every MCU board, plus BOOT0 and NRST on the
  optical board.
* **Supply track widths**: measured and corrected 2026-10-01 (`elec/rail_resistance.py`).
* **CAD against fab data**: `cad_geom_check` compares outline, holes and part positions.

## Considered, and deliberately not done

* **A designator beside every part** (what the friend's board has). On the dense boards
  that is ink on pads, which the fab clips; JLCPCB places from the position file, not from
  ink. The designators are on the assembly-drawing layer. Worth it only for boards
  assembled or reworked by hand, and none of ours is.
* **Fiducials and tooling holes on each board.** JLCPCB adds its own on the rails for
  Economic assembly. Adding ours would grow the small boards for no gain.
* **Teardrops.** They add margin against drill wander at track-to-via joints. They also
  change copper on ten boards that are routed clean; not worth re-validating for a first
  order. A candidate for r2.

## Still open before ordering

* ONE part cannot be ordered assembled: the two internal USB-A sockets on the output panel
  (GCT USB1046, 3 in stock). The 1/4 in jack is back in stock (C368502) and the Pi cap's
  ribbon header is C22438113; both entered 2026-10-02. The UI board's end of that ribbon is
  still a 2.54 mm IDC header, which takes a different cable -- the two ends do not yet agree.
* MCP4261 had 96 in stock on 2026-10-01; the gold pogo target 210; S8B-XH-A 65 against
  100 needed.
* The leg boards' pogo pins overhang the board edge. The fab's rails must go on the other
  edges; say so in the order remark.
* The UI, fret and foot LED boards are not in this review.
