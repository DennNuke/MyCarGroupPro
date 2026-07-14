from enum import Enum


class BodyStatus(str, Enum):
    QUEUED = "queued"        
    IN_LINE = "in_line"     
    IN_REWORK = "in_rework" 
    DONE = "done" 

class Station:
    def __init__(self,id:str, name:str, order:int, capacity:int, processingTicks:int):
        self.id = id
        self.name = name
        self.order = order
        self.capacity = capacity
        self.processingTicks = processingTicks
        self.is_occupied = False
        self.ticks_spent = 0

class Body:
    def __init__(self,id:str, vin:str,model:str, priority:int):
        self.id = id
        self.vin = vin
        self.model= model
        self.currentStationId = None
        self.status = None
        self.priority = priority

class LineState:
    def __init__(self, stations, bodies, input_queue):
        self.stations = stations
        self.bodies = bodies
        self.rework_buffer =  None
        self.event_log = list[str]
        self.ticks = 0
        self.input_queue=input_queue

    def get_station(self, station_id: str) -> Station:
        for st in self.stations:
            if st.id == station_id:
                return st
        return 0
    
    def stations_sorted(self) -> list[Station]:
        return sorted(self.stations, key=lambda s: s.order)

