from collections import defaultdict
from skidl import Pin, Part, Alias, SchLib, SKIDL, TEMPLATE

from skidl.pin import pin_types

SKIDL_lib_version = '0.0.1'

can_tee = SchLib(tool=SKIDL).add_parts(*[
        Part(**{ 'name':'B4B-XH-A', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'B4B-XH-A'}), 'ref_prefix':'J', 'fplist':None, 'footprint':'Connector_JST:JST_XH_B4B-XH-A_1x04_P2.50mm_Vertical', 'keywords':None, 'description':'trunk in', 'datasheet':None, 'pins':[
            Pin(num='1',name='GND',func=pin_types.PASSIVE),
            Pin(num='2',name='V24',func=pin_types.PASSIVE),
            Pin(num='3',name='CAN_H',func=pin_types.PASSIVE),
            Pin(num='4',name='CAN_L',func=pin_types.PASSIVE)] }),
        Part(**{ 'name':'R', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'R'}), 'ref_prefix':'R', 'fplist':None, 'footprint':'Resistor_SMD:R_0603_1608Metric', 'keywords':None, 'description':'CAN termination, 1%', 'datasheet':None, 'pins':[
            Pin(num='1',func=pin_types.PASSIVE),
            Pin(num='2',func=pin_types.PASSIVE)] }),
        Part(**{ 'name':'SolderJumper_2_Open', 'dest':TEMPLATE, 'tool':SKIDL, 'aliases':Alias({'SolderJumper_2_Open'}), 'ref_prefix':'JP', 'fplist':None, 'footprint':'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm', 'keywords':None, 'description':'close on the LAST tee of each bus only', 'datasheet':None, 'pins':[
            Pin(num='1',func=pin_types.PASSIVE),
            Pin(num='2',func=pin_types.PASSIVE)] })])