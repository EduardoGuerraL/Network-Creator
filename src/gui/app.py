from src.core.export import save_project, load_project, migrate_pickle
from src.gui.widgets import get_save_path, get_open_path, ask_node_label, get_image_path
# ── NEW: import the stats panel ────────────────────────────────────────────
from src.gui.stats_panel import StatsPanel
from pygame.locals import (QUIT, MOUSEBUTTONDOWN, MOUSEMOTION, MOUSEBUTTONUP,
                            KEYDOWN, K_n, K_r, K_z, K_s, K_o, K_d, K_e, K_b,
                            K_1, K_2, K_3, K_TAB, KMOD_CTRL)          # K_TAB added
import pygame
from src.core.graph import NetworkManager
from src.utils.geometry import draw_arrow

# Width of the editable canvas (left portion of the window)
_CANVAS_W = 1200


class NetworkApp:
    def __init__(self, img_path=None):
        pygame.init()
        self.clock = pygame.time.Clock()
        self.font  = pygame.font.SysFont("Arial", 18)
        self._cached_zoom       = None
        self._cached_scaled_img = None

        # ── Canvas / image state ────────────────────────────────────────────
        self.has_image = False
        self.min_zoom  = None
        self.max_zoom  = None
        self.zoom      = 1.0
        self.width, self.height = 4000, 3000
        self.bg_image = pygame.Surface((self.width, self.height))
        self.bg_image.fill((35, 38, 43))

        self.hovered_node = None

        # ── Screen setup ────────────────────────────────────────────────────
        # canvas_size governs all viewport / zoom / pan calculations.
        # The actual Pygame window is wider by the side panel.
        self.canvas_size = (_CANVAS_W, 800)
        self.screen_size = (_CANVAS_W + StatsPanel.PANEL_W, 800)  # 1510 × 800

        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("Network Creator")

        self.image_rect = self.bg_image.get_rect()

        # ── Network logic ───────────────────────────────────────────────────
        self.network = NetworkManager()

        # ── UI state ────────────────────────────────────────────────────────
        self.zoom          = 1.0
        self.offset        = [0, 0]
        self.dragging      = False
        self.mode          = "CREATE"
        self.selected_node = None
        self.current_weight = 1

        # ── NEW: side panel ─────────────────────────────────────────────────
        self.stats_panel = StatsPanel()

        # ── Load background image if provided ───────────────────────────────
        if img_path:
            self._load_background(img_path)

    # ═══════════════════════════════════════════════════════════════════════
    # Main loop
    # ═══════════════════════════════════════════════════════════════════════

    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            running = self.handle_events()
            self.draw()
        pygame.quit()

    # ═══════════════════════════════════════════════════════════════════════
    # Event handling
    # ═══════════════════════════════════════════════════════════════════════

    def handle_events(self):
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

    def _handle_keydown(self, event):
        if event.key == K_n:
            self.mode = "CREATE"
        elif event.key == K_r:
            self.mode = "REMOVE" if self.mode != "DELETE" else "CREATE"
        elif event.key == K_e:
            node_idx = self._get_node_at(pygame.mouse.get_pos())
            if node_idx is not None:
                current   = self.network.nodes[node_idx]["label"]
                new_label = ask_node_label(current)
                if new_label is not None:
                    self.network.set_label(node_idx, new_label)

        # ── NEW: cycle stats-panel metric with Tab ──────────────────────────
        elif event.key == K_TAB:
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
                    if path.endswith(".pickle"):
                        self.network = migrate_pickle(path, path.replace(".pickle", ".json"))
                    else:
                        self.network = load_project(path)
            elif event.key == K_b:
                path = get_image_path()
                if path:
                    self._load_background(path)

        if event.key in (K_1, K_2, K_3):
            self.current_weight = int(event.unicode)

    def _handle_mousedown(self, event):
        mouse_pos = event.pos

        # ── NEW: delegate panel-area clicks to the stats panel ──────────────
        if mouse_pos[0] >= _CANVAS_W:
            local_x = mouse_pos[0] - _CANVAS_W
            local_y = mouse_pos[1]
            if event.button == 1:
                self.stats_panel.handle_click(local_x, local_y)
            return   # don't process canvas logic for panel clicks

        # ── Scroll wheel → zoom ─────────────────────────────────────────────
        if event.button in (4, 5):
            self._handle_zoom(event.button, mouse_pos)
            return

        # ── Left click → add / delete node ─────────────────────────────────
        elif event.button == 1:
            rel_pos = self._screen_to_rel(mouse_pos)
            label   = self.network.next_available_label()

            if self.mode == "CREATE":
                self.network.add_node(rel_pos, label=label)
            elif self.mode == "DELETE":
                node_idx = self._get_node_at(mouse_pos)
                if node_idx is not None:
                    self.network.remove_node(node_idx)
                    self.selected_node = None

        # ── Right click → add / deselect link ──────────────────────────────
        elif event.button == 3:
            node_idx = self._get_node_at(mouse_pos)
            if node_idx is not None:
                if self.selected_node is None:
                    self.selected_node = node_idx
                else:
                    self.network.add_link(self.selected_node, node_idx, self.current_weight)
                    self.selected_node = None
            else:
                self.selected_node = None   # deselect on empty click

        # ── Middle click → pan ──────────────────────────────────────────────
        elif event.button == 2:
            self.dragging = True
            self.mouse_start_x,  self.mouse_start_y  = mouse_pos
            self.offset_start_x, self.offset_start_y = self.image_rect.topleft

    # ═══════════════════════════════════════════════════════════════════════
    # Drawing
    # ═══════════════════════════════════════════════════════════════════════

    def draw(self):
        # ── Canvas background ───────────────────────────────────────────────
        self.screen.fill((30, 30, 30))

        if self.has_image:
            cw, ch = self.canvas_size
            src_x = max(0, int(-self.image_rect.x / self.zoom))
            src_y = max(0, int(-self.image_rect.y / self.zoom))
            src_w = min(self.width  - src_x, int(cw / self.zoom) + 2)
            src_h = min(self.height - src_y, int(ch / self.zoom) + 2)
            dst_x = max(0, self.image_rect.x)
            dst_y = max(0, self.image_rect.y)
            dst_w = min(cw - dst_x, int(src_w * self.zoom))
            dst_h = min(ch - dst_y, int(src_h * self.zoom))

            if all(v > 0 for v in (src_w, src_h, dst_w, dst_h)):
                try:
                    visible    = self.bg_image.subsurface(pygame.Rect(src_x, src_y, src_w, src_h))
                    scaled_img = pygame.transform.scale(visible, (dst_w, dst_h))
                    self.screen.blit(scaled_img, (dst_x, dst_y))
                except ValueError:
                    pass
        else:
            # Infinite canvas with dynamic grid
            canvas_surf = self.screen.subsurface(pygame.Rect(0, 0, *self.canvas_size))
            canvas_surf.fill((35, 38, 43))
            self._draw_grid()

        # ── Links ───────────────────────────────────────────────────────────
        for start_idx, end_idx in self.network.links:
            p1 = self._rel_to_screen(self.network.nodes[start_idx]["pos"])
            p2 = self._rel_to_screen(self.network.nodes[end_idx]["pos"])
            draw_arrow(self.screen, (200, 0, 0), p1, p2, 7, 5)

        # ── Nodes + labels ──────────────────────────────────────────────────
        mouse_pos = pygame.mouse.get_pos()
        for i, node in enumerate(self.network.nodes):
            if i == self.selected_node:
                color = (0, 255, 0)
            elif self.mode == "DELETE" and i == self._get_node_at(mouse_pos):
                color = (255, 80, 80)
            else:
                color = (0, 120, 255)

            sp = self._rel_to_screen(node["pos"])
            pygame.draw.circle(self.screen, color, sp, 6)

            if node["label"]:
                lbl = self.font.render(node["label"], True, (255, 255, 255))
                self.screen.blit(lbl, (sp[0] + 9, sp[1] - 9))

        # ── HUD ─────────────────────────────────────────────────────────────
        mode_colors = {"CREATE": (180, 180, 180), "DELETE": (80, 220, 80)}
        hud_color   = mode_colors.get(self.mode, (255, 255, 255))
        info = (
            f"MODO: {self.mode}  |  "
            f"NODOS: {len(self.network.nodes)}  |  "
            f"LINKS: {len(self.network.links)}  |  "
            f"PESO: {self.current_weight}  |  "
            "[R] borrar  [E] etiquetar  [Tab] métrica  [Ctrl+S] guardar  [Ctrl+O] abrir"
        )
        hud = self.font.render(info, True, hud_color)
        self.screen.blit(hud, (10, self.canvas_size[1] - 28))

        # ── NEW: stats panel ─────────────────────────────────────────────────
        self.stats_panel.update(self.network)                        # non-blocking
        self.stats_panel.draw(self.screen, x=_CANVAS_W, y=0)        # blit at right edge

        pygame.display.flip()

    # ═══════════════════════════════════════════════════════════════════════
    # Camera / coordinate helpers
    # ═══════════════════════════════════════════════════════════════════════

    def _screen_to_rel(self, pos):
        rel_x = (pos[0] - self.image_rect.x) / (self.zoom * self.image_rect.width)
        rel_y = (pos[1] - self.image_rect.y) / (self.zoom * self.image_rect.height)
        return (rel_x, rel_y)

    def _rel_to_screen(self, rel_pos):
        if isinstance(rel_pos, dict):
            rel_pos = rel_pos["pos"]
        sx = int(self.image_rect.x + rel_pos[0] * self.zoom * self.image_rect.width)
        sy = int(self.image_rect.y + rel_pos[1] * self.zoom * self.image_rect.height)
        return (sx, sy)

    def _get_node_at(self, mouse_pos):
        # Only consider clicks inside the canvas area
        if mouse_pos[0] >= _CANVAS_W:
            return None
        for i, node in enumerate(self.network.nodes):
            sp   = self._rel_to_screen(node["pos"])
            dist = ((mouse_pos[0] - sp[0]) ** 2 + (mouse_pos[1] - sp[1]) ** 2) ** 0.5
            if dist <= 10:
                return i
        return None

    def _handle_zoom(self, button, mouse_pos):
        rel_x = (mouse_pos[0] - self.image_rect.x) / (self.zoom * self.image_rect.width)
        rel_y = (mouse_pos[1] - self.image_rect.y) / (self.zoom * self.image_rect.height)

        factor   = 1.05 if button == 4 else 1 / 1.05
        new_zoom = self.zoom * factor

        if self.min_zoom is not None:
            new_zoom = max(new_zoom, self.min_zoom)
        if self.max_zoom is not None:
            new_zoom = min(new_zoom, self.max_zoom)

        self.zoom = new_zoom
        self.image_rect.x = int(mouse_pos[0] - rel_x * self.zoom * self.image_rect.width)
        self.image_rect.y = int(mouse_pos[1] - rel_y * self.zoom * self.image_rect.height)
        self._constrain_boundaries()

    def _handle_mousemotion(self, event):
        if self.dragging:
            self.image_rect.x = self.offset_start_x + (event.pos[0] - self.mouse_start_x)
            self.image_rect.y = self.offset_start_y + (event.pos[1] - self.mouse_start_y)
            self._constrain_boundaries()

    def _constrain_boundaries(self):
        """Keep the canvas from drifting out of the visible area."""
        cw, ch = self.canvas_size
        if self.image_rect.x > 0:
            self.image_rect.x = 0
        if self.image_rect.y > 0:
            self.image_rect.y = 0

        min_x = cw - (self.image_rect.width  * self.zoom)
        min_y = ch - (self.image_rect.height * self.zoom)

        if self.image_rect.x < min_x:
            self.image_rect.x = int(min_x)
        if self.image_rect.y < min_y:
            self.image_rect.y = int(min_y)

    def _load_background(self, img_path):
        self.bg_image = pygame.image.load(img_path).convert()
        self.width, self.height = self.bg_image.get_size()
        self.image_rect = self.bg_image.get_rect()

        self.has_image = True
        cw, ch         = self.canvas_size
        self.min_zoom  = max(cw / self.width, ch / self.height)
        self.max_zoom  = 15.0
        self.zoom      = self.min_zoom
        self.image_rect.x = 0
        self.image_rect.y = 0
        self._constrain_boundaries()

    def _draw_grid(self):
        """Adaptive grid for the infinite canvas mode."""
        import math

        TARGET_PX      = 100
        logical_spacing = TARGET_PX / self.zoom
        magnitude      = 10 ** math.floor(math.log10(logical_spacing))
        normalized     = logical_spacing / magnitude

        if normalized < 2:
            spacing = magnitude
        elif normalized < 5:
            spacing = 2 * magnitude
        else:
            spacing = 5 * magnitude

        screen_spacing = spacing * self.zoom
        ox = self.image_rect.x
        oy = self.image_rect.y
        cw, ch = self.canvas_size

        first_col = math.floor(-ox / screen_spacing)
        x = ox + first_col * screen_spacing
        while x <= cw:
            pygame.draw.line(self.screen, (50, 53, 58), (int(x), 0), (int(x), ch))
            x += screen_spacing

        first_row = math.floor(-oy / screen_spacing)
        y = oy + first_row * screen_spacing
        while y <= ch:
            pygame.draw.line(self.screen, (50, 53, 58), (0, int(y)), (cw, int(y)))
            y += screen_spacing