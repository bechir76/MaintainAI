---
doc_id: M-ETP-05
title: M-Series Motors - Electrical Test Procedure (Qualified Technicians Only)
filename: M-ETP-05_motor_electrical_tests.pdf
machine_type: motor
access_level: technician
revision: Rev. A, 2024
---

# M-Series Motors: Electrical Test Procedure

**Restricted document.** These tests use high DC voltages and live measurements. They may only be carried out by qualified electrical technicians authorised under the site electrical safety rules.

## 1. General requirements

- The motor must be isolated and locked out according to SOP-LOTO-001 for all tests except the live current measurement in section 5.
- Verify the absence of voltage at the motor terminals with a tested voltage detector before disconnecting the supply cables.
- Disconnect the supply cables and any surge capacitors, VFD outputs and PT100 sensor leads before applying a test voltage.
- Wear insulating gloves rated for the test voltage and keep other people out of the test area with barriers and a sign.

## 2. Insulation resistance test

Use an insulation tester (megger) with a test voltage of **1000 V DC** for motors rated 400 V.

1. Connect the tester between the three phases joined together and the motor frame (earth).
2. Apply the test voltage for **1 minute** and record the insulation resistance (IR) value at 1 minute.
3. Record the winding temperature. Correct the reading to 40 °C: the insulation resistance halves for every 10 °C increase in temperature.

| Result (corrected to 40 °C) | Assessment |
|---|---|
| Above 100 MΩ | Good |
| 10 to 100 MΩ | Acceptable; trend at next test |
| Below 10 MΩ | Do not energise. Dry the winding and re-test |
| Below 1 MΩ | Do not energise. Winding repair required |

<!-- pagebreak -->

## 3. Polarization index (PI)

The polarization index is the ratio of the insulation resistance at 10 minutes to the resistance at 1 minute, measured with the same test voltage.

PI = IR(10 min) / IR(1 min)

| PI | Assessment for Class F insulation |
|---|---|
| Above 2.0 | Good |
| 1.0 to 2.0 | Questionable; moisture or contamination likely |
| Below 1.0 | Do not energise |

The PI test is not meaningful when the 1-minute insulation resistance is above 5000 MΩ.

### 3.1 Discharging the winding

After any insulation test the winding stores a dangerous charge. Short-circuit the winding to earth with the tester's discharge function or an earthing lead for **at least four times the test duration** (at least 40 minutes after a 10-minute PI test) before touching the terminals.

## 4. Winding resistance test

Measure the resistance of each phase with a low-resistance ohmmeter (4-wire method). Correct all values to the same temperature.

- The difference between the highest and lowest phase resistance must not exceed **2%** of the average.
- A higher difference indicates a shorted turn, a poor connection or a broken conductor.

<!-- pagebreak -->

## 5. Live current imbalance measurement

This measurement is made with the motor running and the terminal box covers closed where possible. Use a clamp meter rated CAT III 600 V or higher, measuring on the supply cables in the starter panel.

1. Measure the current in each of the three phases with the motor at normal load.
2. Calculate the current imbalance: the largest deviation from the average current, divided by the average current, times 100.
3. A current imbalance above **10%** requires investigation of the supply voltage balance, the connections and the winding.

## 6. Records

Record all results on the motor test sheet: date, motor ID, test voltage, IR at 1 and 10 minutes, PI, winding temperature, phase resistances and the name of the technician. Attach the sheet to the maintenance ticket. Compare results with the previous test: a fall in insulation resistance of more than 50% since the last test must be investigated even when the absolute value is acceptable.
