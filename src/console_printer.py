from model import BodyStatus, LineState 

def print_line_state(state: LineState):
    print(f"\n___ Tick {state.ticks} ___")

    print("\nStations:")
    for st in state.stations_sorted():
        if st.occupied_by:
            body = state.bodies[st.occupied_by]
            occ = f"busy: {body.model} ({st.occupied_by}, {body.vin}) — {st.ticks_spent}/{st.processingTicks} ticks"
        else:
            occ = "free"
        print(f"  [{st.order}] {st.name:<22} ({st.id}) — {occ}")

    print("\nInput queue:")
    if not state.input_queue:
        print("  (Null)")
    else:
        for body_id in state.input_queue:
            body = state.bodies[body_id]
            print(f"  {body_id}: {body.model} ({body.vin}), priority={body.priority}")

    print("\nRework buffer:")
    if not state.rework_buffer:
        print("  (Null)")
    else:
        for body_id in state.rework_buffer:
            body = state.bodies[body_id]
            print(f"  {body_id}: {body.model} ({body.vin})")

    print()

    