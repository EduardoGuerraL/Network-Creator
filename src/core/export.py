import pickle
import os
import json

def save_as_pickle(filename, network_manager):
    data = {
        "nodes": network_manager.nodes,
        "links": network_manager.links,
        "weights": network_manager.weights,
        "history": network_manager.action_history
    }
    with open(filename, "wb") as f:
        pickle.dump(data, f)

def export_to_json(filename, network_manager):
    # Ideal para web o integraciones modernas
    data = {
        "nodes": [{"id": i, "x": n[0], "y": n[1]} for i, n in enumerate(network_manager.nodes)],
        "edges": [{"from": l[0], "to": l[1], "w": w} for l, w in zip(network_manager.links, network_manager.weights)]
    }
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)