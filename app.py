import os
import sys
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, render_template, session, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash

sys.path.insert(0, str(Path(__file__).parent / "src"))

from model import BodyStatus, LineState, StationStatus 
from json_loader import load_config 
from engine import (
    tick,
    send_to_tework,
    return_to_line,
    change_priority,
    get_bottleneck,
    break_station,
    update
)

CONFIG_PATH = Path(__file__).parent / "json" / "config1.json"

app = Flask(__name__)
# In production, set this via an environment variable instead of hardcoding it.
app.secret_key = os.environ.get("MYCAR_SECRET_KEY", "dev-secret-key-change-me")

# Simple single-user login store. Default password is "admin123" —
# change it (or wire up real users) before deploying this anywhere real.
USERS = {
    "admin": generate_password_hash(os.environ.get("MYCAR_ADMIN_PASSWORD", "admin123")),
}

state, commands = load_config(CONFIG_PATH)


def login_required(view_func):
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "unauthorized"}), 401
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)
    return wrapped


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get("username", "")
    password = request.form.get("password", "")
    stored_hash = USERS.get(username)

    if stored_hash and check_password_hash(stored_hash, password):
        session["user"] = username
        return redirect(url_for("index"))

    return render_template("login.html", error="Invalid username or password"), 401


@app.route("/logout", methods=["POST"])
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))


def current_station_of(body) -> str | None:
    return getattr(body, "current_station_id", None)


def serialize_state():
    stations = []
    for st in state.stations_sorted():
        occ_body = None
        if st.occupied_by:
            b = state.bodies[st.occupied_by]
            occ_body = {
                "id": st.occupied_by,
                "vin": b.vin,
                "model": b.model,
            }
        stations.append({
            "id": st.id,
            "name": st.name,
            "order": st.order,
            "capacity": st.capacity,
            "processing_ticks": st.processing_ticks,
            "ticks_spent": st.ticks_spent,
            "busy_ticks": st.busy_ticks,
            "occupied_by": occ_body,
            "status": st.status,
            "remaining_down_ticks": st.remaining_down_ticks
        })

    input_queue = []
    for body_id in state.input_queue:
        b = state.bodies[body_id]
        input_queue.append({
            "id": body_id,
            "vin": b.vin,
            "model": b.model,
            "priority": b.priority,
        })

    rework_buffer = []
    if state.rework_buffer:
        for body_id in state.rework_buffer:
            b = state.bodies[body_id]
            rework_buffer.append({
                "id": body_id,
                "vin": b.vin,
                "model": b.model,
            })

    all_bodies = []
    for body_id, b in state.bodies.items():
        status = b.status.value if isinstance(b.status, BodyStatus) else b.status
        all_bodies.append({
            "id": body_id,
            "vin": b.vin,
            "model": b.model,
            "priority": b.priority,
            "status": status,
            "current_station_id": current_station_of(b),
            "tick_entered": b.tick_entered,
            "tick_finished": b.tick_finished,
        })

    completed, throughput, avg_lead_time = state.get_metrics()

    event_log = state.event_log if state.event_log else []

    return {
        "tick": state.tick,
        "stations": stations,
        "input_queue": input_queue,
        "rework_buffer": rework_buffer,
        "bodies": all_bodies,
        "metrics": {
            "completed": completed,
            "throughput": throughput,
            "avg_lead_time": avg_lead_time,
        },
        "event_log": event_log,
        "bottleneck": get_bottleneck(state) if state.stations else None,
    }


@app.route("/")
@login_required
def index():
    return render_template("index.html")


@app.route("/api/state", methods=["GET"])
@login_required
def api_state():
    return jsonify(serialize_state())


@app.route("/api/tick", methods=["POST"])
@login_required
def api_tick():
    tick(state)
    return jsonify(serialize_state())


@app.route("/api/rework", methods=["POST"])
@login_required
def api_rework():
    data = request.get_json(force=True)
    body_id = data.get("body_id")
    send_to_tework(state, body_id)
    return jsonify(serialize_state())

@app.route("/api/break", methods=["POST"])
@login_required
def api_break():
    data = request.get_json(force=True)
    st_id = data.get("st_id")
    ticks = data.get("ticks")
    break_station(state, st_id, ticks)
    return jsonify(serialize_state())


@app.route("/api/return", methods=["POST"])
@login_required
def api_return():
    data = request.get_json(force=True)
    body_id = data.get("body_id")
    position = data.get("position")
    return_to_line(state, body_id, position)
    return jsonify(serialize_state())


@app.route("/api/priority", methods=["POST"])
@login_required
def api_priority():
    data = request.get_json(force=True)
    body_id = data.get("body_id")
    priority = data.get("priority")
    change_priority(state, body_id, priority)
    return jsonify(serialize_state())


@app.route("/api/reset", methods=["POST"])
@login_required
def api_reset():
    global state    
    state = load_config(CONFIG_PATH)
    return jsonify(serialize_state())


if __name__ == "__main__":
    app.run(debug=False, port=5000)
