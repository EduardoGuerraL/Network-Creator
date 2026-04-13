"""
src/gui/app.py
──────────────
Main Network Creator editor.

New features vs previous version
──────────────────────────────────
  • Side panel (StatsPanel) with analytics, generation, and path controls.
  • PATH mode: left-click two nodes to highlight the shortest path.
  • Network generation via BA / ER / WS from the panel.
  • canvas_size / screen_size separation so viewport math is unchanged.
"""

from __future__ import annotations

from typing import Optional, Set, Tuple

import pygame
from pygame.locals import (
    QUIT, MOUSEBUTTONDOWN, MOUSEMOTION, MOUSEBUTTONUP,
    KEYDOWN, K_r, K_z, K_s, K_o, K_e, K_b, K_n, K_TAB,
    K_1, K_2, K_3, KMOD_CTRL,
)

from src.core.export import save_project, load_project, migrate_pickle
from src.core.graph import NetworkManager
from src.core import graph_generators as gen
from src.gui.stats_panel import StatsPanel
from src.gui.widgets import (
    get_save_path, get_open_path, ask_node_label, get_image_path,
    ask_ba_params, ask_er_params, ask_ws_params,
)
from src.utils.geometry import draw_arrow

import networkx as nx

# Width of the editable canvas (left region of the window)
_CANVAS_W = 1200

# Colour constants for path highlighting
_COL_PATH_EDGE = (50,  210, 110)   # green arrow for path edges
_COL_PATH_NODE = (255, 200, 50)    # gold circle for path nodes
_COL_PATH_SRC  = (0,   220, 255)   # cyan for source node
_COL_PATH_DST  = (255, 100, 100)   # pink for destination node


class NetworkApp:
    """
    Main application loop.

    Viewport geometry
    ─────────────────
    canvas_size  (1200 × 800)  — logical canvas for pan / zoom / node placement.
    screen_size  (1510 × 800)  — actual Pygame window  (canvas + side panel).
    """

    def __init__(self, img_path: Optional[str] = None) -> None:
        pygame.init()
        self.clock = pygame.time.Clock()
        self.font  = pygame.font.SysFont("Arial", 18)

        # ── Canvas / image ──────────────────────────────────────────────────
        self.has_image = False
        self.min_zoom  = None
        self.max_zoom  = None
        self.zoom      = 1.0
        self.width, self.height = 4000, 3000
        self.bg_image = pygame.Surface((self.width, self.height))
        self.bg_image.fill((35, 38, 43))

        # ── Window ──────────────────────────────────────────────────────────
        self.canvas_size = (_CANVAS_W, 800)
        self.screen_size = (_CANVAS_W + StatsPanel.PANEL_W, 800)
        self.screen      = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("Network Creator")

        self.image_rect = self.bg_image.get_rect()

        # ── Network logic ───────────────────────────────────────────────────
        self.network = NetworkManager()

        # ── Editor state ────────────────────────────────────────────────────
        self.zoom          = 1.0
        self.offset        = [0, 0]
        self.dragging      = False
        self.mode          = "CREATE"   # "CREATE" | "DELETE" | "PATH"
        self.selected_node: Optional[int] = None
        self.current_weight = 1

        # ── Shortest-path state ─────────────────────────────────────────────
        self._path_start: Optional[int]   = None
        self._path_nodes: Set[int]        = set()
        self._path_edges: Set[Tuple[int,int]] = set()

        # ── Side panel ──────────────────────────────────────────────────────
        self.stats_panel = StatsPanel()

        # ── Optional background image ────────────────────────────────────────
        if img_path:
            self._load_background(img_path)

    # ═══════════════════════════════════════════════════════════════════════
    # Main loop
    # ═══════════════════════════════════════════════════════════════════════

    def run(self) -> None:
        running = True
        while running:
            self.clock.tick(60)
            running = self.handle_events()
            self.draw()
        pygame.quit()

    # ═══════════════════════════════════════════════════════════════════════
    # Event handling
    # ═══════════════════════════════════════════════════════════════════════

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            elif event.type == KEYDOWN:
                self._handle_keydown(event)
            elif event.type == MOUSEBUTTONDOWN:
                self._handle_mousedown(event)
            elif event.type == MOUSEBUTTONUP:
                if event.button in (1, 2):
                    self.dragging = False
            elif event.type == MOUSEMOTION:
                self._handle_mousemotion(event)
        return True

    def _handle_keydown(self, event: pygame.event.Event) -> None:
        if event.key == K_n:
            self.mode = "CREATE"
            self._reset_path()
        elif event.key == K_r:
            self.mode = "DELETE" if self.mode != "DELETE" else "CREATE"
            self._reset_path()
        elif event.key == K_e:
            idx = self._get_node_at(pygame.mouse.get_pos())
            if idx is not None:
                lbl = ask_node_label(self.network.nodes[idx]["label"])
                if lbl is not None:
                    self.network.set_label(idx, lbl)
        elif event.key == K_TAB:
            # Cycle centrality metric in the side panel
            self.stats_panel.next_metric()

        if event.mod & KMOD_CTRL:
            if event.key == K_z:
                self.network.undo()
            elif event.key == K_s:
                path = get_save_path()
                if path:
                    save_project(path, self.network)
            elif event.key == K_o:
                path = get_open_path()
                if path:
                    self.network = (
                        migrate_pickle(path, path.replace(".pickle", ".json"))
                        if path.endswith(".pickle")
                        else load_project(path)
                    )
                    self._reset_path()
            elif event.key == K_b:
                path = get_image_path()
                if path:
                    self._load_background(path)

        if event.key in (K_1, K_2, K_3):
            self.current_weight = int(event.unicode)

    def _handle_mousedown(self, event: pygame.event.Event) -> None:
        pos = event.pos

        # ── Panel area: delegate to side panel ──────────────────────────────
        if pos[0] >= _CANVAS_W:
            if event.button == 1:
                action = self.stats_panel.handle_click(pos[0] - _CANVAS_W, pos[1])
                if action:
                    self._dispatch_panel_action(action)
            return

        # ── Canvas area ─────────────────────────────────────────────────────
        if event.button in (4, 5):
            self._handle_zoom(event.button, pos)
            return

        if event.button == 1:
            self._handle_left_click(pos)
        elif event.button == 3:
            self._handle_right_click(pos)
        elif event.button == 2:
            self.dragging = True
            self.mouse_start_x,  self.mouse_start_y  = pos
            self.offset_start_x, self.offset_start_y = self.image_rect.topleft

    def _handle_left_click(self, pos: Tuple[int, int]) -> None:
        if self.mode == "CREATE":
            rel = self._screen_to_rel(pos)
            self.network.add_node(rel, label=self.network.next_available_label())

        elif self.mode == "DELETE":
            idx = self._get_node_at(pos)
            if idx is not None:
                self.network.remove_node(idx)
                self.selected_node = None
                self._reset_path()

        elif self.mode == "PATH":
            idx = self._get_node_at(pos)
            if idx is None:
                return
            if self._path_start is None:
                # First node selected
                self._path_start = idx
                self._path_nodes = {idx}
                self._path_edges = set()
                self.stats_panel.set_path_status(
                    f"Origen: nodo {self.network.nodes[idx]['label']}  — selecciona destino"
                )
            elif idx != self._path_start:
                # Second node: compute path
                self._compute_path(self._path_start, idx)
                self._path_start = None

    def _handle_right_click(self, pos: Tuple[int, int]) -> None:
        """Right-click: link creation (or cancels path selection)."""
        if self.mode == "PATH":
            self._reset_path()
            return

        idx = self._get_node_at(pos)
        if idx is not None:
            if self.selected_node is None:
                self.selected_node = idx
            else:
                self.network.add_link(self.selected_node, idx, self.current_weight)
                self.selected_node = None
        else:
            self.selected_node = None

    # ═══════════════════════════════════════════════════════════════════════
    # Panel action dispatcher
    # ═══════════════════════════════════════════════════════════════════════

    def _dispatch_panel_action(self, action: dict) -> None:
        atype = action["type"]

        if atype == "generate":
            self._generate_network(action["model"], action["mode"])

        elif atype == "toggle_path":
            if action["active"]:
                self.mode = "PATH"
                self._reset_path()
                self.stats_panel.set_path_status("Selecciona el nodo origen")
            else:
                self.mode = "CREATE"
                self._reset_path()

    # ═══════════════════════════════════════════════════════════════════════
    # Network generation
    # ═══════════════════════════════════════════════════════════════════════

    def _generate_network(self, model: str, mode: str) -> None:
        """
        Replace the current network with a freshly generated one.

        Parameters
        ----------
        model : "ba" | "er" | "ws"
        mode  : "random" → use random params
                "params" → open Tkinter dialogs for manual input
        """
        if mode == "random":
            params = gen.get_random_params(model)
        else:
            params = self._ask_params(model)
            if params is None:
                return   # user cancelled

        self.network = gen.generate(model, params)
        self._reset_path()
        self.selected_node = None
        label = gen.label_from_params(model, params)
        self.stats_panel.set_last_gen_label(label)

    def _ask_params(self, model: str):
        """Open Tkinter dialogs for the chosen model; returns param dict or None."""
        if model == "ba":
            result = ask_ba_params()
            if result is None:
                return None
            n, m = result
            return {"n": n, "m": m}
        elif model == "er":
            result = ask_er_params()
            if result is None:
                return None
            n, p = result
            return {"n": n, "p": p}
        elif model == "ws":
            result = ask_ws_params()
            if result is None:
                return None
            n, k, p = result
            return {"n": n, "k": k, "p": p}
        return None

    # ═══════════════════════════════════════════════════════════════════════
    # Shortest-path logic
    # ═══════════════════════════════════════════════════════════════════════

    def _compute_path(self, src: int, dst: int) -> None:
        """Compute shortest path src→dst and store highlighted sets."""
        G = nx.DiGraph()
        G.add_nodes_from(range(len(self.network.nodes)))
        for s, t in self.network.links:
            G.add_edge(s, t)

        src_lbl = self.network.nodes[src]["label"]
        dst_lbl = self.network.nodes[dst]["label"]

        try:
            path = nx.shortest_path(G, source=src, target=dst)
            self._path_nodes = set(path)
            self._path_edges = set(zip(path[:-1], path[1:]))
            self.stats_panel.set_path_status(
                f"Camino: {' → '.join(self.network.nodes[i]['label'] for i in path)}"
                f"  (longitud {len(path)-1})"
            )
        except nx.NetworkXNoPath:
            self._path_nodes = {src, dst}
            self._path_edges = set()
            self.stats_panel.set_path_status(
                f"Sin camino entre {src_lbl} y {dst_lbl}", error=True
            )
        except nx.NodeNotFound:
            self._reset_path()

    def _reset_path(self) -> None:
        self._path_start = None
        self._path_nodes = set()
        self._path_edges = set()
        if self.mode != "PATH":
            self.stats_panel.set_path_status("")

    # ═══════════════════════════════════════════════════════════════════════
    # Drawing
    # ═══════════════════════════════════════════════════════════════════════

    def draw(self) -> None:
        self.screen.fill((30, 30, 30))

        # ── Background / grid ───────────────────────────────────────────────
        if self.has_image:
            self._draw_bg_image()
        else:
            canvas = self.screen.subsurface(pygame.Rect(0, 0, *self.canvas_size))
            canvas.fill((35, 38, 43))
            self._draw_grid()

        # ── Links ───────────────────────────────────────────────────────────
        for start_idx, end_idx in self.network.links:
            p1 = self._rel_to_screen(self.network.nodes[start_idx]["pos"])
            p2 = self._rel_to_screen(self.network.nodes[end_idx]["pos"])

            in_path = (start_idx, end_idx) in self._path_edges
            color   = _COL_PATH_EDGE if in_path else (200, 0, 0)
            width   = 3             if in_path else 2
            draw_arrow(self.screen, color, p1, p2, 7 if in_path else 6, 5)

        # ── Nodes ───────────────────────────────────────────────────────────
        mouse_pos = pygame.mouse.get_pos()
        for i, node in enumerate(self.network.nodes):
            color, radius = self._node_style(i, mouse_pos)
            sp = self._rel_to_screen(node["pos"])
            pygame.draw.circle(self.screen, color, sp, radius)
            if node["label"]:
                lbl = self.font.render(node["label"], True, (255, 255, 255))
                self.screen.blit(lbl, (sp[0] + 9, sp[1] - 9))

        # ── HUD ─────────────────────────────────────────────────────────────
        self._draw_hud()

        # ── Side panel ──────────────────────────────────────────────────────
        self.stats_panel.update(self.network)
        self.stats_panel.draw(self.screen, x=_CANVAS_W, y=0)

        pygame.display.flip()

    def _node_style(self, idx: int, mouse_pos) -> Tuple[Tuple, int]:
        """Return (color, radius) for node *idx*."""
        if self.mode == "PATH":
            if idx in self._path_edges:   # edge endpoints handled separately
                pass
            if idx == self._path_start:
                return _COL_PATH_SRC, 8
            if idx in self._path_nodes:
                # Distinguish source vs destination vs intermediate
                return _COL_PATH_NODE, 8
        if idx == self.selected_node:
            return (0, 255, 0), 7
        if self.mode == "DELETE" and idx == self._get_node_at(mouse_pos):
            return (255, 80, 80), 7
        return (0, 120, 255), 6

    def _draw_hud(self) -> None:
        mode_colors = {
            "CREATE": (180, 180, 180),
            "DELETE": (80,  220, 80),
            "PATH":   (0,   220, 200),
        }
        color = mode_colors.get(self.mode, (255, 255, 255))
        info  = (
            f"MODO: {self.mode}  |  "
            f"NODOS: {len(self.network.nodes)}  |  "
            f"LINKS: {len(self.network.links)}  |  "
            f"PESO: {self.current_weight}  |  "
            "[R] borrar  [E] etiquetar  [Tab] métrica  [Ctrl+S/O] guardar/abrir"
        )
        t = self.font.render(info, True, color)
        self.screen.blit(t, (10, self.canvas_size[1] - 28))

    def _draw_bg_image(self) -> None:
        cw, ch = self.canvas_size
        src_x  = max(0, int(-self.image_rect.x / self.zoom))
        src_y  = max(0, int(-self.image_rect.y / self.zoom))
        src_w  = min(self.width  - src_x, int(cw / self.zoom) + 2)
        src_h  = min(self.height - src_y, int(ch / self.zoom) + 2)
        dst_x  = max(0, self.image_rect.x)
        dst_y  = max(0, self.image_rect.y)
        dst_w  = min(cw - dst_x, int(src_w * self.zoom))
        dst_h  = min(ch - dst_y, int(src_h * self.zoom))
        if all(v > 0 for v in (src_w, src_h, dst_w, dst_h)):
            try:
                vis = self.bg_image.subsurface(pygame.Rect(src_x, src_y, src_w, src_h))
                self.screen.blit(pygame.transform.scale(vis, (dst_w, dst_h)), (dst_x, dst_y))
            except ValueError:
                pass

    # ═══════════════════════════════════════════════════════════════════════
    # Camera helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _screen_to_rel(self, pos: Tuple[int, int]) -> Tuple[float, float]:
        rx = (pos[0] - self.image_rect.x) / (self.zoom * self.image_rect.width)
        ry = (pos[1] - self.image_rect.y) / (self.zoom * self.image_rect.height)
        return (rx, ry)

    def _rel_to_screen(self, rel_pos) -> Tuple[int, int]:
        if isinstance(rel_pos, dict):
            rel_pos = rel_pos["pos"]
        sx = int(self.image_rect.x + rel_pos[0] * self.zoom * self.image_rect.width)
        sy = int(self.image_rect.y + rel_pos[1] * self.zoom * self.image_rect.height)
        return (sx, sy)

    def _get_node_at(self, mouse_pos: Tuple[int, int]) -> Optional[int]:
        if mouse_pos[0] >= _CANVAS_W:
            return None
        for i, node in enumerate(self.network.nodes):
            sp   = self._rel_to_screen(node["pos"])
            dist = ((mouse_pos[0]-sp[0])**2 + (mouse_pos[1]-sp[1])**2) ** 0.5
            if dist <= 10:
                return i
        return None

    def _handle_zoom(self, button: int, mouse_pos: Tuple[int, int]) -> None:
        rx = (mouse_pos[0] - self.image_rect.x) / (self.zoom * self.image_rect.width)
        ry = (mouse_pos[1] - self.image_rect.y) / (self.zoom * self.image_rect.height)
        factor = 1.05 if button == 4 else 1 / 1.05
        nz     = self.zoom * factor
        if self.min_zoom is not None:
            nz = max(nz, self.min_zoom)
        if self.max_zoom is not None:
            nz = min(nz, self.max_zoom)
        self.zoom = nz
        self.image_rect.x = int(mouse_pos[0] - rx * self.zoom * self.image_rect.width)
        self.image_rect.y = int(mouse_pos[1] - ry * self.zoom * self.image_rect.height)
        self._constrain_boundaries()

    def _handle_mousemotion(self, event: pygame.event.Event) -> None:
        if self.dragging:
            self.image_rect.x = self.offset_start_x + (event.pos[0] - self.mouse_start_x)
            self.image_rect.y = self.offset_start_y + (event.pos[1] - self.mouse_start_y)
            self._constrain_boundaries()

    def _constrain_boundaries(self) -> None:
        cw, ch = self.canvas_size
        if self.image_rect.x > 0:
            self.image_rect.x = 0
        if self.image_rect.y > 0:
            self.image_rect.y = 0
        min_x = cw - self.image_rect.width  * self.zoom
        min_y = ch - self.image_rect.height * self.zoom
        if self.image_rect.x < min_x:
            self.image_rect.x = int(min_x)
        if self.image_rect.y < min_y:
            self.image_rect.y = int(min_y)

    def _load_background(self, img_path: str) -> None:
        self.bg_image = pygame.image.load(img_path).convert()
        self.width, self.height = self.bg_image.get_size()
        self.image_rect = self.bg_image.get_rect()
        self.has_image  = True
        cw, ch          = self.canvas_size
        self.min_zoom   = max(cw / self.width, ch / self.height)
        self.max_zoom   = 15.0
        self.zoom       = self.min_zoom
        self.image_rect.x = self.image_rect.y = 0
        self._constrain_boundaries()

    def _draw_grid(self) -> None:
        import math
        TARGET_PX      = 100
        logical_spacing = TARGET_PX / self.zoom
        magnitude      = 10 ** math.floor(math.log10(logical_spacing))
        n              = logical_spacing / magnitude
        spacing        = magnitude if n < 2 else (2*magnitude if n < 5 else 5*magnitude)
        ss             = spacing * self.zoom
        ox, oy         = self.image_rect.x, self.image_rect.y
        cw, ch         = self.canvas_size

        x = ox + math.floor(-ox / ss) * ss
        while x <= cw:
            pygame.draw.line(self.screen, (50, 53, 58), (int(x), 0), (int(x), ch))
            x += ss
        y = oy + math.floor(-oy / ss) * ss
        while y <= ch:
            pygame.draw.line(self.screen, (50, 53, 58), (0, int(y)), (cw, int(y)))
            y += ss