from model import BodyStatus, LineState 

def tick(state: LineState):
    state.ticks += 1
    stations = state.stations_sorted()
    n = len(stations)

    for i in reversed(range(n)):
        st = stations[i]
        if st.occupied_by is None:
            continue

        if st.ticks_spent < st.processingTicks:
            st.ticks_spent += 1
            continue

        body_id = st.occupied_by
        body = state.bodies[body_id]

        if i == n - 1:
            body.status = BodyStatus.DONE
            body.currentStationId = None
            st.occupied_by = None
            st.ticks_spent = 0
            continue

        next_st = stations[i + 1]
        if next_st.is_free():
            next_st.occupied_by = body_id
            next_st.ticks_spent = 0
            body.currentStationId = next_st.id
            st.occupied_by = None
            st.ticks_spent = 0

    if stations:
        first_st = stations[0]
        if first_st.is_free() and state.input_queue:
            body_id = state.input_queue.pop(0)
            body = state.bodies[body_id]

            first_st.occupied_by = body_id
            first_st.ticks_spent = 0
            body.current_station_id = first_st.id
            body.status = BodyStatus.IN_LINE

    return state