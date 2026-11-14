"""Output board, SIGNAL half: the STM32H743 + USB3300 (optical processing, USB HS host to
the optical board on J4, FS device to the CM5 on J9), the pickup preamp, ADC, DAC, relay
and TRS jack (J5, J8), the 3V3 rails, and J11 (the brain board's enable / mode / button
lead). x1.

    py -3.12 elec/output_signal.py     # -> elec/out/output_signal.{net,board.json}

The circuit is output_board.py's; output_split.py says which half each part is on and why.
"""
import output_split

if __name__ == "__main__":
    output_split.main("signal")
