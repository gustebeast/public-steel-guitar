p='elec/motor_ctrl.py'; s=open(p,encoding='utf-8').read()
a=s.index("    # ── USB-C to the Pi ──")
b=s.index("    # ── 24 V -> 5 V FOR THE Pi, AND THE CROWBAR THAT MATTERS MORE")
new='''    # ── the link to the Pi: USB 2.0 on a top-entry XH, NOT a USB-C receptacle ──────
    # ⚠ THE USB-C COULD NOT BE PLUGGED IN (2026-09-21). It sat on the board's -Y edge with
    # its mouth facing the -Y rail, and standing on the keyhead endplate that edge is 5.5 mm
    # from the wall -- no USB-C plug, straight or right-angle, fits in front of it, let alone
    # goes in. Every other edge is as tight (9 mm to the deck, 10 to the floor, 8 to the Pi).
    # The only direction with room is straight off the board's face into the bay, which is
    # the direction every OTHER lead on this board already leaves by: a top-entry XH.
    # So the link is a stock USB-A -> 4-way XH lead (Amazon B0H9QTYT83), plugged into the
    # Pi's USB-A like the old cable was. XH is what every board-level connector in the
    # instrument is (user), the cable's crimps re-pin in the housing without solder if a
    # batch arrives in another order, and nothing here needed USB-C: no CC (a USB-A host has
    # none, so R8/R9 went with it), no orientation, and full speed is all the link uses.
    # Pin order is USB's own: 1 VBUS, 2 D-, 3 D+, 4 GND.
    # VBUS IS DELIBERATELY UNCONNECTED, as it was on the USB-C: the board runs off the 24 V
    # rail, and taking VBUS as well would leave the Pi's supply and the instrument's
    # arguing over who holds the rail. It is a landing for a future VBUS-present sense.
    usb = _xh("J4", "USB 2.0 link to the Pi (USB-A -> XH lead): VBUS n/c, D-, D+, GND")
    vbus = Net("VBUS_NC")
    vbus += usb[1]
    dm += usb[2]
    dp += usb[3]
    gnd += usb[4]
'''
s=s[:a]+new+s[b:]
s=s.replace('''USB_FP = "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12"\n''','')
s=s.replace('''        "R8": (-7.00, -24.00, 0.0),\n        "R9": (-10.00, -24.00, 0.0),\n''','')
open(p,'w',encoding='utf-8').write(s)
