"""Output board, POWER half: both USB-C PD inlets (AP33772S + switch + LM74700 ideal diode
each), VIN_BUS, the INA226 on the brain board's feed, J10 / J12 to the brain board, the data
switch U17 and J3 to the CM5's gadget port, and the 5 V buck. x1.

    py -3.12 elec/output_power.py      # -> elec/out/output_power.{net,board.json}

The circuit is output_board.py's; output_split.py says which half each part is on and why.
"""
import output_split

if __name__ == "__main__":
    output_split.main("power")
