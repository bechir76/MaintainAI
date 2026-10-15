---
doc_id: M-OM-03
title: M-Series Three-Phase Induction Motors - Operation Manual
filename: M-OM-03_motor_operation.pdf
machine_type: motor
access_level: viewer
revision: Rev. D, 2023
---

# M-Series Three-Phase Induction Motors

## 1. Scope

This manual covers installation and operation of M-Series totally enclosed fan cooled (TEFC) squirrel cage induction motors, frame sizes 160 to 225, for 400 V 50 Hz supply. Maintenance and troubleshooting are covered in M-MT-04. Electrical tests on windings are described in M-ETP-05, which is restricted to qualified electrical technicians.

## 2. Ratings

| Model | Power | Rated current at 400 V | Speed | Efficiency class |
|---|---|---|---|---|
| M-160L | 15 kW | 29 A | 1460 rpm | IE3 |
| M-200L | 30 kW | 56 A | 1475 rpm | IE3 |
| M-225M | 45 kW | 82 A | 1480 rpm | IE3 |

### 2.1 Common data

| Item | Value |
|---|---|
| Insulation class | F (155 °C) |
| Temperature rise | Class B (80 K) |
| Degree of protection | IP55 |
| Cooling method | IC411 (shaft-mounted fan) |
| Duty | S1 continuous |
| Ambient temperature | -20 to +40 °C |
| Altitude | up to 1000 m without derating |
| Winding protection | 3 x PT100 RTD in the stator winding |

### 2.2 Bearings

| Model | Drive end | Non-drive end |
|---|---|---|
| M-160L | 6309 C3 | 6209 C3 |
| M-200L | 6312 C3 | 6212 C3 |
| M-225M | 6313 C3 | 6213 C3 |

<!-- pagebreak -->

## 3. Installation

### 3.1 Mounting

- Mount the motor on a flat, rigid base. Check for soft foot before tightening the feet: maximum 0.05 mm.
- Leave a free space of at least one quarter of the frame height behind the fan cover so that cooling air can enter.
- Do not mount the motor where hot exhaust air from other equipment can be drawn into the fan.

### 3.2 Alignment

Align the motor to the driven machine within 0.05 mm parallel offset and 0.05 mm per 100 mm angular. Belt drives must be tensioned according to the belt manufacturer; excessive belt tension overloads the drive end bearing.

### 3.3 Electrical connection

- Connect according to the diagram inside the terminal box. 400 V supply: delta connection for these frame sizes.
- The cable must be sized for the rated current and the installation method. Earth the motor at the earth terminal in the terminal box and on the frame.
- Set the overload relay to the rated current on the nameplate. Do not set it higher to avoid nuisance trips; find the cause instead.
- Connect the PT100 winding sensors to the protection relay.

### 3.4 Starting

The motors are designed for direct-on-line (DOL), star-delta or variable frequency drive (VFD) starting. With DOL starting, the starting current is about 7 times rated current.

**Maximum number of starts:** 3 starts per hour, evenly spaced, or 2 consecutive starts from cold. Frequent starting is a common cause of winding overheating because each start heats the rotor and stator.

<!-- pagebreak -->

## 4. Operation and protection

### 4.1 Temperature monitoring

The stator winding temperature is measured by the PT100 sensors. Typical winding temperature at full load and 40 °C ambient is 110 to 120 °C.

| Winding temperature | Action |
|---|---|
| Up to 130 °C | Normal operation |
| 130 °C | Warning: check load and cooling |
| 145 °C | Alarm / trip: the protection relay stops the motor |

Insulation life halves for every 10 °C of operation above the rated temperature of the insulation class. Repeated operation above 145 °C causes premature winding failure.

### 4.2 Vibration limits

M-Series motors are classified as medium machines on rigid foundations. Overall vibration velocity on the bearing housings:

| Zone | Velocity (mm/s RMS) | Meaning |
|---|---|---|
| Good | below 1.8 | New or recently serviced machine |
| Acceptable | 1.8 to 2.8 | Unrestricted operation |
| Warning | 2.8 to 4.5 | Plan maintenance |
| Alarm | above 4.5 | Damage likely; investigate immediately |

### 4.3 Supply quality

- Voltage tolerance: +/-5% of rated voltage at rated frequency.
- Voltage imbalance between phases should not exceed **1%**. An imbalance of 1% can cause a current imbalance of 6 to 10% and extra heating of the winding. Above 1% the motor must be derated.
- Loss of one phase (single phasing) while running causes a rapid rise in current and temperature; the overload relay must trip within seconds.

### 4.4 Current

The running current at full load must not exceed the rated current on the nameplate. A sustained current above 105% of rated current is a warning; above 115% the overload relay will trip.

<!-- pagebreak -->

## 5. Lubrication

The M-Series motors from frame 200 have regreasable bearings with grease nipples on both end shields. Frame 160 motors have sealed-for-life bearings.

### 5.1 Regreasing intervals at 1500 rpm

| Bearing | Grease quantity | Interval |
|---|---|---|
| 6312 C3 | 20 g | 4,500 h |
| 6212 C3 | 13 g | 6,000 h |
| 6313 C3 | 25 g | 4,000 h |
| 6213 C3 | 15 g | 5,500 h |

- Halve the interval for ambient temperatures above 40 °C or for vertical mounting.
- Use a polyurea or lithium complex grease, NLGI 2 or 3. The factory grease is a polyurea grease; check compatibility before changing grease type.
- Regrease with the motor running. Open the grease outlet plug and let the excess grease escape for about 1 hour before closing it.

### 5.2 Storage

If a motor is stored for more than 3 months, rotate the shaft by hand every month to prevent false brinelling of the bearings. Measure the insulation resistance before putting a stored motor into service (see M-ETP-05).
