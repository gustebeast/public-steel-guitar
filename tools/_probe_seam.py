"""What clear board top is there at the seam, on EACH side separately?

The retraction in docs/fret-led.md 9.1 quotes one number -- "the seam bay is 10.40" --
against a 12.00 tip-to-tip span. But 12.00 is a SUM: sliding a pogo inboard retreats its
tip by the same amount, so the two pads stay 12.00 apart wherever they sit. The question
is not whether 12.00 fits between the combs; it is whether EACH board has room for a
4.50 mm pogo BODY at the place its pad would have to be.
"""
from src import fret_light as FL

BODY = 4.50          # C5203987 barrel length (datasheet YZF0002-38080-02)
WORK = 6.00          # its working height, pad face to tip


def main():
    walls = {}
    for panel in ("mid", "key"):
        xs = [x for _n, x in FL.fret_xs() if FL.panel_range(panel)[0] <= x <= FL.panel_range(panel)[1]]
        b = sorted(FL._boundaries(xs, *FL.panel_range(panel)))
        walls[panel] = b
        bx0, bx1 = FL.board_span(panel)
        print("%-4s board %9.2f .. %9.2f   comb walls %9.2f .. %9.2f  (%d walls)"
              % (panel, bx0, bx1, b[0], b[-1], len(b)))

    # the two facing ends: mid's -X end and key's +X end
    mid_b0 = FL.board_span("mid")[0]
    key_b1 = FL.board_span("key")[1]
    mid_wall = min(walls["mid"])          # mid's -X-most comb wall
    key_wall = max(walls["key"])          # key's +X-most comb wall
    half = FL.WALL / 2.0

    print("\nfacing ends:")
    print("  mid  board -X edge %9.2f   its -X-most wall %9.2f (face %9.2f)"
          % (mid_b0, mid_wall, mid_wall + half))
    print("  key  board +X edge %9.2f   its +X-most wall %9.2f (face %9.2f)"
          % (key_b1, key_wall, key_wall - half))

    mid_clear = (mid_wall - half) - mid_b0     # clear top on mid, wall face to board end
    key_clear = key_b1 - (key_wall + half)     # clear top on key
    print("\nCLEAR BOARD TOP at each facing end (what a 4.50 body needs):")
    print("  mid  %6.2f mm   %s" % (mid_clear, "OK" if mid_clear >= BODY else "TOO SHORT"))
    print("  key  %6.2f mm   %s" % (key_clear, "OK" if key_clear >= BODY else "TOO SHORT"))

    print("\nthe span the pads would need, 2 x %.2f = %.2f:" % (WORK, 2 * WORK))
    print("  key board edge %.2f to mid comb wall face %.2f = %.2f"
          % (key_b1, mid_wall + half, (mid_wall + half) - key_b1))

    if key_clear < BODY:
        need = BODY - key_clear
        print("\n  -> key is short by %.2f mm of clear top." % need)
        print("     Its +X-most wall sits at %.2f; moving it %.2f further -X gives the body room."
              % (key_wall, need))
        ks = sorted([x for _n, x in FL.fret_xs()
                     if FL.panel_range("key")[0] <= x <= FL.panel_range("key")[1]])
        print("     The cell that pays is the one outboard of fret x=%.2f; its neighbours"
              % ks[-1])
        print("     are %.2f apart, so it loses %.0f%% of its width."
              % (ks[-1] - ks[-2], 100.0 * need / (ks[-1] - ks[-2])))


if __name__ == "__main__":
    main()
