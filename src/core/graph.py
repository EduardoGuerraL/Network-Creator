class NetworkManager:
    def __init__(self):
        self.nodes = []      # Lista de (rel_x, rel_y)
        self.links = []      # Lista de (source_idx, target_idx)
        self.weights = []    # Antes 'lanes' o 'pistas'
        self.action_history = []

    def add_node(self, pos):
        self.nodes.append(pos)
        self.action_history.append(("node", pos))

    def add_link(self, start_idx, end_idx, weight=1):
        if (start_idx, end_idx) not in self.links:
            self.links.append((start_idx, end_idx))
            self.weights.append(weight)
            self.action_history.append(("link", (start_idx, end_idx)))

    def undo(self):
        if not self.action_history:
            return
        last_action = self.action_history.pop()
        if last_action[0] == "node":
            self.nodes.pop()
        elif last_action[0] == "link":
            idx = self.links.index(last_action[1])
            self.links.pop(idx)
            self.weights.pop(idx)