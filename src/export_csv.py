import csv
from model import LineState
from engine import get_bottleneck

def export(state: LineState):
    data = [
          ["Completed", "Average lead time", "Throughput", "Bottleneck", "Down time total"],
          [state.completed, state.avgLeadTime, state.throughput, get_bottleneck(state), state.down_time_total]
    ]
    with open("./output/output.csv", "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerows(data)