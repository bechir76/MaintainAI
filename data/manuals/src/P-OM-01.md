---
doc_id: P-OM-01
title: P-Series End-Suction Centrifugal Pumps - Installation and Operation Manual
filename: P-OM-01_pump_installation_operation.pdf
machine_type: pump
access_level: viewer
revision: Rev. C, 2024
---

# P-Series End-Suction Centrifugal Pumps

## 1. About this manual

This manual covers installation, commissioning and operation of P-Series single-stage end-suction centrifugal pumps. Maintenance intervals, fault tables and repair procedures are in the companion document P-MT-02 (Maintenance and Troubleshooting Guide).

Read this manual and the site safety procedures before working on the pump. Any work on a stopped pump requires isolation according to SOP-LOTO-001 (Lockout/Tagout). Work on pressurised pipework requires SOP-PRS-002 (Pressure Release).

## 2. Model designation

The model code gives the discharge nozzle and the nominal impeller diameter in millimetres. Example: **P-100/250** is a pump with a DN100 discharge flange and a 250 mm nominal impeller.

| Model | Discharge | Impeller | Typical motor |
|---|---|---|---|
| P-50/160 | DN50 | 160 mm | 5.5 kW |
| P-80/200 | DN80 | 200 mm | 15 kW |
| P-100/250 | DN100 | 250 mm | 30 kW |

## 3. Safety summary

- Never run the pump dry. The mechanical seal is lubricated by the pumped liquid and is destroyed within seconds of dry running.
- Never run the pump against a closed discharge valve for more than 30 seconds. The liquid in the casing heats up rapidly and can flash to steam.
- Keep the coupling guard fitted whenever the motor can be started.
- Surfaces can exceed 60 °C when pumping hot water. Wear gloves and allow the casing to cool before touching.
- Do not exceed the maximum casing pressure of 16 bar or the maximum liquid temperature of 90 °C.

<!-- pagebreak -->

## 4. Technical specifications

| Parameter | P-50/160 | P-80/200 | P-100/250 |
|---|---|---|---|
| Rated flow | 25 m3/h | 90 m3/h | 180 m3/h |
| Rated head | 32 m | 50 m | 62 m |
| Speed | 2950 rpm | 2950 rpm | 1475 rpm |
| Motor power | 5.5 kW | 15 kW | 30 kW |
| Motor rated current (400 V) | 10.5 A | 27 A | 54 A |
| Max casing pressure | 16 bar | 16 bar | 16 bar |
| Max liquid temperature | 90 °C | 90 °C | 90 °C |
| Minimum continuous flow | 30% of BEP | 30% of BEP | 30% of BEP |
| Drive end bearing | 6306 C3 | 6308 C3 | 6310 C3 |
| Non-drive end bearing | 6306 C3 | 6308 C3 | 6310 C3 |
| Bearing lubrication | Grease | Grease | Grease |
| Shaft seal | Mechanical seal, carbon / SiC, EPDM | same | same |
| Weight (pump only) | 48 kg | 112 kg | 205 kg |

### 4.1 Materials

Casing and impeller are grey cast iron EN-GJL-250 as standard. The shaft is stainless steel 1.4021. Wear rings are bronze and are replaceable on the casing side.

### 4.2 Standard duty point at site

On this site the P-Series pumps are sized for a nominal discharge pressure of **6.0 bar** at the rated flow. A sustained discharge pressure below 4.5 bar indicates a loss of performance (see section 8).

<!-- pagebreak -->

## 5. Installation

### 5.1 Foundation

Mount the baseplate on a rigid concrete foundation with a mass of at least three times the mass of the pump unit. Level the baseplate to within 0.2 mm/m before grouting. Tighten the foundation bolts after the grout has cured for at least 48 hours. Foundation bolt torque for M16 bolts is **140 N·m**.

### 5.2 Pipework

- Support suction and discharge pipes independently. The pump casing must never carry the weight of the pipework.
- Flange faces must be parallel and aligned before bolting. Pipe strain is a common cause of misalignment and high vibration.
- The suction pipe should be at least one size larger than the suction nozzle, with a straight length of at least 5 pipe diameters before the pump inlet.
- Use eccentric reducers on the suction side, flat side up, to avoid air pockets.

### 5.3 Suction conditions and NPSH

The available NPSH must exceed the required NPSH of the pump by a margin of at least **1.0 m** over the whole operating range. Insufficient margin causes cavitation, which is heard as a crackling or "gravel" noise and causes vibration and erosion of the impeller.

### 5.4 Shaft alignment

Align the pump and motor shafts with a laser or dial indicator system after the pipework is connected. Tolerances for the flexible coupling:

| Check | Tolerance |
|---|---|
| Parallel (offset) misalignment | 0.05 mm maximum |
| Angular misalignment | 0.05 mm per 100 mm maximum |
| Soft foot | 0.05 mm maximum |

Re-check the alignment after the first 24 hours of operation at operating temperature.

<!-- pagebreak -->

## 6. Commissioning

1. Check that the shaft turns freely by hand.
2. Check the bearing housings contain grease; pumps are delivered pre-greased.
3. Fill the pump and suction line completely with liquid and vent the casing through the vent plug on top of the casing.
4. Open the suction valve fully. Close the discharge valve.
5. Jog the motor briefly to check the direction of rotation against the arrow on the casing. Reverse rotation produces low head and can unscrew the impeller nut.
6. Start the motor and open the discharge valve slowly within 30 seconds.
7. Check the discharge pressure, motor current and noise. The motor current must not exceed the rated current on the nameplate.
8. Check the mechanical seal for leakage. A mechanical seal should show no visible leakage.

## 7. Normal operation

- Operate the pump between 70% and 110% of the best efficiency point (BEP) flow. Prolonged operation below the minimum continuous flow of 30% of BEP causes recirculation, overheating and vibration.
- Do not throttle the pump on the suction side. Control the flow with the discharge valve only.
- To stop the pump, close the discharge valve, then stop the motor. Close the suction valve if the pump will be isolated for maintenance.
- In freezing conditions drain the casing through the drain plug when the pump is out of service.

<!-- pagebreak -->

## 8. Operating limits and condition monitoring

The pump is monitored online by vibration, bearing temperature, discharge pressure and motor current sensors. Alarm limits follow the site standard CMS-001.

| Measurement | Normal | Warning | Alarm |
|---|---|---|---|
| Vibration, bearing housing (mm/s RMS) | below 2.8 | 4.5 | 7.1 |
| Bearing temperature | 45 to 65 °C | 80 °C | 90 °C |
| Discharge pressure (nominal 6.0 bar) | 5.5 to 6.5 bar | below 4.5 bar | below 3.5 bar |
| Motor current | up to 100% of rated | 105% of rated | 115% of rated |

### 8.1 Response to limits

- **Warning**: the pump may stay in service. Increase monitoring to daily readings and plan an inspection within 7 days.
- **Alarm**: inform the shift supervisor and inspect within 24 hours. If vibration exceeds **7.1 mm/s RMS**, stop the pump and investigate before restarting it. Running with alarm-level vibration quickly damages bearings and the mechanical seal.

### 8.2 Taking a manual vibration reading

Measure velocity in mm/s RMS (10 Hz to 1000 Hz) on both bearing housings in the horizontal, vertical and axial directions. Use the same measurement points each time; they are marked with a red dot on the bearing housing. Record the highest value as the overall reading.

For troubleshooting high vibration, see P-MT-02 section 4.
