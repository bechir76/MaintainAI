---
doc_id: SOP-LOTO-001
title: SOP-LOTO-001 - Lockout/Tagout Procedure
filename: SOP-LOTO-001_lockout_tagout.pdf
machine_type: general
access_level: viewer
revision: Rev. 6, 2025
---

# SOP-LOTO-001: Lockout/Tagout Procedure

## 1. Purpose

This procedure protects people from the unexpected start-up of machines and the release of hazardous energy during maintenance, cleaning, adjustment or repair. It applies to all pumps, motors, compressors and associated systems on site.

**No work may be done inside a guard, on rotating parts, on electrical connections or on pressurised parts unless the equipment is locked out according to this procedure.**

## 2. Definitions

- **Authorised person**: a person trained in this procedure who applies locks and tags and performs the work.
- **Affected person**: a person who operates or works near the equipment but does not perform the work.
- **Energy isolating device**: a device that physically prevents the transmission of energy, such as a main switch, a circuit breaker or a valve. Push buttons, emergency stops and control circuits are **not** energy isolating devices.
- **Personal lock**: a lock with a single key, issued to one authorised person and marked with that person's name.

## 3. Types of hazardous energy

| Energy | Examples on site |
|---|---|
| Electrical | Motor supply, control circuits, VFD capacitors |
| Mechanical | Rotating shafts, couplings, belts, flywheels, conveyor tension |
| Pneumatic | Compressed air in receivers, separator vessels and pipework |
| Hydraulic | Liquid under pressure in pump casings and pipework |
| Thermal | Hot liquids, hot oil, hot surfaces above 60 °C |
| Gravity | Raised loads, vertical conveyor sections |

## 4. Responsibilities

Supervisors make sure that the equipment-specific isolation list is available. Each authorised person applies their own personal lock and is responsible for their own safety. Nobody may work under another person's lock.

<!-- pagebreak -->

## 5. Lockout steps

1. **Prepare.** Identify all energy sources of the equipment using the isolation list. Get the locks, tags and test equipment you need.
2. **Notify.** Inform the affected persons and the control room that the equipment will be shut down and locked out.
3. **Shut down.** Stop the equipment with its normal stop control.
4. **Isolate.** Operate all energy isolating devices: open the main switch or circuit breaker, close the valves.
5. **Lock and tag.** Each authorised person applies a personal lock and a danger tag to every energy isolating device. The tag shows the name, the date and the reason for the lockout.
6. **Release stored energy.** Release or restrain all stored energy: release pressure (SOP-PRS-002), let rotating parts come to a complete stop, discharge capacitors, block parts that can move by gravity, and let hot parts cool down.
7. **Verify isolation.** Make sure nobody is exposed, then press the start button to confirm the equipment does not start. Test for absence of voltage at the work location with a tested voltage detector. Return the start control to the off position.
8. **Do the work.** Only now may the work begin.

> Verification (step 7) is mandatory. Most lockout accidents happen because the wrong isolator was locked or the equipment was fed from a second source.

<!-- pagebreak -->

## 6. Removing locks and restarting

1. Check that the work is complete, tools are removed and guards are refitted.
2. Make sure all persons are clear of the equipment.
3. Notify the affected persons and the control room that the equipment will be restarted.
4. Each authorised person removes **only their own lock and tag**.
5. Restore the energy and start the equipment according to the operating instructions.

### 6.1 Group lockout

When several people work on the same equipment, the lead authorised person locks the isolating devices and places the keys in a group lock box. Each member of the group applies a personal lock to the lock box before starting work and removes it when their work is finished.

### 6.2 Shift change

At a shift change the incoming authorised person applies their personal lock before the outgoing person removes theirs, so that the equipment is never without protection.

### 6.3 Removing a lock when the owner is absent

A lock may only be removed by the supervisor when the owner cannot be found, after:

- a documented attempt to contact the owner,
- a check that the equipment is safe to restart,
- informing the owner before they return to work.

<!-- pagebreak -->

## 7. Equipment-specific notes

### 7.1 Pumps (P-Series)

- Lock the motor circuit breaker in the off position.
- Close and lock the suction and discharge valves.
- Drain the pump casing and release the pressure according to SOP-PRS-002 before opening the pump.
- If the liquid was hotter than 60 °C, wait until the casing has cooled below 50 °C.

### 7.2 Motors (M-Series)

- Lock the motor supply circuit breaker or switch-disconnector.
- For motors on a variable frequency drive, wait at least **5 minutes** after isolation for the DC bus capacitors to discharge, then verify the absence of voltage.
- Restrain the driven machine if it can turn the motor (for example a fan driven by the wind or a conveyor with a load).

### 7.3 Compressors (C-Series)

- Stop the compressor with the stop button, not the emergency stop, and wait until the motor has stopped.
- Lock the main switch, close and lock the outlet isolation valve.
- Release the pressure according to SOP-PRS-002 and confirm 0 bar on the separator vessel gauge.
- The compressor can restart automatically when it is only stopped by the controller. A stopped compressor with a lit "automatic restart" indicator is **not** safe.

## 8. Training and audits

Authorised persons are trained before they apply locks and retrained every 3 years. Supervisors audit at least one lockout per month.
