import json
import os

CURRENT_VERSION = "1.0"

def save_project(filepath, network_manager):
    """Guarda en formato JSON compatible con NetworkX node-link."""
    data = {
        "version": CURRENT_VERSION,
        "graph": {},
        "nodes": [
            {
                "id": i,
                "label": n["label"],
                "x": n["pos"][0],
                "y": n["pos"][1]
            }
            for i, n in enumerate(network_manager.nodes)
        ],
        "links": [
            {
                "source": s,
                "target": t,
                "weight": w
            }
            for (s, t), w in zip(network_manager.links, network_manager.weights)
        ],
        "directed": True,
        "multigraph": False
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load_project(filepath):
    """Carga un .json y retorna un NetworkManager reconstruido."""
    from src.core.graph import NetworkManager
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    nm = NetworkManager()
    for node in data["nodes"]:
        nm.add_node((node["x"], node["y"]), label=node.get("label", ""))

    # add_node registra en action_history — limpiar para que undo no deshaga la carga
    nm.action_history.clear()

    for link in data["links"]:
        nm.add_link(link["source"], link["target"], link.get("weight", 1))

    nm.action_history.clear()
    return nm

# Mantener save_as_pickle solo para leer archivos viejos (migración)
def migrate_pickle(pickle_path, json_path):
    """Lee un .pickle viejo y lo guarda como .json nuevo."""
    import pickle
    with open(pickle_path, "rb") as f:
        old_data = pickle.load(f)

    from src.core.graph import NetworkManager
    nm = NetworkManager()
    for pos in old_data["nodes"]:
        nm.add_node(pos, label="")
    nm.action_history.clear()
    for (s, t), w in zip(old_data["links"], old_data["weights"]):
        nm.add_link(s, t, w)
    nm.action_history.clear()

    save_project(json_path, nm)
    return nm