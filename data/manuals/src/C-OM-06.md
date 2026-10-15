---
doc_id: C-OM-06
title: C-Series Oil-Injected Rotary Screw Air Compressors - Operation Manual
filename: C-OM-06_compressor_operation.pdf
machine_type: compressor
access_level: viewer
revision: Rev. E, 2024
---

# C-Series Rotary Screw Air Compressors

## 1. Scope

This manual covers installation and operation of C-Series oil-injected rotary screw compressors with integrated controller. Service intervals and troubleshooting are in C-MT-07. Before opening any part of the air or oil circuit, release all stored pressure according to SOP-PRS-002.

## 2. Technical data

| Parameter | C-22 | C-37 | C-55 |
|---|---|---|---|
| Free air delivery at 7 bar | 3.6 m3/min | 6.2 m3/min | 9.4 m3/min |
| Maximum working pressure | 8.0 bar | 8.0 bar | 8.0 bar |
| Motor power | 22 kW | 37 kW | 55 kW |
| Rated motor current (400 V) | 41 A | 67 A | 98 A |
| Oil capacity | 14 L | 22 L | 30 L |
| Safety valve setting | 10.0 bar | 10.0 bar | 10.0 bar |
| Sound level | 68 dB(A) | 70 dB(A) | 72 dB(A) |
| Cooling air flow | 2.9 m3/s | 4.4 m3/s | 6.1 m3/s |
| Weight | 520 kg | 780 kg | 1050 kg |

### 2.1 Main components

Air filter, inlet valve, airend (screw element), oil separator vessel with separator element, minimum pressure valve, oil cooler and aftercooler (combined cooler block), thermostatic bypass valve, oil filter, condensate drain and electronic controller.

## 3. Operating principle

Air is drawn through the air filter and the inlet valve into the airend, where it is compressed together with injected oil. The oil cools, seals and lubricates the rotors. In the separator vessel the oil is separated from the air; the air passes the minimum pressure valve and the aftercooler to the network. The oil returns through the oil cooler and the oil filter to the airend. A thermostatic valve bypasses the oil cooler until the oil reaches **71 °C**, so that no condensate forms in the oil.

<!-- pagebreak -->

## 4. Controller and set points

The controller loads the compressor when the network pressure falls to the loading pressure and unloads it when the unloading pressure is reached. When unloaded, the inlet valve closes and the motor runs with low power. After the unloaded run-on time without demand, the motor stops.

| Setting | Factory value | Adjustable range |
|---|---|---|
| Loading pressure | 7.0 bar | 5.5 to 7.5 bar |
| Unloading pressure | 7.5 bar | 6.0 to 8.0 bar |
| Unloaded run-on time | 6 min | 2 to 20 min |
| Stop run-on (unloaded before stop) | 30 s | fixed |

### 4.1 Warnings and shutdowns

| Signal | Warning | Shutdown |
|---|---|---|
| Airend discharge temperature | 105 °C | 110 °C |
| Delivery pressure | 8.5 bar | 9.0 bar |
| Oil separator differential pressure | 0.8 bar | - |
| Motor overload | - | thermal relay trip |

Normal airend discharge temperature is 80 to 95 °C. A shutdown must be investigated before the compressor is restarted. The controller stores the last 50 events with date, time and running hours.

### 4.2 Display messages

- **A:EDT** airend discharge temperature warning.
- **S:EDT** shutdown on airend discharge temperature.
- **A:SEP** separator element differential pressure high; replace the separator element.
- **A:SRV** service interval reached.

<!-- pagebreak -->

## 5. Installation

- Install the compressor indoors in a clean, well-ventilated room with an ambient temperature between **5 °C and 40 °C**.
- The cooling air flow (section 2) must be extracted from the room. Recirculation of hot air from the cooler outlet back to the cooling air inlet is the most common cause of high discharge temperature.
- Leave at least 1 m of free space around the compressor for service access.
- Connect the condensate drain to an oil-water separator. Condensate contains oil and must not go to the drain directly.
- Install an isolation valve between the compressor outlet and the air network so the compressor can be isolated for maintenance.

## 6. Daily operation

### 6.1 Before starting

- Check the oil level in the sight glass with the compressor stopped and unloaded: the level must be between the minimum and maximum marks.
- Check that the condensate drain works (test button on the drain).
- Check the controller for warnings.

### 6.2 Starting and stopping

- Start with the start button. The compressor starts unloaded and loads after the star-delta transition.
- Always stop with the stop button, not with the emergency stop. The stop button unloads the compressor and stops the motor after 30 seconds; this allows the separator vessel to depressurise.
- Use the emergency stop only in an emergency.

### 6.3 During operation

Check daily the delivery pressure, the airend discharge temperature and the loaded hours. A rising discharge temperature over several days usually means a dirty cooler.
