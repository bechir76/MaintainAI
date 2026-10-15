---
doc_id: M-MT-04
title: M-Series Induction Motors - Maintenance and Troubleshooting Guide
filename: M-MT-04_motor_maintenance_troubleshooting.pdf
machine_type: motor
access_level: viewer
revision: Rev. B, 2023
---

# M-Series Motors: Maintenance and Troubleshooting

## 1. Scope

This guide describes preventive maintenance and troubleshooting for M-Series TEFC induction motors. Ratings and operating limits are given in M-OM-03. Insulation and winding tests are in M-ETP-05 (restricted to qualified electrical technicians).

All work on the motor or the terminal box requires isolation according to SOP-LOTO-001. Check for absence of voltage before opening the terminal box.

## 2. Preventive maintenance schedule

| Interval | Task |
|---|---|
| Monthly | Clean the cooling fins and the fan cover inlet. Check for unusual noise. |
| Every 3 months | Check winding temperature trend and running current against nameplate. |
| Per lubrication table (M-OM-03 section 5) | Regrease the bearings. |
| Every 12 months | Measure insulation resistance (M-ETP-05). Check terminal connections for tightness and discolouration. |
| Every 12 months | Check alignment and vibration on both bearing housings. |
| Every 40,000 hours | Replace both bearings. |

### 2.1 Cleaning the cooling path

TEFC motors depend on the air flow from the shaft-mounted fan over the finned frame. Dust, fibres or oil mist on the fins act as insulation and can raise the winding temperature by 10 to 20 °C. Clean the fins with a brush or dry compressed air at a maximum of 2 bar, with the motor isolated. Never use a water jet on the fan cover.

<!-- pagebreak -->

## 3. Fault table

| Symptom | Probable cause | Remedy |
|---|---|---|
| Overheating | Blocked or dirty cooling fins / fan cover | Clean the cooling path (section 2.1). |
| Overheating | Damaged or missing cooling fan | Replace the fan; check fan cover clearance. |
| Overheating | Mechanical overload of the driven machine | Measure current; check the driven load (jammed conveyor, worn bearings). |
| Overheating | Supply voltage imbalance above 1% | Measure phase voltages; correct the supply. |
| Overheating | Single phasing (loss of one phase) | Check fuses, contactor contacts and terminals. |
| Overheating | Too many starts per hour | Limit to 3 starts per hour. |
| Overheating | High ambient temperature (above 40 °C) | Improve ventilation or derate. |
| High vibration | Misalignment or soft foot | Re-align; correct soft foot to 0.05 mm. |
| High vibration | Bearing damage | Replace the bearings. |
| High vibration | Rotor imbalance or broken rotor bar | Balance the rotor; check current spectrum for pole pass sidebands. |
| Noisy bearings | Lack of grease or wrong grease | Regrease per M-OM-03 section 5. |
| Overload relay trips | Overload, wrong relay setting, single phasing | Check current per phase and relay setting. |
| Motor does not start | No supply, blown fuse, motor or load locked | Check supply and that the shaft turns freely after isolation. |

<!-- pagebreak -->

## 4. Troubleshooting motor overheating

Use this procedure when the winding temperature reaches the warning limit of **130 °C**, or when the motor has tripped on the winding temperature alarm of **145 °C**.

1. **Do not reset and restart repeatedly.** A motor that tripped on temperature must cool down before restart. Repeated restarts add starting heat and can destroy the winding.
2. **Confirm the measurement.** Compare the three PT100 readings. One sensor reading much higher than the others may be a sensor or wiring fault. Check the frame temperature with an infrared thermometer: at full load the frame is typically 40 to 60 °C above ambient.
3. **Check the load current.** Measure the current in all three phases and compare with the rated current on the nameplate. A current above rated current means the motor is overloaded: check the driven machine (for a conveyor: jammed rollers, belt tension, product build-up).
4. **Check the supply.** Measure the three phase-to-phase voltages. Calculate the voltage imbalance; it must not exceed 1%. A missing phase or a high-resistance connection gives one phase with high or zero current.
5. **Check the cooling.** Inspect the fan and fan cover, clean the cooling fins and make sure there is free space behind the fan cover. Check that the motor is not drawing in hot air.
6. **Check the duty.** Review the start/stop history. More than 3 starts per hour overheats the motor.
7. **Check the bearings.** A failing bearing adds friction heat and noise, mainly at the drive end.
8. **Check the winding insulation.** If the motor has been running above 145 °C, a qualified electrical technician must measure the insulation resistance (M-ETP-05) before the motor is returned to service.
9. **Record the findings** in a maintenance ticket with the measured currents, voltages and temperatures.

<!-- pagebreak -->

## 5. Bearing replacement

1. Isolate the motor according to SOP-LOTO-001 and uncouple it from the driven machine.
2. Remove the fan cover and the fan. Mark the position of the end shields.
3. Remove the end shields and withdraw the rotor carefully, supporting it so that it does not touch the stator winding.
4. Pull the bearings off with a puller acting on the inner ring.
5. Heat the new bearings with an induction heater to a maximum of **110 °C** and slide them onto the shaft. Never hammer a bearing onto the shaft.
6. Fill the bearing and the grease chamber about one half with fresh grease of the specified type.
7. Reassemble the motor, check that the rotor turns freely and measure the insulation resistance before connecting the supply.

## 6. Checking for broken rotor bars

Broken rotor bars cause current fluctuations at twice slip frequency and vibration at running speed with sidebands. Typical signs are a cyclic "beating" noise under load and a slow pulsation of the ammeter needle. Confirm with motor current signature analysis; a sideband level less than 45 dB below the supply frequency peak indicates a broken bar.
