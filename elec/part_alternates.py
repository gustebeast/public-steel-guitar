"""cadkit M42, the project's half: maker lifecycle and a named alternate for every part chosen
by number (every value with an LCSC code in elec/fab.py), in ONE table.

Every generator calls stamp(notes) just before it writes <board>.board.json, so each board's
quality.alternates is this whole table. quality.py checks it against that board's own
<board>.order.json rows (cadkit/pcbflow/order_check.py) and reads an entry by value or by code.

An entry is "<lifecycle> (<source>, <date seen>); alternate: <part> -- <why it drops in>",
or "alternate: none -- <why>". An alternate is a fallback for the day a part goes away; it is
NOT an instruction to change the BOM. Lifecycle is what the maker or a distributor said on
the date given. Where a small maker publishes no lifecycle status, the entry says so instead
of guessing one.

⚠ CH340C IS WAIVED, NOT REPLACED (lead, 2026-11-10). JLC flags code C84681 as not sold, but
it still holds 97k in stock against about 3 per instrument, and R1 is already built on it.
So the order uses C84681 while stock lasts. The alternate below is the one to switch to when
the stock does run out.
"""

ALTERNATES = {
    "CH340C": (
        "JLC marks code C84681 'no longer manufactured' (2026-11-10; WCH publishes no "
        "lifecycle), yet the same part is still sold as LCSC C7464026, 1425 in stock; "
        "alternate: CH340B WCH C81010 (SOP-16, 4243 in stock) -- the same pinout on every pin "
        "the boards use (1 GND, 2 TXD, 3 RXD, 4 V3, 5/6 UD+/UD-, 13 DTR#, 14 RTS#, 16 VCC) "
        "and an internal clock like the C. The three pins that differ float on every board "
        "(optical U32, output_panel U17, motor_ctrl U7: pins 7, 8, 15): 7 becomes RST# with "
        "an internal pull-up, 8 is NC, and 15 becomes the TNOW output. It enumerates as the "
        "same 1a86:7523 with the ch341 driver on /dev/ttyUSB*, so publicbench.romflash "
        "(find_port, DTR/RTS via TIOCMSET) and the M43 USB-only flash path are unchanged. "
        "CH343G is not a drop-in (CDC-ACM /dev/ttyACM*, a different PID: romflash would "
        "change), CH340K is ESSOP-10, and CH340N is SOP-8 with no DTR#"),
    '1N4148WT':
        'no maker lifecycle found (JSMSEMI; JLC buyable, 1.05M, 2026-11-10); alternate: 1N4148WT-7 Diodes C83482 -- same-MPN SOD-523 switching diode',
    '2.54-2*20P':
        'no maker lifecycle published (BOOMELE; JLC buyable, 7573, 2026-11-10); alternate: 2541FV-2x20P-B HanElectricity C25503128 -- 2x20 2.54 mm THT female, 8.5 mm tall, gold, fits the Pi header',
    '2N7002':
        'no maker lifecycle found (JSCJ; Octopart lists no status, 2026-11-10); alternate: 2N7002,215 Nexperia C65189 -- the same SOT-23 G/S/D 60 V small-signal NMOS',
    '52271-2079':
        'Active (DigiKey, 2026-11-10); alternate: none -- no non-Molex 20-way 1.0 mm bottom-contact FFC socket with this land at LCSC',
    'AD8402ARZ10':
        "LAST TIME BUY (analog.com product page; Octopart EOL, 2026-11-10); alternate: none -- no other maker's dual 10k 256-step pot is pin-compatible in SOIC-14 (MCP42010's pinout differs, AD5262 is TSSOP-16). A design decision before the next order, not a waiver",
    'AO3400A':
        'Production (Octopart, 2026-11-10); alternate: AO3400A UMW C347475 -- same-MPN second source, SOT-23 30 V NMOS, same pinout',
    'AO3401A':
        'Production (Octopart, 2026-11-10); alternate: AO3401A UMW C347476 -- same-MPN second source, SOT-23 -30 V PMOS, same pinout',
    'AP2112K-3.3TRG1':
        'Active (DigiKey, 2026-11-10); alternate: AP2112K-3.3TRG1 TECH PUBLIC C23380830 -- same-MPN SOT-23-5 second source, 600 mA, VIN/GND/EN/NC/VOUT',
    'AP2114H-3.3TRG1':
        'Active (DigiKey, 2026-11-10); alternate: none -- no second-source 1 A LDO in SOT-223 with the GND/VOUT/VIN order at LCSC (AP2114HA swaps the pins; LM1117-3.3 fits them but drops about 1.2 V)',
    'B2B-XH-A':
        'Production (Octopart, 2026-11-10); alternate: XH-2A BOOMELE C20079 -- XH-compatible 2.5 mm top-entry header, same footprint, takes XHP housings',
    'B4B-PH-K-S':
        'Active (DigiKey, 2026-11-10); alternate: PH-4A HCTL C2908625 -- PH-compatible 4-way top-entry THT, takes PHR-4',
    'B4B-XH-A':
        'Production (Octopart, 2026-11-10); alternate: XH-4A BOOMELE C37815 -- XH-compatible 2.5 mm top-entry header, same footprint, takes XHP housings',
    'B6B-PH-K-S':
        'Active (DigiKey, 2026-11-10); alternate: PH-6A BOOMELE C33478 -- PH-compatible 6-way top-entry THT at 2.0 mm, takes PHR-6',
    'B6B-XH-A':
        'Production (Octopart, 2026-11-10); alternate: XH-6A BOOMELE C5663 -- XH-compatible 2.5 mm top-entry header, same footprint, takes XHP housings',
    'BLM18KG601SN1D':
        'Active (DigiKey, 2026-11-10); alternate: UPZ1608U601-1R3TF Sunlord C97000 -- 0603 600 Ohm at 100 MHz, 1.3 A, 150 mOhm',
    'BZT52C10T-7':
        'Active (DigiKey, 2026-11-10); alternate: BZT52C10T MDD C2993010 -- same-MPN 10 V SOD-523 zener from a second maker',
    'CH32V203C8T6':
        'no maker lifecycle published (WCH; JLC buyable, 9076, 2026-11-10); alternate: none -- CH32F103C8T6 / STM32F103C8T6 share the LQFP-48 pinout but are Arm cores: a firmware port, not a drop-in',
    'CH32V203G6U6':
        'no maker lifecycle published (WCH; JLC buyable, 6465, 2026-11-10); alternate: none -- CH32V203G8U6 C5187530 shares the pinout but is not sold, and no other maker has a pin-compatible QFN-28',
    'CH32V307WCU6':
        'no maker lifecycle published (WCH; LCSC sells it, 2026-11-10); alternate: none -- an MCU with its own QFN-68 pinout, and the firmware targets it',
    'CH334F':
        "no maker lifecycle published (WCH, 2026-11-10); alternate: none -- WCH's own QFN-24 hub pinout; the other CH334 variants are other packages",
    'CJO05-240003320B30':
        'no maker lifecycle found (JSCJ; Octopart lists no status, 2026-11-10); alternate: OT322524MJBA4SL YXC C717686 -- a 24 MHz 3225 4-pad CMOS oscillator with the standard OE/GND/OUT/VDD pinout; its supply code still to be confirmed as 3.3 V',
    'DSHP01TSGER':
        'no maker lifecycle published (kangshen; JLC buyable, 11942, 2026-11-10); alternate: DSHP01TSGER KE-SWITCH C5144960 -- the same MPN and recessed-slide SMD body, 24 V 25 mA',
    'DSS16':
        "no maker lifecycle found (FUXINSEMI; JLC buyable, 19378, 2026-11-10); alternate: SL16 Yangjie C698820 -- SOD-123 1 A 60 V Schottky, 550 mV at 1 A (lower than the DSS16's 700)",
    'ESD5B5.0ST1G':
        'Active (DigiKey, 2026-11-10); alternate: ESD5B5.0ST1G-P TECH PUBLIC C907831 -- same-MPN SOD-523 bidirectional 5 V ESD',
    'FRC2512F1R20TS':
        'no maker lifecycle published (FOJAN; JLC buyable, 7755, 2026-11-10); alternate: 25121WF120KT4E UNI-ROYAL C46193 -- 2512 1.2 Ohm 1 % 1 W thick film',
    'G6K-2F-Y-DC5':
        "Production (Octopart; C47190 is the tape-and-reel G6K-2F-Y-TR DC5, 2026-11-10); alternate: HFD4/5-SR Hongfa C64399 -- a 5 V DPDT 10x6.5 mm SMD signal relay sold as the G6K-class equivalent; its pad drawing still to be checked against the G6K's",
    'HX-TYPE-C 16P 180 LC-B H10.0':
        "no maker lifecycle published (hanxia; JLC buyable, 1701, 2026-11-10); alternate: none -- no other maker's vertical THT 16P USB-C with a 10.0 mm body at LCSC (hanxia's HX TYPE-C 16P LC H10.0 C25168811 is the nearest, footprint unchecked)",
    'INA226AIDGSR':
        'Active (ti.com, 2026-11-10); alternate: INA226AQDGSRQ1 TI C2653835 -- the AEC-Q100 grade of the same die, VSSOP-10 (0 at LCSC that day)',
    'JFC1206-1100FS':
        'no maker lifecycle published (JDT; JLC buyable, 29497, 2026-11-10); alternate: 0466001.NRHF Littelfuse C151135 -- 1206 fast 1 A 63 V, 50 A interrupt (rated to 90 C, not 125)',
    'JFC1206-1150FS':
        'no maker lifecycle published (JDT; JLC buyable, 6514, 2026-11-10); alternate: 046601.5NRHF Littelfuse C187598 -- 1206 fast 1.5 A 63 V, 50 A interrupt',
    'JFC1206-1200FS':
        'no maker lifecycle published (JDT; JLC buyable, 38766, 2026-11-10); alternate: 0466002.NRHF Littelfuse C3105 -- 1206 fast 2 A 63 V, 50 A interrupt',
    'JFC1206-1300FS':
        'no maker lifecycle published (JDT; JLC buyable, 31396, 2026-11-10); alternate: 0466003.NRHF Littelfuse C14165 -- 1206 fast 3 A, 50 A interrupt, rated 32 V (enough on a 24 V rail)',
    'JFC1206-1400FS':
        'no maker lifecycle published (JDT; JLC buyable, 36147, 2026-11-10); alternate: 0466004.NRHF Littelfuse C187596 -- 1206 fast 4 A, 50 A interrupt, rated 32 V (enough on a 24 V rail)',
    'KPJX-4S-S':
        "Production (Octopart, 2026-11-10); alternate: none -- Kycon's own 4-pin power DIN footprint and shell",
    'LESD5L5.0CT1G':
        'no maker lifecycle found (LRC; JLC buyable, 9202, 2026-11-10); alternate: TPESD5L5.0CT1G TECH PUBLIC C2827664 -- same-MPN SOD-523 5 V ESD second source',
    'LMR16006XDDCR':
        'Active (ti.com family page, orderable in stock, 2026-11-10); alternate: LMR16006XDDCR-MS MSKSEMI C54539952 -- same-MPN SOT-23-6 second source of the 0.7 MHz X grade (the Y grade is 2.1 MHz: not a drop-in)',
    'LMR33630ADDAR':
        'Active (ti.com, 2026-11-10); alternate: none -- the B / C grades run at 1.4 / 2.1 MHz instead of 400 kHz (inductor and compensation change), the 400 kHz Q1 grade is VQFN only, and there is no second source at JLC',
    'LMR33630BRNXR':
        'Active (ti.com, 2026-11-10); alternate: LMR33630BQRNXRQ1 TI C1850373 -- the Q1 grade, the same 1.4 MHz B option in the same RNX VQFN (0 at LCSC that day); LMR33630CRNXR C2071783 also sits on the land, at 2.1 MHz',
    'LMV331IDBVR':
        'Active (ti.com, 2026-11-10); alternate: LMV331W5-7 Diodes C107643 -- the same LMV331 SOT-23-5 open-collector comparator, 2.7-5.5 V',
    'LTE-C9901':
        'Production (Octopart, 2026-11-10); alternate: none -- no 0603 IR emitter with this footprint and a matched wavelength and angle at LCSC',
    'MA730GQ-Z':
        "Active (monolithicpower.com and DigiKey, 2026-11-10; 0 at JLC that day, 100 at the MPS store); alternate: MA732GQ-Z MPS C3824836 (2741 at JLC) -- the same 16-pin pinout, SPI/SSI/ABZ/PWM and 14-bit core; its filter window register FW (0x0E) defaults to 11.5 bit / 370 Hz, so firmware writes FW=187 for the MA730's 13.8 bit / 23 Hz. (MA702 is the same pinout at 12 bit; MA780 and MA600 are not pin-compatible)",
    'MCP4261-103E/ST':
        'Active (DigiKey; Microchip projects EOL 2036-07, 2026-11-10); alternate: MCP4251-103E/ST Microchip C637078 -- the same TSSOP-14 pinout, 10k dual 257-step; pin 11 WP becomes NC and the wipers are volatile, so firmware restores them at power-up (only 5 at JLC that day)',
    'MMBT3904':
        'no maker lifecycle found (JSCJ; JLC buyable, 4.3M, 2026-11-10); alternate: MMBT3904LT1G onsemi C81464 -- the standard SOT-23 NPN, same pinout',
    'MX126-5.0-02P':
        'no maker lifecycle published (MAX; JLC buyable, 11365, 2026-11-10); alternate: KF126-5.0-2P Cixi Kefa C474900 -- the same 126-style 5.0 mm 2P THT screw terminal, 18 A 250 V',
    'MX128-5.0-02P-Y':
        'no maker lifecycle published (MAX; LCSC C5188463, 2026-11-10); alternate: KF128-5.0-2P Cixi Kefa C474950 -- the generic 128-series 5.0 mm 2P PCB screw terminal, same footprint',
    'NMJ6HCD2':
        "Production (Octopart, 2026-11-10); alternate: none -- Neutrik's own jack footprint and panel cut-out",
    'NUP2105LT1G':
        'Active (DigiKey, 2026-11-10); alternate: PESD2CAN,215 Nexperia C75176 -- 24 V dual CAN-line TVS, SOT-23, two lines and a common pin 3',
    'PB-22E85-S-5.7C-C-W':
        'no maker lifecycle published (Legion; JLC buyable, 2422, 2026-11-10); alternate: PB-22E85PA-S-5.7A-C-W HOOYA C2939301 -- the same 8.5x8.5 DIP-6 self-locking body and 5.7 stem, but a rectangular plunger (cap fit to check) and 2.5 N instead of 1.8 N',
    'PCM1808PWR':
        'Active (ti.com, 2026-11-10); alternate: PCM1808QPWRQ1 TI C2864157 -- the automotive grade of the same part, TSSOP-14',
    'PCM5102APWR':
        'Active (ti.com, 2026-11-10); alternate: PCM5101APWR TI C2667024 -- pin-compatible family member, TSSOP-20, about 106 dB against 112',
    'PD15-22B/TR8':
        "Production (Octopart, 2026-11-10); alternate: CTMLPD15-22B CT Micro C55259952 -- a PD15-22B-style SMD 3.2x2.7 photodiode; its spectral response still to be checked against Everlight's",
    'PNR3015-150M':
        "no maker lifecycle published (APV; JLC buyable, only 878, 2026-11-10); alternate: none -- every other 15 uH 3x3 at LCSC saturates at 0.88 A or below, short of the 1.4 A the LMR16006's current limit needs",
    'PZ1.27-2x8P':
        'no maker lifecycle published (hanxia; JLC buyable, 1909, 2026-11-10); alternate: PZ1.27-2x8PWZ-L13.0-A SHOU HAN C55566475 -- the same 2x8 1.27 mm right-angle gold header; tail and row geometry to be checked against the drawing',
    'RK73B3ATTE2R0J':
        "Active (DigiKey, 2026-11-10); alternate: 25121WJ020JT4E UNI-ROYAL C25479 -- 2512 2 Ohm 5 % 1 W; KOA was chosen for its one-pulse curve, and this one's pulse rating is unchecked",
    'RKJXT1F42001':
        "Active (DigiKey, 2026-11-10); alternate: none -- ALPS only: no other maker's stick + encoder + push shares its footprint",
    'S4B-PH-K-S':
        "Active (DigiKey, 2026-11-10); alternate: PH-4AWD BOOMELE C49994 -- PH-compatible 4-way side-entry THT, 9.9 mm long like JST's, takes PHR-4",
    'S4B-PH-SM4-TB':
        'Active (DigiKey, 2026-11-10); alternate: HC-PH-4AWT HCTL C2845444 -- PH-compatible SMD right-angle 4-way, 12x5.5x8.65 against 11.9x5.5x8.6, takes PHR-4',
    'S4B-XH-A':
        'Active (DigiKey, 2026-11-10); alternate: XH-4AW HCTL C2908613 -- XH-compatible 4-way side-entry THT, takes XHP-4',
    'S4B-XH-SM4-TB':
        'Active (DigiKey, 2026-11-10); alternate: HC-XH-4AWT HCTL C2845685 -- XH-compatible SMD right-angle 4-way with tabs, body 10.5x15x6.1 against 10x15x6: land pattern to be checked against our footprint',
    'S4B-ZR-SM4A-TF':
        "Active (DigiKey, base part number, 2026-11-10); alternate: none -- no ZR-compatible SMD right-angle header from another maker at LCSC, and JST's S4B-ZR-SM2-TF C5306725 has a different body and pads",
    'S6B-PH-SM4-TB':
        'Active (DigiKey, 2026-11-10); alternate: HC-PH-6AWT HCTL C2845446 -- PH-compatible SMD right-angle 6-way, 16x5.5x8.65 against 15.9x5.5x8.6, takes PHR-6',
    'S8B-XH-A':
        "Active (DigiKey, 2026-11-10); alternate: XH-8AW HCTL C2908617 -- XH-compatible 8-way side-entry THT at 2.5 mm, takes JST's XHP-8 housing",
    'SMBJ5.0A':
        'Active (DigiKey, Littelfuse, 2026-11-10); alternate: SMBJ5.0A Brightking C78423 -- the industry-standard 5 V 600 W SMB unidirectional TVS',
    'SMCJ24A':
        'no maker lifecycle found (Brightking; JLC buyable, 5984, 2026-11-10); alternate: SMCJ24A Littelfuse C224045 -- the industry-standard 24 V 1500 W SMC TVS',
    'SMF24A':
        'no maker lifecycle found (Jingdao; JLC buyable, 97924, 2026-11-10); alternate: SMF24A Littelfuse C315999 -- the industry-standard 24 V 200 W SOD-123FL TVS',
    'SN65HVD230DR':
        'Active (ti.com, 2026-11-10); alternate: SN65HVD230DR-JSM JSMSEMI C46596299 -- same-MPN SOP-8 second source of the 3.3 V transceiver, same pinout',
    'SQD50P06-15L':
        'Production (Octopart, 2026-11-10); alternate: SUD50P06-15L-E3 Vishay C3290999 -- the industrial grade of the same -60 V P-channel in DPAK',
    'STM32H743IIT6':
        'Active (st.com, 2026-11-10); alternate: STM32H753IIT6 ST C146558 -- the same LQFP-176 pinout and firmware, plus crypto/hash (only 26 at LCSC that day)',
    'SWPA5040S4R7MT':
        'not confirmed (DigiKey lists only the +-30 % SWPA5040S4R7NT, Active; JLC buyable, 3983, 2026-11-10); alternate: FNR5040S4R7MT cjiang C167963 -- 5x5 shielded 4.7 uH +-20 %, Isat 3.8 A (over our 3.5 A minimum), Irms 3.3 A',
    'TAXM12M4RFBCCT2T':
        'no maker lifecycle published (Yajingxin; JLC buyable, 35061, 2026-11-10); alternate: X322512MOB4SI YXC C70565 -- 3225 4-pad 12 MHz, CL 12 pF, ESR 80 Ohm, tighter tolerance',
    'TAXM25M4RDBCCT2T':
        'no maker lifecycle published (Yajingxin; JLC buyable, 17992, 2026-11-10); alternate: X322525MMB4SI YXC C70582 -- 3225 4-pad 25 MHz, CL 10 pF, but ESR 50 Ohm against our 30 Ohm max: oscillator margin to re-check',
    'TAXM8M4RFDCET2T':
        'no maker lifecycle published (Yajingxin; JLC buyable, 58529, 2026-11-10); alternate: XXDCELNANF-8MHZ TAITIEN C367183 -- 3225 4-pad 8 MHz, CL 12 pF; its ESR is unlisted, to be confirmed at 250 Ohm or below',
    'TCAN3413DR':
        "Active (ti.com, 2026-11-10); alternate: TCAN3403DRQ1 TI C31086109 -- TI's automotive twin, same SOIC-8 pinout with VIO on pin 5, +-58 V bus (0 at JLC on 2026-11-10). NOT TCAN3414: its pin 5 is SHDN, and tied to VIO it sits in shutdown",
    'TLC5971RGER':
        'Active (ti.com, 2026-11-10); alternate: none -- TI is the only source, and the sibling TLC59711 is HTSSOP-20, not VQFN-24',
    'TLV320ADC3140IRTWT':
        'Active (ti.com, 2026-11-10); alternate: TLV320ADC5140IRTWR TI C2876368 -- pin-compatible family member in the same WQFN-24 4x4',
    'TLV9061IDBVR':
        'Active (ti.com, 2026-11-10); alternate: TLV9061QDBVRQ1 TI C22439604 -- the AEC-Q100 grade of the same part, SOT-23-5',
    'TLV9062IDGKR':
        'Active (ti.com, 2026-11-10); alternate: TLV9062QDGKRQ1 TI C4367989 -- the AEC-Q100 grade of the same part, VSSOP-8 (0 at LCSC that day)',
    'TPS2553DBVR':
        'Active (ti.com, 2026-11-10); alternate: TPS2553QDBVRQ1 TI C130055 -- the AEC-Q100 grade of the same part, SOT-23-6',
    'TPS7A2033PDBVR':
        'Active (ti.com, 2026-11-10); alternate: LP5907MFX-3.3/NOPB TI C80670 -- the same SOT-23-5 IN/GND/EN/NC/OUT pinout, a low-noise 3.3 V LDO, but 250 mA against 300: check the load',
    'TS3USB221ARSER':
        'Active (ti.com, 2026-11-10); alternate: TS3USB221ARSER-HXY HXY C49108275 -- same-MPN UQFN-10 1.5x2 second source (FSUSB42UMX is 1.4x1.8: a different land)',
    'TS3USB221RSER':
        'Active (ti.com, 2026-11-10); alternate: TS3USB221ARSER TI C128396 -- the pin-compatible A revision, the same UQFN-10 1.5x2',
    'TS5A3159DCKR':
        'Active (ti.com, 2026-11-10); alternate: TS5A3159ADCKR TI C475493 -- the pin-compatible A revision, the same SC-70-6',
    'TUSB320LAIRWBR':
        'Active (ti.com, 2026-11-10); alternate: TUSB320LIRWBR TI C2836598 -- the same family and X2QFN-12 pinout; LI vs LAI defaults still to be compared',
    'TYPE-C-31-M-12':
        "no maker lifecycle found (HRO; Octopart lists no status, 2026-11-10); alternate: none -- no other maker's 16P receptacle with a verified identical footprint at LCSC",
    'USB3300-EZK-TR':
        "Active (DigiKey, 2026-11-10); alternate: none -- the ULPI PHY pinout is the USB3300's own (USB3320 and similar differ)",
    'USBLC6-2SC6':
        'Active (st.com, 2026-11-10); alternate: USBLC6-2SC6 UMW C2687116 -- same-MPN second source, SOT-23-6, same pinout',
    'VLS6045EX-6R8M':
        "Active (DigiKey, 2026-11-10); alternate: none -- no 6x6 6.8 uH at LCSC reaches 4.7 A Isat; SWPA6045S6R8MT Sunlord C57254 (4.3 A) only if the 5 V buck's peak allows it",
    'WPN4020H4R7MT':
        'Active (DigiKey, 2026-11-10); alternate: CKCSA4020-4.7uH/M CENKER C354583 -- 4x4 shielded 4.7 uH +-20 %, Isat 4.0 A (our design point), Irms 2.85 A, 110 mOhm',
    'XL-5050RGBW':
        "no maker lifecycle published (XINGLIGHT; JLC buyable, 52409, 2026-11-10); alternate: HL-5050RGBW-S1 HONGLITRONIC C917441 -- 5050 8-pin RGBW with separate anodes and cathodes; its die-to-pin map to be checked against XINGLIGHT's before it counts",
    'YZ165615055F-04025-02':
        'no maker lifecycle published (Xinyangze; JLC buyable, 1467, 2026-11-10); alternate: none -- a right-angle 1x4 spring-pin header whose geometry is mated to the YZ185115035T target; no second source',
    'YZ185115035T-04025-01':
        'no maker lifecycle published (Xinyangze; JLC buyable, only 210, 2026-11-10); alternate: none -- its only family twin, C5296825, is right-angle and does not fit the adapter',
    'YZF0002-38080-02':
        'no maker lifecycle published (Xinyangze; JLC buyable, 486 = 30 instruments at 16, 2026-11-10); alternate: none -- no other side-mount SMD pogo with this barrel and land, and above 12 V, at LCSC',
}

WAIVE = {
    "M42:C84681": ("CH340C kept while stock lasts (lead, 2026-11-10): 97k in stock against "
                   "about 3 per instrument, and R1 is already built on it. The drop-in for when "
                   "it runs out is CH340B C81010 (quality.alternates)"),
}


def stamp(notes):
    """Put the table and the M42 waivers into a board's notes (before board.json is written)."""
    q = notes.setdefault("quality", {})
    q["alternates"] = dict(ALTERNATES)
    q.setdefault("waive", {}).update(WAIVE)
    return notes
