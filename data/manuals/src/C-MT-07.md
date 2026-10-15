---
doc_id: C-MT-07
title: C-Series Rotary Screw Compressors - Maintenance and Troubleshooting Guide
filename: C-MT-07_compressor_maintenance_troubleshooting.pdf
machine_type: compressor
access_level: viewer
revision: Rev. C, 2024
---

# C-Series Compressors: Maintenance and Troubleshooting

## 1. Scope and safety

This guide covers preventive maintenance, fault finding and the oil change procedure for C-Series compressors. Set points and limits are given in C-OM-06.

Before any maintenance: stop the compressor with the stop button, isolate it according to SOP-LOTO-001, close the outlet isolation valve and release all pressure from the separator vessel according to SOP-PRS-002. The oil and the airend can be hotter than 80 °C directly after stopping.

## 2. Service intervals

| Interval | Task |
|---|---|
| Daily | Check oil level, condensate drain and controller messages. |
| Every 500 hours | Clean the air filter pre-filter mat. Check the cooler for dirt. |
| Every 2,000 hours | Replace the air filter element. Clean the cooler fins. |
| Every 4,000 hours or 12 months | Change the oil and the oil filter. Replace the air filter element. |
| Every 8,000 hours | Replace the oil separator element. Check the minimum pressure valve. |
| Every 8,000 hours | Check the thermostatic valve and the condensate drain. |
| Every 24,000 hours | Airend bearing inspection by authorised service. |

Replace the oil separator element earlier if the separator differential pressure exceeds **0.8 bar** (controller message A:SEP), or if oil carry-over into the network is observed.

### 2.1 Oil specification

Use only the synthetic compressor oil specified for C-Series compressors (ISO VG 46, 4,000-hour oil). Do not mix with mineral oil. Oil capacity: C-22: 14 L, C-37: 22 L, C-55: 30 L.

<!-- pagebreak -->

## 3. Fault table

| Symptom | Probable cause | Remedy |
|---|---|---|
| High discharge temperature | Low oil level | Top up oil; look for leaks. |
| High discharge temperature | Dirty or blocked cooler | Clean the cooler fins with compressed air from the fan side. |
| High discharge temperature | Hot air recirculation / poor ventilation | Check room ventilation and ducting. |
| High discharge temperature | Faulty thermostatic valve | Replace the thermostatic valve element. |
| High discharge temperature | Clogged oil filter | Replace the oil filter. |
| High discharge temperature | Ambient above 40 °C | Improve ventilation. |
| Delivery pressure too high, safety valve blows | Unloading pressure set too high | Check controller set points. |
| Delivery pressure too high | Inlet valve does not close | Check inlet valve and solenoid valve. |
| Delivery pressure too low | Air demand higher than capacity | Check for network leaks; add capacity. |
| Delivery pressure too low | Clogged air filter | Replace the air filter element. |
| Oil in compressed air | Separator element damaged or saturated | Replace the separator element. |
| Oil in compressed air | Scavenge line blocked | Clean the scavenge line and its nozzle. |
| High vibration | Loose mounting or worn coupling element | Check anti-vibration mounts and coupling. |
| High vibration | Airend bearing wear | Contact authorised service. |
| Motor overload trip | High pressure, low voltage, airend damage | Check set points and supply voltage; turn the airend by hand. |

<!-- pagebreak -->

## 4. Troubleshooting high discharge temperature

Use this procedure for warning A:EDT (105 °C) or shutdown S:EDT (110 °C).

1. **Read the event log** on the controller. Note the temperature, the ambient temperature and the loaded hours at the event.
2. **Check the room.** Measure the ambient temperature near the cooling air inlet. Look for recirculation of hot cooler air and for blocked ventilation openings.
3. **Check the oil level** with the compressor stopped and depressurised. Low oil level is the most frequent cause of high temperature.
4. **Inspect the cooler.** Remove the cooler cover and inspect the fins. Clean with compressed air (maximum 6 bar) blowing from the fan side, or with a soft brush. Do not use high-pressure water.
5. **Check the oil filter and thermostatic valve.** If the cooler outlet stays cold while the airend is hot, the thermostatic valve is stuck in bypass. Replace the element.
6. **Check the oil.** Dark or sludgy oil has lost its cooling capacity. Change the oil and the oil filter (section 5).
7. **Restart and monitor.** After the repair, run the compressor loaded for at least 30 minutes and confirm the discharge temperature is between 80 and 95 °C.

Do not bypass or raise the 110 °C shutdown. At higher temperatures the oil can oxidise and there is a risk of fire in the separator vessel.

<!-- pagebreak -->

## 5. Oil and oil filter change

1. Run the compressor until the oil is warm (about 60 °C); warm oil drains faster and carries contaminants out.
2. Stop the compressor with the stop button. Isolate and lock out according to SOP-LOTO-001.
3. Close the outlet isolation valve and release the pressure according to SOP-PRS-002. Check that the separator vessel pressure gauge reads **0 bar**.
4. Slowly open the oil filler plug one turn to release any remaining pressure.
5. Drain the oil from the drain valve of the separator vessel and the oil cooler into a container. Dispose of used oil as hazardous waste.
6. Replace the oil filter. Lubricate the new filter gasket with oil and tighten by hand, three quarters of a turn after contact.
7. Close the drain valves and fill with new oil to the maximum mark of the sight glass.
8. Refit the filler plug, remove the locks and start the compressor. Run for a few minutes, stop, depressurise and check the oil level again.
9. Reset the service counter on the controller and record the oil change in the maintenance ticket.
