---
doc_id: P-MT-02
title: P-Series Centrifugal Pumps - Maintenance and Troubleshooting Guide
filename: P-MT-02_pump_maintenance_troubleshooting.pdf
machine_type: pump
access_level: viewer
revision: Rev. B, 2024
---

# P-Series Pumps: Maintenance and Troubleshooting

## 1. Scope

This guide gives the preventive maintenance schedule, fault tables and step-by-step troubleshooting for P-Series end-suction centrifugal pumps. Operating limits are defined in P-OM-01 section 8 and in the site standard CMS-001.

Before any maintenance task that requires access to the coupling, the seal or the inside of the pump, isolate the pump according to SOP-LOTO-001 and release pressure from the pipework according to SOP-PRS-002.

## 2. Preventive maintenance schedule

| Interval | Task |
|---|---|
| Daily | Check for unusual noise, leakage at the mechanical seal and correct discharge pressure. |
| Weekly | Record vibration on both bearing housings (if no online monitoring). |
| Monthly | Check bearing temperature, foundation bolts and coupling guard. |
| Every 4,000 operating hours | Regrease the bearings: 10 g per bearing for 6308, 15 g per bearing for 6310. |
| Every 12 months | Check shaft alignment and coupling elastomer. |
| Every 16,000 hours or 2 years | Replace the mechanical seal. |
| Every 24,000 hours | Replace both bearings; measure wear ring clearance. |

### 2.1 Grease specification

Use a lithium complex grease, NLGI grade 2, with a mineral base oil viscosity of 100 to 150 mm2/s at 40 °C. Do not mix greases with different thickeners. Over-greasing is a common cause of high bearing temperature: add the quantity in the table only, with the pump running, and leave the drain plug open for 30 minutes.

### 2.2 Wear ring clearance

The diametral clearance between impeller and casing wear ring is 0.30 mm when new. Replace the wear rings when the clearance exceeds **0.60 mm**. Excessive clearance reduces flow and discharge pressure.

<!-- pagebreak -->

## 3. Fault table

| Symptom | Probable cause | Remedy |
|---|---|---|
| High vibration | Shaft misalignment | Re-align to 0.05 mm (P-OM-01 section 5.4). |
| High vibration | Cavitation (insufficient NPSH) | Check suction valve fully open, strainer clean, suction level. |
| High vibration | Impeller imbalance or deposits | Clean or balance the impeller. |
| High vibration | Worn or damaged bearings | Replace bearings (section 6). |
| High vibration | Loose foundation bolts or soft foot | Re-torque bolts to 140 N·m; correct soft foot. |
| High vibration | Operation far from BEP | Adjust the duty point with the discharge valve. |
| Low discharge pressure | Air in suction line or casing | Vent the casing; check suction joints for air leaks. |
| Low discharge pressure | Wrong direction of rotation | Swap two motor phases. |
| Low discharge pressure | Worn impeller or wear rings | Measure clearance; replace above 0.60 mm. |
| Low discharge pressure | Blocked suction strainer | Clean the strainer. |
| Seal leakage | Worn seal faces or dry running | Replace the mechanical seal (section 5). |
| Bearing overheating | Over-greasing | Remove excess grease; follow the quantities in section 2. |
| Bearing overheating | Misalignment or pipe strain | Check alignment and pipe supports. |
| Motor overload | Flow above rated (too low system resistance) | Throttle the discharge valve. |

### 3.1 Reading the vibration pattern

- Vibration highest in the **axial** direction, often at twice running speed: misalignment.
- Vibration highest in the **radial** direction at running speed (1x): imbalance.
- Broadband or high-frequency vibration with rising bearing temperature: bearing damage.
- Random vibration with crackling noise at the suction: cavitation.

<!-- pagebreak -->

## 4. Troubleshooting high vibration

Follow these steps when a P-Series pump reaches the vibration warning (4.5 mm/s RMS) or alarm (7.1 mm/s RMS) limit.

1. **Confirm the reading.** Take a manual reading on both bearing housings in the horizontal, vertical and axial directions (P-OM-01 section 8.2). A single high reading from the online sensor may be a loose sensor mount.
2. **Check the trend.** A sudden step points to a mechanical event (loose part, damaged impeller). A slow rise over weeks points to wear, deposits or bearing degradation.
3. **Decide whether to stop.** If the vibration exceeds 7.1 mm/s RMS, stop the pump and investigate before restarting. Inform the shift supervisor.
4. **Check the operating point.** Compare discharge pressure and flow to the duty point. Listen at the suction for cavitation noise. Make sure the suction valve is fully open and the strainer is clean.
5. **Check the foundation.** With the pump running, check for movement at the baseplate. After isolation, re-torque the foundation bolts to 140 N·m and check for soft foot (0.05 mm maximum).
6. **Isolate the pump** according to SOP-LOTO-001 before touching the coupling or rotating parts.
7. **Check alignment and coupling.** Measure shaft alignment and inspect the coupling elastomer for wear or cracks. Re-align if parallel offset or angular misalignment exceeds 0.05 mm.
8. **Check the bearings.** Rotate the shaft by hand and feel for roughness. High bearing temperature together with high-frequency vibration means the bearings must be replaced.
9. **Inspect the impeller.** If steps 4 to 8 show no cause, release the pressure (SOP-PRS-002), open the pump and inspect the impeller for deposits, erosion or a damaged vane.
10. **Restart and verify.** After the repair, restart the pump and confirm vibration is below 2.8 mm/s RMS. Record the readings in the maintenance ticket.

<!-- pagebreak -->

## 5. Mechanical seal replacement

1. Isolate the pump (SOP-LOTO-001) and release the pressure and drain the casing (SOP-PRS-002).
2. Remove the coupling spacer and the bearing frame assembly (back pull-out design: the casing stays on the pipework).
3. Remove the impeller nut and the impeller. Mark the position of the seal on the shaft sleeve.
4. Remove the old seal. Clean the shaft sleeve and the seal chamber. Replace the sleeve if it is scored.
5. Fit the new seal using only water or a seal lubricant; never use oil or grease on EPDM elastomers.
6. Refit the impeller and tighten the impeller nut to **95 N·m** (P-80/200) or **135 N·m** (P-100/250).
7. Reassemble, re-align and fill the pump before start-up. Never start a pump with a new seal dry.

## 6. Bearing replacement

- Remove bearings with a puller acting on the inner ring.
- Heat new bearings with an induction heater to a maximum of **110 °C**. Never use an open flame.
- Fill the bearing housing one third with grease. Over-filling leads to overheating.
- After a bearing change, expect a bearing temperature up to 75 °C during the first 8 hours as the grease distributes.

## 7. Torque values

| Joint | Torque |
|---|---|
| Foundation bolts M16 | 140 N·m |
| Impeller nut P-80/200 | 95 N·m |
| Impeller nut P-100/250 | 135 N·m |
| Casing bolts M12 | 60 N·m |
