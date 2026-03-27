class NetworkManager:
    def __init__(self):
        self.nodes = []      # Lista de {"pos": (rel_x, rel_y), "label": str}
        self.links = []      # Lista de (source_idx, target_idx)
        self.weights = []
        self.action_history = []

    def add_node(self, pos, label=""):
        node = {"pos": pos, "label": label}
        self.nodes.append(node)
        self.action_history.append(("node", len(self.nodes) - 1))

    def remove_node(self, idx):
        """Elimina nodo y todos sus enlaces. Reindexar links."""
        self.nodes.pop(idx)
        # Filtra enlaces que usaban este nodo, reindexar los restantes
        new_links, new_weights = [], []
        for (s, t), w in zip(self.links, self.weights):
            if s == idx or t == idx:
                continue
            # Ajustar índices
            s = s - 1 if s > idx else s
            t = t - 1 if t > idx else t
            new_links.append((s, t))
            new_weights.append(w)
        self.links = new_links
        self.weights = new_weights
        self.action_history.append(("remove_node", idx))

    def add_link(self, start_idx, end_idx, weight=1):
        if (start_idx, end_idx) not in self.links:
            self.links.append((start_idx, end_idx))
            self.weights.append(weight)
            self.action_history.append(("link", (start_idx, end_idx)))
    
    def remove_link(self, start_idx, end_idx):
        if (start_idx, end_idx) in self.links:
            idx = self.links.index((start_idx, end_idx))
            self.links.pop(idx)
            self.weights.pop(idx)
            self.action_history.append(("remove_link", (start_idx, end_idx)))
    
    def set_label(self, node_idx, label):
        self.nodes[node_idx]["label"] = label
    

    def undo(self):
        if not self.action_history:
            return
        last = self.action_history.pop()
        if last[0] == "node":
            self.nodes.pop()
        elif last[0] == "link":
            idx = self.links.index(last[1])
            self.links.pop(idx)
            self.weights.pop(idx)
        # remove_node y remove_link no son "undoables" en este sprint