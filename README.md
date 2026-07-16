# MyCar Pro — with frontend

## Requirements

```bash
pip install flask
```

## Run

```bash
python app.py
```

Open **http://127.0.0.1:5000** in browser.

The line loads from `json/config1.json` on startup.

## What you can do in the UI

- **Tick →** — advance the line by one tick (calls `engine.tick`)
- **Отправить на доработку** — send the selected body to rework
  (`engine.send_to_tework`)
- **Вернуть на линию** — return a body from rework back into the input
  queue at a given position (`engine.return_to_line`)
- **Изменить приоритет** — change a body's priority in the input queue
  (`engine.change_priority`)
- **Сбросить симуляцию** — reload the line from `config1.json`

The page shows stations, the input queue, the rework buffer, live metrics, and
the full event log.

## Project structure

```
mycar_app/
├── app.py                  # Flask API layer, basically frontend
├── json/
│   └── config1.json        # line config
├── src/
│   ├── model.py             # data classes 
│   ├── json_loader.py       # config loader 
│   ├── engine.py             # tick, rework, return, priority logic 
│   ├── console_printer.py    # original console printer
│   └── main.py                # original console version
├── templates/
│   └── index.html           # frontend
```

## API endpoints

All endpoints return the full serialized line state as JSON.

| Method | Endpoint        | Body                                 | Calls                    |
|--------|-----------------|---------------------------------------|---------------------------|
| GET    | `/api/state`    | —                                      | just reads current state |
| POST   | `/api/tick`     | —                                      | `engine.tick`             |
| POST   | `/api/rework`   | `{"body_id": "b1"}`                    | `engine.send_to_tework`   |
| POST   | `/api/return`   | `{"body_id": "b1", "position": 5}`     | `engine.return_to_line`   |
| POST   | `/api/priority` | `{"body_id": "b1", "priority": 1}`     | `engine.change_priority`  |
| POST   | `/api/reset`    | —                                      | `json_loader.load_config` |
