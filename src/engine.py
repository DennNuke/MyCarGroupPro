from model import BodyStatus, LineState, StationStatus

def tick(state: LineState):
    state.tick += 1
    stations = state.stations_sorted()
    n = len(stations)

    for i in reversed(range(n)):
        st = stations[i]
        if st.occupied_by is None:
            continue

        if st.status == StationStatus.DOWN:
            st.remaining_down_ticks -= 1
            state.down_time_total +=1
            if st.remaining_down_ticks == 0:
                st.status = StationStatus.UP
                _log(state, "STATION RECOVER", st.id, None, None)
            continue

        st.busy_ticks +=1

        if st.ticks_spent < st.processing_ticks:
            st.ticks_spent += 1
            continue

        body_id = st.occupied_by
        body = state.bodies[body_id]

        if i == n - 1:
            body.status = BodyStatus.DONE
            body.current_station_id = None
            st.occupied_by = None
            st.ticks_spent = 0

            body.tick_finished = state.tick

            state.completed += 1
            state.throughput = state.completed / state.tick
            state.avgLeadTime = (state.avgLeadTime * (state.completed - 1) + (body.tick_finished - body.tick_entered)) / state.completed
            _log(state, "EXIT_LINE", body_id, st.id, None)
            continue

        next_st = stations[i + 1]
        if next_st.is_free():
            next_st.occupied_by = body_id
            next_st.ticks_spent = 0
            body.current_station_id = next_st.id
            st.occupied_by = None
            st.ticks_spent = 0
            
            _log(state, "ADVANCE_LINE", body_id, st.id, next_st.id)

    if stations:
        first_st = stations[0]
        if first_st.is_free() and state.input_queue and first_st.status :
            if st.status == StationStatus.DOWN:
                st.remaining_down_ticks -= 1
                state.down_time_total +=1
                if st.remaining_down_ticks == 0:
                    st.status = StationStatus.UP
                    _log(state, "STATION RECOVER", st.id, None, None)
            else:
                body_id = state.input_queue.pop(0)
                body = state.bodies[body_id]

                first_st.occupied_by = body_id
                first_st.ticks_spent = 0
                body.current_station_id = first_st.id
                body.status = BodyStatus.IN_LINE
            
                body.tick_entered = state.tick
                _log(state, "ENTER_LINE", body_id, None, first_st.id)


    return state

def send_to_tework(state: LineState, body_id):
    body = state.bodies.get(body_id)

    if body is None:
        raise ValueError(f"Body with id={body_id!r} not found")

    if body.status != BodyStatus.IN_LINE or body.current_station_id is None:
        raise ValueError(
            f"Body {body_id!r} cannot be sent to rework: "
            f"body isn't in line(body status: {body.status.value})"
        )

    st = state.get_station(body.current_station_id)

    if st.occupied_by != body_id:
        raise ValueError(
            f"Unauthorized state: station {st.id!r} doesn't contain {body_id!r}"
        )

    body.current_station_id = None
    st.occupied_by = None
    st.ticks_spent = 0

    if state.rework_buffer == None:
        state.rework_buffer = []
    state.rework_buffer.append(body_id)
    body.status = BodyStatus.IN_REWORK
    
    _log(state, "REWORK_SENT", body_id, st.id, "rework")

def return_to_line(state: LineState, body_id, position):
    body = state.bodies.get(body_id)

    if body is None:
        raise ValueError(f"Body with id={body_id!r} not found")

    if body_id not in state.rework_buffer:
        raise ValueError(
            f"Body {body_id!r} cannot be returned to line: it isn't located "
            f"in rework buffer (body status: {body.status.value})"
        )

    body.priority = position
    state.input_queue.insert(0, body_id)
    state.input_queue.sort(key=lambda x: state.bodies.get(x).priority)
    body.status = BodyStatus.QUEUED
    state.rework_buffer.remove(body_id)

    
    _log(state, "RETURN_LINE", body_id, "rework", None)

def  change_priority(state: LineState, body_id, priority):
    body = state.bodies.get(body_id)

    if body is None:
        raise ValueError(f"Body with id={body_id!r} not found")

    _log(state, "PRIORITY_CHANGE", body_id, f"p: {body.priority}", f"p: {priority}")
    body.priority = priority
    state.input_queue.sort(key=lambda x: state.bodies.get(x).priority)


def get_bottleneck(state: LineState):
    stations = state.stations_sorted()
    n = len(stations)

    max_st = stations[0]
    for i in range(n):
        st = stations[i]
        if st.busy_ticks > max_st.busy_ticks:
            max_st = st
    return max_st.id

def  break_station(state: LineState, st_id: str, ticks):
    st = state.get_station(st_id)
    st.status = StationStatus.DOWN
    st.remaining_down_ticks = ticks
    _log(state, "STATION BREAK", st_id, None, None)

def run_scenario(config, ticks):
    line_state, commands = config
    for n in range(0, ticks):
        tick(line_state)
        update(commands, line_state)
    return line_state.get_metrics()[0], line_state.get_metrics()[1], get_bottleneck(line_state)

def _log(state: LineState, event_type: str, body_id: str, from_: str | None, to: str | None) -> None:
    if state.event_log == None:
        state.event_log = []
    state.event_log.append(
        {
            "tick": state.tick,
            "type": event_type,
            "body_id": body_id,
            "from": from_,
            "to": to,
        }
    )

def update(commands, state: LineState):
    for n in range(0, len(commands)):
        command = commands[n]
        if command["atTick"] != state.tick:
            continue
        match command["type"]:
            case "send_to_rework":
                send_to_tework(state, command["object_id"])
                return
            case "return_to_line":
                return_to_line(state, command["object_id"], command["param"])
                return
            case "change_priority":
                change_priority(state, command["object_id"], command["param"])
                return
            case "break_station":
                break_station(state, command["object_id"], command["param"])
                return