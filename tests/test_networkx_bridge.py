"""
test_networkx_bridge.py
-----------------------
Convierte un NetworkManager al grafo NetworkX equivalente y verifica
que la estructura sea idéntica: mismos nodos, enlaces, y pesos.

Uso:
    python -m tests.test_networkx_bridge          # usa red de ejemplo interna
    python -m tests.test_networkx_bridge red.json # carga un proyecto guardado

    Flags opcionales (al final):
    --no-plot    No muestra la ventana de matplotlib
    --save       Guarda la figura en tests/graph_plot.png
"""

import sys
import os
import json

# Asegura que el root del proyecto esté en el path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import networkx as nx
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
import numpy as np
from src.core.graph import NetworkManager
from src.core.export import save_project, load_project


# ─────────────────────────────────────────────
# 1. Conversión NetworkManager → NetworkX
# ─────────────────────────────────────────────

def to_networkx(network_manager: NetworkManager) -> nx.DiGraph:
    """
    Convierte un NetworkManager a un DiGraph de NetworkX.

    Atributos de nodo:  x, y (coordenadas relativas), label
    Atributos de arco:  weight
    """
    G = nx.DiGraph()

    for i, node in enumerate(network_manager.nodes):
        G.add_node(i,
                   x=node["pos"][0],
                   y=node["pos"][1],
                   label=node.get("label", ""))

    for (src, tgt), w in zip(network_manager.links, network_manager.weights):
        G.add_edge(src, tgt, weight=w)

    return G


# ─────────────────────────────────────────────
# 2. Verificación de integridad
# ─────────────────────────────────────────────

def verify(nm: NetworkManager, G: nx.DiGraph) -> bool:
    """Comprueba que el grafo NetworkX refleja exactamente el NetworkManager."""
    ok = True

    # Número de nodos
    if G.number_of_nodes() != len(nm.nodes):
        print(f"  [FAIL] Nodos: NetworkManager={len(nm.nodes)}, NetworkX={G.number_of_nodes()}")
        ok = False
    else:
        print(f"  [OK]   Nodos: {G.number_of_nodes()}")

    # Número de arcos
    if G.number_of_edges() != len(nm.links):
        print(f"  [FAIL] Arcos: NetworkManager={len(nm.links)}, NetworkX={G.number_of_edges()}")
        ok = False
    else:
        print(f"  [OK]   Arcos: {G.number_of_edges()}")

    # Cada arco existe con el peso correcto
    for (src, tgt), w in zip(nm.links, nm.weights):
        if not G.has_edge(src, tgt):
            print(f"  [FAIL] Arco faltante: {src} → {tgt}")
            ok = False
        elif G[src][tgt]["weight"] != w:
            print(f"  [FAIL] Peso incorrecto en {src}→{tgt}: "
                  f"esperado={w}, obtenido={G[src][tgt]['weight']}")
            ok = False

    return ok


# ─────────────────────────────────────────────
# 3. Análisis básico con NetworkX
# ─────────────────────────────────────────────

def analyze(G: nx.DiGraph):
    """Muestra métricas básicas del grafo usando NetworkX."""
    print("\n── Análisis NetworkX ──────────────────────────")
    print(f"  Nodos          : {G.number_of_nodes()}")
    print(f"  Arcos          : {G.number_of_edges()}")
    print(f"  Dirigido       : {G.is_directed()}")
    print(f"  Fuertemente conexo : {nx.is_strongly_connected(G) if G.number_of_nodes() > 0 else 'N/A'}")

    if G.number_of_nodes() > 0:
        # Grado de entrada y salida
        in_deg  = dict(G.in_degree())
        out_deg = dict(G.out_degree())
        print(f"  Grado entrada  : {in_deg}")
        print(f"  Grado salida   : {out_deg}")

        # Nodo con mayor centralidad de grado
        if G.number_of_edges() > 0:
            centrality = nx.degree_centrality(G)
            top_node = max(centrality, key=centrality.get)
            print(f"  Nodo más central: {top_node} "
                  f"(label='{G.nodes[top_node].get('label', '')}', "
                  f"centralidad={centrality[top_node]:.3f})")

            # Componentes fuertemente conexas
            sccs = list(nx.strongly_connected_components(G))
            print(f"  Comp. fuertemente conexas: {len(sccs)}")

        # Camino más corto (si hay nodos suficientes y el grafo es conexo)
        if G.number_of_nodes() >= 2 and nx.is_weakly_connected(G):
            try:
                src, tgt = list(G.nodes)[:2]
                path = nx.shortest_path(G, source=src, target=tgt, weight="weight")
                print(f"  Camino más corto ({src}→{tgt}): {path}")
            except nx.NetworkXNoPath:
                print(f"  Sin camino entre nodo 0 y nodo 1")

    print("───────────────────────────────────────────────")


# ─────────────────────────────────────────────
# 4. Visualización con Matplotlib
# ─────────────────────────────────────────────

def plot_graph(G: nx.DiGraph, show: bool = True, save_path: str = None):
    """
    Dibuja el grafo usando las coordenadas reales (x, y) guardadas en cada nodo.
    Si los nodos no tienen coordenadas, usa spring_layout como fallback.

    Colores de nodos: centralidad de grado (colormap plasma).
    Grosor de arcos:  proporcional al peso.
    Etiquetas:        label del nodo si existe, si no el id numérico.
    """
    if G.number_of_nodes() == 0:
        print("  [PLOT] El grafo está vacío, nada que dibujar.")
        return

    # ── Posiciones ────────────────────────────────────────────────────────────
    # Usa las coordenadas del NetworkManager si están disponibles.
    # El eje Y se invierte porque en pygame 0,0 es esquina superior izquierda.
    has_coords = all("x" in G.nodes[n] and "y" in G.nodes[n] for n in G.nodes)

    if has_coords:
        pos = {n: (G.nodes[n]["x"], 1.0 - G.nodes[n]["y"]) for n in G.nodes}
        layout_name = "coordenadas reales (espacio de la red)"
    else:
        pos = nx.spring_layout(G, seed=42)
        layout_name = "spring layout (sin coordenadas)"

    # ── Métricas para colorear ─────────────────────────────────────────────
    centrality  = nx.degree_centrality(G)
    node_values = [centrality[n] for n in G.nodes]

    # ── Pesos de arcos ────────────────────────────────────────────────────
    weights     = [G[u][v].get("weight", 1) for u, v in G.edges]
    edge_widths = [1.0 + w * 0.8 for w in weights]   # weight=1→1.8px, 3→3.4px

    # ── Etiquetas ─────────────────────────────────────────────────────────
    labels = {
        n: G.nodes[n].get("label", "") or str(n)
        for n in G.nodes
    }

    # ── Figura ────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(16, 7),
                             gridspec_kw={"width_ratios": [3, 1]})
    ax_graph, ax_info = axes

    fig.patch.set_facecolor("#0C0E12")   # mismo BG_COLOR que la app
    ax_graph.set_facecolor("#0C0E12")
    ax_info.set_facecolor("#0C0E12")

    # ── Dibujar arcos ─────────────────────────────────────────────────────
    # Separar arcos con recíproco (bidireccionales) para curvarlos
    curved, straight = [], []
    for u, v in G.edges:
        if G.has_edge(v, u):
            curved.append((u, v))
        else:
            straight.append((u, v))

    nx.draw_networkx_edges(G, pos,
                           edgelist=straight,
                           ax=ax_graph,
                           edge_color="#00FFC8",
                           arrows=True,
                           arrowsize=18,
                           arrowstyle="-|>",
                           width=[edge_widths[list(G.edges).index(e)]
                                  for e in straight] if straight else 1.5,
                           node_size=500)

    nx.draw_networkx_edges(G, pos,
                           edgelist=curved,
                           ax=ax_graph,
                           edge_color="#00C896",
                           arrows=True,
                           arrowsize=15,
                           arrowstyle="-|>",
                           connectionstyle="arc3,rad=0.2",
                           width=[edge_widths[list(G.edges).index(e)]
                                  for e in curved] if curved else 1.5,
                           node_size=500)

    # ── Dibujar nodos ─────────────────────────────────────────────────────
    cmap = plt.cm.plasma
    nc = nx.draw_networkx_nodes(G, pos,
                                ax=ax_graph,
                                node_color=node_values,
                                cmap=cmap,
                                node_size=500,
                                linewidths=1.5,
                                edgecolors="#00FFC8")

    # ── Etiquetas de nodo ─────────────────────────────────────────────────
    nx.draw_networkx_labels(G, pos,
                            labels=labels,
                            ax=ax_graph,
                            font_color="white",
                            font_size=9,
                            font_weight="bold")

    # ── Etiquetas de peso en arcos ────────────────────────────────────────
    edge_labels = {(u, v): G[u][v]["weight"]
                   for u, v in G.edges if G[u][v].get("weight", 1) != 1}
    if edge_labels:
        nx.draw_networkx_edge_labels(G, pos,
                                     edge_labels=edge_labels,
                                     ax=ax_graph,
                                     font_color="#AAFFEE",
                                     font_size=8,
                                     bbox=dict(alpha=0))

    # ── Colorbar ──────────────────────────────────────────────────────────
    sm = plt.cm.ScalarMappable(cmap=cmap,
                                norm=mcolors.Normalize(
                                    vmin=min(node_values),
                                    vmax=max(node_values)))
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax_graph, shrink=0.6, pad=0.02)
    cbar.set_label("Centralidad de grado", color="white", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="white")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="white")

    ax_graph.set_title(f"Network Creator — DiGraph\n"
                       f"Layout: {layout_name}",
                       color="white", fontsize=11, pad=12)
    ax_graph.axis("off")

    # ── Panel de métricas ─────────────────────────────────────────────────
    ax_info.axis("off")

    in_deg  = dict(G.in_degree())
    out_deg = dict(G.out_degree())

    # Top 5 nodos por centralidad
    top5 = sorted(centrality.items(), key=lambda x: x[1], reverse=True)[:5]

    lines = [
        ("MÉTRICAS", "", True),
        ("", "", False),
        ("Nodos",  str(G.number_of_nodes()), False),
        ("Arcos",  str(G.number_of_edges()), False),
        ("Dirigido", str(G.is_directed()), False),
        ("", "", False),
        ("CONECTIVIDAD", "", True),
    ]

    if G.number_of_nodes() > 1:
        lines += [
            ("Débilmente conexo",
             str(nx.is_weakly_connected(G)), False),
            ("Fuertemente conexo",
             str(nx.is_strongly_connected(G)), False),
            ("SCCs",
             str(len(list(nx.strongly_connected_components(G)))), False),
        ]

    lines += [
        ("", "", False),
        ("TOP CENTRALIDAD", "", True),
    ]
    for node_id, val in top5:
        lbl = labels[node_id]
        lines.append((f"  {lbl}", f"{val:.3f}", False))

    y = 0.97
    for left, right, is_header in lines:
        if is_header:
            ax_info.text(0.05, y, left, color="#00FFC8",
                         fontsize=9, fontweight="bold",
                         transform=ax_info.transAxes, va="top")
        else:
            ax_info.text(0.05, y, left, color="#B0C4CE",
                         fontsize=8.5, transform=ax_info.transAxes, va="top")
            if right:
                ax_info.text(0.95, y, right, color="white",
                             fontsize=8.5, transform=ax_info.transAxes,
                             va="top", ha="right")
        y -= 0.055 if is_header else 0.048

    # ── Guardar / mostrar ─────────────────────────────────────────────────
    plt.tight_layout()

    if save_path:
        os.makedirs(os.path.dirname(save_path) or ".", exist_ok=True)
        plt.savefig(save_path, dpi=150, bbox_inches="tight",
                    facecolor=fig.get_facecolor())
        print(f"  [PLOT] Figura guardada en: {save_path}")

    if show:
        plt.show()

    plt.close(fig)


# ─────────────────────────────────────────────
# 6. Red de ejemplo interna (sin archivo)
# ─────────────────────────────────────────────

def build_sample_network() -> NetworkManager:
    """Construye una red de ejemplo para probar sin necesidad de la GUI."""
    nm = NetworkManager()
    #      id   pos            label
    nm.add_node((0.1, 0.2), label="A")
    nm.add_node((0.5, 0.1), label="B")
    nm.add_node((0.9, 0.3), label="C")
    nm.add_node((0.5, 0.8), label="D")
    nm.action_history.clear()

    nm.add_link(0, 1, weight=1)  # A → B
    nm.add_link(1, 2, weight=2)  # B → C
    nm.add_link(2, 3, weight=1)  # C → D
    nm.add_link(3, 0, weight=3)  # D → A  (ciclo)
    nm.add_link(0, 2, weight=2)  # A → C  (atajo)
    nm.action_history.clear()

    return nm


# ─────────────────────────────────────────────
# 7. Main
# ─────────────────────────────────────────────

def main():
    print("═══════════════════════════════════════════════")
    print("  Network Creator → NetworkX Bridge Test")
    print("═══════════════════════════════════════════════\n")

    # ── Parsear argumentos simples ────────────────────────────────────────
    args      = sys.argv[1:]
    no_plot   = "--no-plot" in args
    do_save   = "--save"    in args
    json_args = [a for a in args if not a.startswith("--")]

    # Cargar desde archivo JSON o usar red de ejemplo
    if json_args:
        json_path = json_args[0]
        if not os.path.exists(json_path):
            print(f"[ERROR] Archivo no encontrado: {json_path}")
            sys.exit(1)
        print(f"  Cargando red desde: {json_path}\n")
        nm = load_project(json_path)
    else:
        print("  Usando red de ejemplo interna (4 nodos, 5 arcos)\n")
        nm = build_sample_network()

    # Convertir
    print("── Conversión ─────────────────────────────────")
    G = to_networkx(nm)
    print(f"  DiGraph creado: {G}")

    # Verificar integridad
    print("\n── Verificación ───────────────────────────────")
    success = verify(nm, G)
    print(f"\n  Resultado: {'✓ PASS' if success else '✗ FAIL'}")

    # Análisis
    analyze(G)

    # Exportar el DiGraph a JSON de NetworkX (node-link format)
    out_path = "tests/output_networkx.json"
    os.makedirs("tests", exist_ok=True)
    data = nx.node_link_data(G)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n  DiGraph exportado a: {out_path}")

    # Graficar
    print("\n── Visualización ──────────────────────────────")
    save_path = "tests/graph_plot.png" if do_save else None
    plot_graph(G, show=not no_plot, save_path=save_path)

    print("\n═══════════════════════════════════════════════\n")
    return G  # útil si se importa como módulo


if __name__ == "__main__":
    main()