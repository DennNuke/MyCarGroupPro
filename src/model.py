class Station:
    def __init__(self,id:str, name:str, order:int, capacity:int, processingTicks:int):
        self.id = id
        self.name = name
        self.order = order
        self.capacity = capacity
        self.processingTicks = processingTicks

class Body:
    def __init__(self,id:str, vin_model:str, currentStationId:int, status:int, priority:int):
        self.id = id
        self.vin_model = vin_model
        self.currentStationId = currentStationId
        self.status = status
        self.priority = priority

