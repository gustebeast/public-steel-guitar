# The volume pedal's latency budget, checked

**The user's target (2026-09-30):** "get the position info on the motor board, relay to
the pi, then relay to the output board in <50ms".

**Verdict: the budget holds with roughly 45 ms of slack, and every term that this
hardware controls is under 5 ms. The one term that can blow it is not hardware at all —
it is Linux userspace scheduling on the Pi.**

## The chain, term by term

| # | hop | time | where the number comes from |
|---|---|---|---|
| 1 | pedal sensor → CAN frame | **≤ 2.0 ms** | bus B's sensor boards sample at 500 Hz, so the worst case is a full sample period of quantisation |
| 2 | frame on the wire | **≈ 0.07 ms** | a 2-byte CAN frame is ~64 bits with stuffing; bus B runs **1 Mbps** (motor_ctrl.py: 500 kbps is over budget at 11 sensor boards, 1 Mbps sits at 39.6%) |
| 3 | arbitration wait | **< 1 ms** | 39.6% load against a 52% target. The headroom was bought for exactly this: CAN arbitrates by priority, and utilisation buys latency, not just throughput |
| 4 | motor board MCU → Pi | **≈ 1 ms** | USB interrupt endpoint at a 1 ms interval |
| 5 | **Pi userspace turnaround** | **1–10 ms typical, tens of ms under load** | ⚠ the only soft number in the table |
| 6 | Pi → output board MCU | **≈ 1 ms** | same, through the panel's hub |
| 7 | MCU → the gain pot | **0.16 ms** | 16 bits of bit-banged SPI at 100 kHz into the MCP4261 |
| 8 | pot wiper → audible | **0** | it is an **analog** attenuator. There is no sample, so there is no sample delay |

**Hardware total, excluding the Pi: ≈ 4.3 ms.** The remaining ~45 ms is all available to
term 5.

## What this means for the design

**⚠ TERM 8 IS WHY THE GAIN IS A DIGITAL POT AND NOT A MULTIPLY ON THE Pi.** A software
gain would add its own buffer's worth of latency *and* would not exist at all in the
direct mode, which is the mode whose entire purpose is that the Pi is not in the path.
The pot is set by a control message and then gets out of the way; the audio never meets
it as data.

**⚠ AND THE 500 Hz SAMPLE RATE IS THE BIGGEST HARDWARE TERM, not the bus.** Term 1 is
thirty times term 2. If the pedal ever feels laggy, the lever to pull is the sensor
board's sample rate, not the bitrate — and bus B has the capacity: 39.6% at 500 Hz means
a twelfth board sampling at 1 kHz still fits.

**⚠ THE RISK IS TERM 5 AND IT IS MITIGABLE WITHOUT NEW HARDWARE.** A volume-pedal packet
that waits behind the Pi's audio thread on a non-realtime scheduler is the one way to
miss 50 ms. It wants a small dedicated thread and an interrupt endpoint rather than
polling. Worth measuring on the real Pi before assuming it is fine — it is the only
number in this table that was not derived from a datasheet or a bus calculation.

**A note on what was NOT done.** The Pi hop could be removed by putting a CAN transceiver
on the output panel and letting it listen to bus B directly, which would take the whole
chain under 4 ms. That is a real option and it is NOT taken here, because it adds a part,
a connector and a bus stub to a board that currently has no CAN at all, to buy margin
against a budget that is already met four times over. Revisit it only if term 5 measures
badly on hardware.
