# Bill of Materials — purchased parts

Sourcing for the bought parts (printed parts are built from `src/`). Links are
validated stock items where noted; the rest list the spec to source against.
See `electromechanical-pedal-steel-spec.md` §12 for the fuller cost estimate.

| Part | Spec | Qty | Source | Notes |
|------|------|-----|--------|-------|
| **Drive belt** | GT2 (2 mm pitch) open-ended, **5 mm wide** | ~6.5 m total (cut to length) | [Bulkman3D GT2 open belt](https://bulkman3d.com/product/gt000-gt0003/) | cut-to-length, ~$0.5–1.7/m; splice into loops with the printed belt-clamp. 3 mm was unsourceable; 6 mm too wide for the 9.5 mm pitch. |
| Drive motor | MKS SERVO42D (48 mm NEMA17, CAN, 14-bit encoder) | 10 | — | self-locking screw means it's off at rest |
| Leadscrew | Ø5 × 1 mm lead, single-start (self-locking) | 10 | — | vertical, ~53 mm |
| Leadscrew nut | round brass, Ø7 body / Ø9 flange | 10 | — | pressed into the carriage |
| Screw support | bushing or MR85 ball bearing, Ø5 × Ø8 | 10 | — | + thrust washer for the axial string pull |
| Locknut | M5, Ø8 | 10 | — | axial retainer on the screw end |
| Bridge bearing | ball bearing Ø3 bore × Ø8 OD | 10 | — | one per string, the 90° turn; on a shared Ø3 axle |
| Guide rod | Ø2.5 hardened steel | 10 | — | anti-rotation, ~28 mm |
| Far-end tuner | standard locking guitar tuner | 10 | — | hand-tension to set the taut regime |
| Fasteners | M3 (NEMA17 mounts), M2 (belt clamps) | — | — | |

Printed parts (no purchase): carriage, screw_rail, bridge_support, motor_bank,
belt_clamp, screw_pulley, motor_pulley — see `py -3.12 -m src.build --list`.
