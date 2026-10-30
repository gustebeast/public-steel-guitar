"""The ORDERED R1 boards keep their silk exactly as ordered (lead ruling, 2026-10-29).

cadkit's labeller now lays an INK BLEED under every outline-font text (kicad_silk.INK_BLEED)
so the instrument's face clears the fab's 0.15 mm minimum stroke -- measured without it at
0.1299 mm in 'A' at size 1.5 (quality A12). Every unordered or R2 board takes the fix. A
board already ordered is frozen: re-finishing it must reproduce the files that were sent,
so it lays no bleed, and A12's ink finding is waived on it with the reason. The lettering
on those boards is cosmetic; a broken 'A' does not change a connection.

Call as_ordered(BOARD_NOTES) just before a board writes its notes, on the R1 path only.
Its R2 drops the call."""

WHY = ("ordered R1, frozen as sent (lead, 2026-10-29): the face's 'A' inks 0.130 mm at 1.5 "
       "against 0.15, cosmetic on this board. R2 boards lay cadkit's ink bleed instead")


def as_ordered(notes):
    notes["silk_ink_bleed"] = 0.0
    notes.setdefault("quality", {}).setdefault("waive", {})["A12:silk outline-font ink"] = WHY
    return notes
