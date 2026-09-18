# PARKED: TRRS routing down the adjustable leg

**Parked 2026-09-16 by the user.** Not startable yet — it depends on the leg↔pedal-bar
TRRS joint, which is not built. Revisit once that joint exists.

## The problem

The leg is length-adjustable. The TRRS lead has to run its whole length, and it has to
survive the leg going from **maximum extension to minimum** without being crimped,
pinched or dragged. The user's framing:

> Ideally the TRRS cable could be sized such that the leg can be set to its maximum
> length, then you can adjust the leg down to the minimum length and the TRRS cable will
> cleanly shrink without getting crimped.

So the slack is not optional and it is not small: it is the **full adjustment range**,
and it has to be stored somewhere that does not foul the leg's own telescoping.

## The user's proposals

1. **A wrapping rod.** A rod inside the leg that the lead is wound tightly around to
   coil it. A coil takes up extension and retraction the way a retractable cord does,
   without a fixed bend anywhere.
2. **Buy a pre-wound (coiled) TRRS lead.** The user's own caveat: hard to find one with
   a trustworthy datasheet — and this project has been bitten twice already by parts
   whose real numbers were not published (both leg springs still carry a
   measure-on-arrival step for exactly that reason).

The user is explicitly open to other approaches.

## What is already known, and constrains the answer

* **The lead must be CONTINUOUS from the pedal bar to the top joint.** The user called
  this out when parking the prompt: the leg↔body blind-mate at the top is finished and
  its floating jack is fed by one lead down the leg. Whatever happens in the middle, the
  installation plan has to thread a single lead through both ends.
* **The coil is already threaded onto that lead** (`leg_trrs.SPR_ID` 6.6 clears the far
  plug's Ø6.1 overmould). That was not free — it is the reason the float spring is a
  second SKU, and it is the constraint that made an earlier version of the joint
  unbuildable. Any routing scheme that changes which moulded end goes where has to be
  re-checked against it.
* **Ø6.6 pass-through the whole tenon** (`leg_trrs.PASS_D`), sized so the lead's far
  moulded plug can travel the tenon's full length and out the bottom. A wrapping rod
  has to live somewhere that does not narrow that path.
* **The tenon's core is spoken for.** The latch pocket owns the tenon's −Y middle, and
  the signal spine already sits at (−1.6, +5.6) to clear it. A rod on the axis is not
  automatically available.
* A **jacketed Ø3.8 cable bends worse than bare leads** — the 90° fold at the top joint
  had to be moved into stripped 28 AWG for exactly this reason. Coiling a jacketed lead
  around a small rod is the same problem at a larger radius, and the minimum bend radius
  is the thing to establish first.

## Questions to answer when this is picked up

1. What IS the leg's adjustment range? The slack length falls straight out of it.
2. Minimum bend radius of the chosen lead — measured or datasheet, not assumed. This
   sets the rod's diameter, and the rod's diameter sets whether it fits at all.
3. Does the coil rotate, or does it breathe in place? A coil that has to rotate needs a
   bearing surface and will abrade the jacket; one that breathes does not.
4. Where does the rod anchor — the fixed tenon, the adjust tenon, or the sleeve? The
   answer decides whether the coil's ends move relative to each other.
5. A pre-wound lead is still worth pricing, if one can be found with real numbers.
