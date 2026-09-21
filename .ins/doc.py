p='src/electronics.py'; s=open(p,encoding='utf-8').read()
a=s.index("# -- the ledge the cradles hang from, in the FLAT tray frame")
b=s.index("NUT_KEEPOUT_Y1 = 33.0")
b=s.index("\n",b)+1
s=s[:a]+'''# -- where the cradles' columns start, in the FLAT tray frame -------------------------
# stand() maps this frame to the world as  world_x = local_z - 543.8, so:
RIB_LZ    = -87.5        # local z -> world x -631.3: just inside the endplate's own wall,
                         # which ends at -631 behind the Pi and -627 behind the controller
'''+s[b:]
a=s.index('''    AND EACH ONE NEEDS A WEB BACK TO THE ENDPLATE''')
b=s.index('''    """''',a)
s=s[:a]+'''    EACH ONE IS ATTACHED BY ITS OWN COLUMNS. The tray was a plate standing ~22 mm proud of
    the endplate's inboard face, and the first cradles fused at the tray's position attached
    to nothing -- the motor controller's came out a free-floating 18,121 mm3 lump, which the
    overlap gate cannot see (two solids that never touch do not interpenetrate). Every
    column here starts inside the endplate wall (RIB_LZ), and keyhead_endplate asserts the
    finished part is ONE solid.
'''+s[b:]
s=s.replace('''    Each board gets its own cradle, independent of the other: walls capture it in the
    plate's plane, pads carry it off the face, so the only way in or out is straight off
    the face -- and one M4 button beside the +Y edge closes that.''','''    Each board gets its own cradle, independent of the other: walls capture it in the
    plate's plane, a lip under its edge carries it off the face, so the only way in or out
    is straight off the face -- and one M4 button closes that (through the motor
    controller's mounting ear; beside the Pi's +Y edge, its holes being too small).''')
s=s.replace('''    open_edge is -Y for both''','''    The -Y side is open above the board for both''')
open(p,'w',encoding='utf-8').write(s)
p='src/keyhead_endplate.py'; s=open(p,encoding='utf-8').read()
s=s.replace('''Check electronics.LEDGE_L* against where this "
        "plate's material actually reaches."''','''Check electronics.RIB_LZ (where the columns start) "
        "against where this plate's wall actually is."''')
open(p,'w',encoding='utf-8').write(s)
