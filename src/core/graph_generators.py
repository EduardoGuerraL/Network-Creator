"""
src/core/graph_generators.py
─────────────────────────────
Automatic network generation using classic NetworkX random graph models.
Converts the generated undirected graph into a NetworkManager instance
with relative (0..1) node positions and optional bidirectional edges.

Supported models
────────────────
  "ba"  — Barabási-Albert  (scale-free, preferential attachment)
  "er"  — Erdős-Rényi      (random, binomial)
  "ws"  — Watts-Strogatz   (small-world)
"""

from __future__ import annotations

import math
import random
from typing import Any, Dict, Tuple

import networkx as nx

from src.core.graph import NetworkManager

# ── Default / random parameter ranges ──────────────────────────────────────

_DEFAULTS: Dict[str, Dict[str, Any]] = {
    "ba": {"n": 30, "m": 2},
    "er": {"n": 30, "p": 0.15},
    "ws": {"n": 30, "k": 4, "p": 0.2},
}

_RANDOM_RANGES: Dict[str, callable] = {
    "ba": lambda: {"n": random.randint(20, 50), "m": random.randint(1, 3)},
    "er": lambda: {"n": random.randint(20, 50), "p": round(random.uniform(0.08, 0.25), 2)},
    "ws": lambda: {
        "n": random.randint(20, 50),
        "k": random.choice([4, 6, 8]),
        "p": round(random.uniform(0.05, 0.35), 2),
    },
}

MODEL_LABELS: Dict[str, str] = {
    "ba": "Barabási-Albert",
    "er": "Erdős-Rényi",
    "ws": "Watts-Strogatz",
}


# ── Public API ──────────────────────────────────────────────────────────────

def get_defaults(model: str) -> Dict[str, Any]:
    """Return the default parameter dict for *model*."""
    return dict(_DEFAULTS[model])


def get_random_params(model: str) -> Dict[str, Any]:
    """Return randomised parameters within reasonable ranges for *model*."""
    return _RANDOM_RANGES[model]()


def generate(model: str, params: Dict[str, Any]) -> NetworkManager:
    """
    Generate a network using the given model and parameters.

    Parameters
    ----------
    model  : one of "ba", "er", "ws"
    params : dict whose keys match the model's parameter names

    Returns
    -------
    A freshly created NetworkManager instance ready for use in NetworkApp.
    """
    G = _build_nx_graph(model, params)
    return _nx_to_manager(G)


def label_from_params(model: str, params: Dict[str, Any]) -> str:
    """Human-readable summary string for display in the panel footer."""
    name = MODEL_LABELS.get(model, model.upper())
    parts = [f"{k}={v}" for k, v in params.items()]
    return f"{name}  ({', '.join(parts)})"


# ── Internal helpers ────────────────────────────────────────────────────────

def _build_nx_graph(model: str, params: Dict[str, Any]) -> nx.Graph:
    """Dispatch to the correct NetworkX generator."""
    if model == "ba":
        n = int(params["n"])
        m = int(params["m"])
        m = max(1, min(m, n - 1))
        return nx.barabasi_albert_graph(n, m)

    elif model == "er":
        n = int(params["n"])
        p = float(params["p"])
        p = max(0.0, min(p, 1.0))
        return nx.erdos_renyi_graph(n, p)

    elif model == "ws":
        n = int(params["n"])
        k = int(params["k"])
        p = float(params["p"])
        # k must be even and < n
        k = max(2, min(k, n - 1))
        if k % 2 != 0:
            k -= 1
        p = max(0.0, min(p, 1.0))
        return nx.watts_strogatz_graph(n, k, p)

    else:
        raise ValueError(f"Unknown model: {model!r}")


def _nx_to_manager(G: nx.Graph) -> NetworkManager:
    """
    Convert an undirected NetworkX graph to a NetworkManager.

    Node layout
    ───────────
    • n ≤ 60  → circular layout  (clean, no crossings for small nets)
    • n > 60  → jittered concentric rings (fast, avoids overlap)

    Edges
    ─────
    Both directions (u→v and v→u) are added so the directed graph preserves
    the undirected semantics of the random graph models.
    """
    nm  = NetworkManager()
    n   = G.number_of_nodes()
    pos = _compute_layout(n)

    for i in range(n):
        nm.add_node(pos[i], label=str(i + 1))
    nm.action_history.clear()

    for u, v in G.edges():
        nm.add_link(u, v, weight=1)
        nm.add_link(v, u, weight=1)   # bidirectional
    nm.action_history.clear()

    return nm


def _compute_layout(n: int) -> list:
    """
    Return a list of (rel_x, rel_y) positions in [0.05, 0.95]².

    Strategy
    ────────
    • 1–60 nodes : evenly spaced on a single circle
    • 61–200     : two concentric circles
    • > 200      : grid with small random jitter
    """
    if n == 0:
        return []

    if n <= 60:
        return _circle_layout(n, cx=0.5, cy=0.5, r=0.38)

    if n <= 200:
        outer = int(n * 0.65)
        inner = n - outer
        return (
            _circle_layout(outer, cx=0.5, cy=0.5, r=0.40)
            + _circle_layout(inner, cx=0.5, cy=0.5, r=0.22)
        )

    # Grid fallback with jitter
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    step = 0.90 / max(cols, rows)
    positions = []
    for i in range(n):
        col = i % cols
        row = i // cols
        x = 0.05 + col * step + random.uniform(-step * 0.15, step * 0.15)
        y = 0.05 + row * step + random.uniform(-step * 0.15, step * 0.15)
        positions.append((round(x, 4), round(y, 4)))
    return positions


def _circle_layout(
    n: int, cx: float, cy: float, r: float
) -> list:
    """Place *n* nodes evenly on a circle of radius *r* centred at (cx, cy)."""
    positions = []
    for i in range(n):
        angle = 2 * math.pi * i / n - math.pi / 2   # start at top
        x = round(cx + r * math.cos(angle), 4)
        y = round(cy + r * math.sin(angle), 4)
        positions.append((x, y))
    return positions