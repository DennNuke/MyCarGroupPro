# MyCarGroupPro

MES simualtion

## How it works

- The line is made up of **stations**, each with a different number of ticks of processing a body.
- **Bodies** (cars) enter from an input queue, sorted by priority, and go from station to station.
- Each call to `tick()` advances the simulation by one time.
- **Commands** loaded from the config file are applied at specific ticks with `update()`:
  - `send_to_rework` — pull a body off the line into a rework buffer
  - `return_to_line` — reinsert a reworked body into the input queue at a given priority
  - `change_priority` — reorder a body in the input queue
  - `break_station` — take a station down for a number of ticks
- Every state change is recorded in an event log (`ENTER_LINE`, `ADVANCE_LINE`, `EXIT_LINE`, `REWORK_SENT`, `RETURN_LINE`, `PRIORITY_CHANGE`, `STATION BREAK`, `STATION RECOVER`).
- At the end of a run, the simulator reports completed bodies, throughput, average lead time, and the bottleneck station (the one with the most busy ticks), and exports these metrics to CSV.

## Project structure

```
MyCar/
├── json/
│   ├── config1.json      # scenario #1
│   └── config2.json      # scenario #2
├── output/
│   └── output.csv        # metrics from the last run
├── src/
│   ├── main.py            # entry point — runs the simulation tick by tick
│   ├── model.py            # core data classes: Station, Body, LineState
│   ├── engine.py            # simulation logic: tick(), update(), commands, metrics
│   ├── json_loader.py        # loads a LineState + commands from a JSON config
│   ├── console_printer.py     # prints line state to the console each tick
│   └── export_csv.py          # writes final metrics to output/output.csv
└── README.md
```

## Requirements

- Python 3.10+

## Usage

```bash
cd src
python main.py
```

Each run prints:
- The station and input-queue state after every tick
- The full event log
- Final metrics: completed bodies, throughput, average lead time
- The bottleneck station and how many ticks it was busy
- A CSV export to `output/output.csv`

## Config file format

```json
{
  "stations": [
    { "id": "st1", "name": "One", "order": 0, "capacity": 1, "processingTicks": 1 }
  ],
  "bodies": [
    { "id": "b1", "vin": "KZ0001", "model": "Mercedes", "priority": 10 }
  ],
  "commands": [
    { "type": "send_to_rework", "object_id": "b1", "param": 0, "atTick": 3 },
    { "type": "return_to_line", "object_id": "b1", "param": 2, "atTick": 5 },
    { "type": "change_priority", "object_id": "b4", "param": 4, "atTick": 6 },
    { "type": "break_station", "object_id": "st2", "param": 4, "atTick": 8 }
  ]
}
```

- **stations**: `order` determines line position (0 = first); `processingTicks` is how long a body occupies the station.
- **bodies**: `priority` (lower = earlier) determines input queue order.
- **commands**: `atTick` is when the command fires; `object_id` is the body or station it targets; `param` meaning depends on the command (rework insertion index, new priority, downtime length).

## Output metrics (`output/output.csv`)

| Column | Meaning |
|---|---|
| Completed | Number of bodies that exited the line |
| Average lead time | Mean ticks from entry to completion |
| Throughput | Completed bodies per tick |
| Bottleneck | Station with the highest total busy ticks |
| Down time total | Total ticks lost to station breakdowns |

## Known limitations / TODO

- login
- fix up some code