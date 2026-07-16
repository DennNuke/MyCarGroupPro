from enum import Enum


class BodyStatus(str, Enum):
    QUEUED = "queued"        
    IN_LINE = "in_line"     
    IN_REWORK = "in_rework" 
    DONE = "done" 

class Station:
    def __init__(self,id:str, name:str, order:int, capacity:int, processing_ticks:int):
        self.id = id
        self.name = name
        self.order = order
        self.capacity = capacity
        self.processing_ticks = processing_ticks
        self.occupied_by = None
        self.ticks_spent = 0
        self.busy_ticks = 0

    def is_free(self) -> bool:
        return self.occupied_by is None

class Body:
    def __init__(self,id:str, vin:str,model:str, priority:int):
        self.id = id
        self.vin = vin
        self.model= model
        self.current_station_id = None
        self.status = None
        self.priority = priority
        self.tick_entered = 0
        self.tick_finished = 0

class LineState:
    def __init__(self, stations, bodies, input_queue):
        self.stations = stations
        self.bodies = bodies
        self.rework_buffer =  None
        self.event_log = None
        self.tick = 0
        self.input_queue=input_queue
        self.completed = 0
        self.throughput = 0
        self.avgLeadTime = 0

    def get_station(self, station_id: str) -> Station:
        for st in self.stations:
            if st.id == station_id:
                return st
        return None
    
    def stations_sorted(self) -> list[Station]:
        return sorted(self.stations, key=lambda s: s.order)
    
    def get_metrics(self, total_ticks):
        return self.completed, self.completed / total_ticks, self.avgLeadTime
    def get_metrics(self):
        return self.completed, self.throughput, self.avgLeadTime


