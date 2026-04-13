"""
src/gui/stats_panel.py
──────────────────────
Real-time centrality distribution panel for Network Creator.

Renders a Gaussian KDE of the selected centrality metric as a side panel
inside the Pygame window.  All heavy computation (NetworkX + matplotlib)
runs in a background daemon thread so the UI never freezes.

Drop-in usage in NetworkApp
───────────────────────────
    from src.gui.stats_panel import StatsPanel

    # __init__
    self.stats_panel = StatsPanel()

    # draw()  — called every frame
    self.stats_panel.update(self.network)        # non-blocking
    self.stats_panel.draw(self.screen, x=1200, y=0)

    # handle click (after offsetting mouse_x by canvas width)
    self.stats_panel.handle_click(mouse_x - 1200, mouse_y)

    # cycle metric with Tab key
    self.stats_panel.next_metric()
"""

from __future__ import annotations

import io
import threading
from typing import List, Optional, Tuple

import numpy as np
import pygame

# ── matplotlib: non-interactive Agg backend (must be set before pyplot) ───
import matplotlib
matplotlib.use("Agg")
import matplotlib.figure as mpl_figure   # noqa: E402  (after use())

import networkx as nx

# ═══════════════════════════════════════════════════════════════════════════
# Metrics registry
# ═══════════════════════════════════════════════════════════════════════════

def _safe_eigenvector(G: nx.DiGraph):
    """Eigenvector centrality with graceful fallback for disconnected graphs."""
    try:
        return nx.eigenvector_centrality_numpy(G)
    except Exception:
        # Fallback: degree centrality is always computable
        return nx.degree_centrality(G)


# Each entry: (key, display_label, callable)
METRICS: List[Tuple[str, str, callable]] = [
    ("degree",      "Degree",      nx.degree_centrality),
    ("betweenness", "Betweenness", nx.betweenness_centrality),
    ("closeness",   "Closeness",   nx.closeness_centrality),
    ("eigenvector", "Eigenvector", _safe_eigenvector),
]

# ═══════════════════════════════════════════════════════════════════════════
# Layout constants
# ═══════════════════════════════════════════════════════════════════════════

PANEL_W    = 310           # width of the side panel in pixels
PANEL_H    = 800           # must match app screen height
HEADER_H   = 46            # top bar with title
BTN_H      = 34            # height of each metric button
BTN_GAP    = 6             # gap between buttons
BTN_PAD    = 10            # horizontal padding from panel edge
FOOTER_H   = 32            # bottom status bar

# y-offset where the plot area starts
_PLOT_TOP = HEADER_H + len(METRICS) * (BTN_H + BTN_GAP) + BTN_GAP * 2

# ── Colour palette (matches Network Creator's dark theme) ──────────────────
_BG       = (12,  14,  18)
_DARK     = (22,  26,  33)
_ACCENT   = (0,   255, 200)
_ACCENT2  = (255, 140, 66)    # warm orange for mean line
_TEXT_HI  = (240, 245, 255)
_TEXT_DIM = (90,  100, 115)
_BORDER   = (35,  40,  50)
_GRID     = (26,  30,  38)

# matplotlib hex strings
_MPL_BG     = "#0C0E12"
_MPL_DARK   = "#161A21"
_MPL_ACCENT = "#00FFC8"
_MPL_WARM   = "#FF8C42"
_MPL_DIM    = "#5A6473"
_MPL_GRID   = "#1A1E26"


# ═══════════════════════════════════════════════════════════════════════════
# StatsPanel class
# ═══════════════════════════════════════════════════════════════════════════

class StatsPanel:
    """
    Side panel that displays a real-time KDE of the selected centrality.

    Thread-safety model
    ───────────────────
    The background worker writes to ``self._plot_surf`` under ``self._lock``.
    The main thread reads from it under the same lock only in ``draw()``.
    No other shared state is mutated by the worker.
    """

    # Expose so callers can widen their Pygame window by exactly this amount.
    PANEL_W = PANEL_W

    def __init__(self) -> None:
        self._metric_idx:  int                    = 0
        self._plot_surf:   Optional[pygame.Surface] = None
        self._lock:        threading.Lock         = threading.Lock()
        self._computing:   bool                   = False
        self._dirty:       bool                   = True
        # Snapshot of (n_nodes, n_links, metric_idx) to detect changes cheaply.
        self._prev_state:  Tuple[int, int, int]   = (-1, -1, -1)

        # Fonts are lazy-initialised on first draw() call.
        self._font_title: Optional[pygame.font.Font] = None
        self._font_btn:   Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def current_metric(self) -> Tuple[str, str, callable]:
        """Return the currently selected (key, label, fn) tuple."""
        return METRICS[self._metric_idx]

    def next_metric(self) -> None:
        """Cycle to the next metric (Tab key binding)."""
        self._metric_idx = (self._metric_idx + 1) % len(METRICS)
        self._dirty = True

    def set_metric_by_index(self, idx: int) -> None:
        if 0 <= idx < len(METRICS) and idx != self._metric_idx:
            self._metric_idx = idx
            self._dirty = True

    def handle_click(self, local_x: int, local_y: int) -> bool:
        """
        Process a mouse click at panel-local coordinates.
        Returns True if a metric button was hit and the selection changed.
        """
        for i in range(len(METRICS)):
            if self._btn_rect(i).collidepoint(local_x, local_y):
                self.set_metric_by_index(i)
                return True
        return False

    def update(self, network_manager) -> None:
        """
        Non-blocking update.  Call every frame.  Spawns a worker thread only
        when the network or selected metric has changed since the last render.
        """
        state = (
            len(network_manager.nodes),
            len(network_manager.links),
            self._metric_idx,
        )

        if state != self._prev_state:
            self._dirty     = True
            self._prev_state = state

        if not self._dirty or self._computing:
            return

        # --- Take a thread-safe snapshot of the network data ---------------
        nodes   = list(network_manager.nodes)
        links   = list(network_manager.links)
        weights = list(network_manager.weights)
        metric  = self._metric_idx

        self._computing = True
        thread = threading.Thread(
            target=self._worker,
            args=(nodes, links, weights, metric),
            daemon=True,
        )
        thread.start()

    def draw(self, screen: pygame.Surface, x: int = 1200, y: int = 0) -> None:
        """Blit the complete panel onto *screen* at position (x, y)."""
        self._init_fonts()

        panel = pygame.Surface((PANEL_W, PANEL_H))
        panel.fill(_BG)

        # Separator line on the left edge
        pygame.draw.line(panel, _BORDER, (0, 0), (0, PANEL_H), 2)

        # ── Header ────────────────────────────────────────────────────────
        self._draw_header(panel)

        # ── Metric buttons ────────────────────────────────────────────────
        for i, (_, label, _) in enumerate(METRICS):
            self._draw_button(panel, i, label)

        # ── Plot area ────────────────────────────────────────────────────
        plot_h = PANEL_H - _PLOT_TOP - FOOTER_H
        with self._lock:
            plot_surf = self._plot_surf

        if plot_surf is not None:
            # Smooth-scale the cached matplotlib render to the exact plot area.
            scaled = pygame.transform.smoothscale(plot_surf, (PANEL_W, plot_h))
            panel.blit(scaled, (0, _PLOT_TOP))
        else:
            # Placeholder while thread is running
            status = "Calculando…" if self._computing else "Red vacía"
            msg = self._font_small.render(status, True, _TEXT_DIM)
            panel.blit(
                msg,
                (PANEL_W // 2 - msg.get_width() // 2,
                 _PLOT_TOP + plot_h // 2 - msg.get_height() // 2),
            )

        # ── Footer ───────────────────────────────────────────────────────
        self._draw_footer(panel)

        screen.blit(panel, (x, y))

    # ── Private: UI helpers ────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        if self._font_title is None:
            self._font_title = pygame.font.SysFont("Arial", 15, bold=True)
            self._font_btn   = pygame.font.SysFont("Arial", 12, bold=True)
            self._font_small = pygame.font.SysFont("Arial", 12)

    def _btn_rect(self, idx: int) -> pygame.Rect:
        """Return the Rect for button *idx* in panel-local coords."""
        top = HEADER_H + idx * (BTN_H + BTN_GAP) + BTN_GAP
        return pygame.Rect(BTN_PAD, top, PANEL_W - BTN_PAD * 2, BTN_H)

    def _draw_header(self, surface: pygame.Surface) -> None:
        pygame.draw.rect(surface, _DARK, (0, 0, PANEL_W, HEADER_H))
        pygame.draw.line(surface, _BORDER, (0, HEADER_H - 1), (PANEL_W, HEADER_H - 1))

        title = self._font_title.render("ANÁLISIS DE RED", True, _ACCENT)
        surface.blit(
            title,
            (PANEL_W // 2 - title.get_width() // 2,
             HEADER_H // 2 - title.get_height() // 2),
        )

    def _draw_button(self, surface: pygame.Surface, idx: int, label: str) -> None:
        rect     = self._btn_rect(idx)
        selected = idx == self._metric_idx

        bg_col  = _ACCENT           if selected else _DARK
        br_col  = _ACCENT           if selected else (45, 50, 62)
        tx_col  = _BG               if selected else _TEXT_HI

        pygame.draw.rect(surface, bg_col, rect, border_radius=5)
        pygame.draw.rect(surface, br_col, rect, width=1, border_radius=5)

        txt = self._font_btn.render(label.upper(), True, tx_col)
        surface.blit(
            txt,
            (rect.centerx - txt.get_width() // 2,
             rect.centery - txt.get_height() // 2),
        )

        # Small active indicator dot on the right edge
        if selected:
            cx = rect.right - 10
            cy = rect.centery
            pygame.draw.circle(surface, _BG, (cx, cy), 4)

    def _draw_footer(self, surface: pygame.Surface) -> None:
        n, e, _ = self._prev_state
        fy = PANEL_H - FOOTER_H
        pygame.draw.line(surface, _BORDER, (0, fy), (PANEL_W, fy))

        info = f"nodos: {max(0, n)}   enlaces: {max(0, e)}"
        msg  = self._font_small.render(info, True, _TEXT_DIM)
        surface.blit(
            msg,
            (PANEL_W // 2 - msg.get_width() // 2,
             fy + FOOTER_H // 2 - msg.get_height() // 2),
        )

        # hint
        hint = self._font_small.render("[Tab] cambiar", True, (50, 58, 70))
        surface.blit(hint, (PANEL_W - hint.get_width() - 8, fy + 2))

    # ── Private: background worker ─────────────────────────────────────────

    def _worker(
        self,
        nodes:   list,
        links:   list,
        weights: list,
        metric_idx: int,
    ) -> None:
        """Thread target: compute centrality → render → store surface."""
        try:
            values = self._compute_centrality(nodes, links, weights, metric_idx)
            surf   = self._render_kde(values, metric_idx)
            with self._lock:
                self._plot_surf = surf
                self._dirty     = False
        except Exception as exc:
            print(f"[StatsPanel] worker error ({METRICS[metric_idx][0]}): {exc}")
        finally:
            self._computing = False

    @staticmethod
    def _compute_centrality(
        nodes:   list,
        links:   list,
        weights: list,
        metric_idx: int,
    ) -> List[float]:
        """Build a DiGraph and return a list of centrality values (one per node)."""
        key, label, fn = METRICS[metric_idx]

        G = nx.DiGraph()
        G.add_nodes_from(range(len(nodes)))
        for (s, t), w in zip(links, weights):
            G.add_edge(s, t, weight=w)

        if len(nodes) == 0:
            return []

        try:
            centrality = fn(G)
            return [centrality.get(i, 0.0) for i in range(len(nodes))]
        except Exception as exc:
            print(f"[StatsPanel] centrality fallback ({key}): {exc}")
            # Always-computable fallback
            return list(nx.degree_centrality(G).values())

    # ── Private: rendering ─────────────────────────────────────────────────

    @staticmethod
    def _gaussian_kde(
        data: np.ndarray,
        n_pts: int = 300,
    ) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Pure-NumPy Gaussian KDE — no SciPy dependency.
        Bandwidth selected by Silverman's rule of thumb.

        Returns (x_grid, density) or (None, None) if KDE is not applicable.
        """
        if len(data) < 2:
            return None, None

        std = data.std()
        if std == 0.0:
            return None, None

        n  = len(data)
        bw = 1.06 * std * n ** (-0.2)                     # Silverman

        lo, hi = data.min() - 3 * bw, data.max() + 3 * bw
        x      = np.linspace(lo, hi, n_pts)

        # Vectorised kernel evaluation
        diff = (x[:, None] - data[None, :]) / bw          # (n_pts, n)
        kde  = np.exp(-0.5 * diff ** 2).sum(axis=1)
        kde /= n * bw * np.sqrt(2.0 * np.pi)

        return x, kde

    def _render_kde(
        self,
        values:     List[float],
        metric_idx: int,
    ) -> pygame.Surface:
        """
        Render a matplotlib figure with the KDE and return a pygame.Surface.
        This runs in the background thread.
        """
        _, label, _ = METRICS[metric_idx]

        plot_h  = PANEL_H - _PLOT_TOP - FOOTER_H
        fig_w   = PANEL_W  / 100.0
        fig_h   = plot_h   / 100.0

        fig = mpl_figure.Figure(figsize=(fig_w, fig_h), dpi=100)
        fig.patch.set_facecolor(_MPL_BG)
        ax = fig.add_subplot(111)
        ax.set_facecolor(_MPL_DARK)

        if len(values) >= 2:
            data = np.asarray(values, dtype=float)
            x, kde = self._gaussian_kde(data)

            if kde is not None:
                # Filled area under KDE curve
                ax.fill_between(x, kde, color=_MPL_ACCENT, alpha=0.15)
                ax.plot(x, kde, color=_MPL_ACCENT, linewidth=1.5, zorder=3)

                # Rug plot (individual node markers at y=0)
                ax.plot(
                    data,
                    np.zeros_like(data),
                    "|",
                    color=_MPL_ACCENT,
                    alpha=0.45,
                    markersize=7,
                    zorder=2,
                )

                # Mean vertical line
                mean = float(data.mean())
                ax.axvline(
                    mean,
                    color=_MPL_WARM,
                    linewidth=1.2,
                    linestyle="--",
                    alpha=0.85,
                    label=f"μ = {mean:.3f}",
                    zorder=4,
                )

                # Min / max annotations
                ax.axvline(data.min(), color=_MPL_DIM, linewidth=0.8,
                           linestyle=":", alpha=0.6)
                ax.axvline(data.max(), color=_MPL_DIM, linewidth=0.8,
                           linestyle=":", alpha=0.6)

                leg = ax.legend(
                    fontsize=7,
                    facecolor="#1A1D24",
                    labelcolor=_MPL_WARM,
                    framealpha=0.75,
                    loc="upper right",
                    edgecolor="#2A2D35",
                )
                leg.get_frame().set_linewidth(0.5)

            else:
                # All values identical — single spike
                ax.axvline(values[0], color=_MPL_ACCENT, linewidth=2)
                ax.text(
                    0.5, 0.6,
                    f"valor constante\n{values[0]:.4f}",
                    ha="center", va="center",
                    transform=ax.transAxes,
                    color=_MPL_ACCENT, fontsize=8,
                )

        else:
            # Not enough data
            msg = "Red vacía" if len(values) == 0 else "Solo 1 nodo"
            ax.text(
                0.5, 0.5, msg,
                ha="center", va="center",
                transform=ax.transAxes,
                color=_MPL_DIM, fontsize=9,
            )

        # ── Axis styling ──────────────────────────────────────────────────
        ax.set_title(
            f"{label} centrality  (n={len(values)})",
            color=_MPL_ACCENT,
            fontsize=8,
            pad=4,
            fontweight="bold",
        )
        ax.set_xlabel("valor", color=_MPL_DIM, fontsize=7.5)
        ax.set_ylabel("densidad", color=_MPL_DIM, fontsize=7.5)
        ax.tick_params(colors=_MPL_DIM, labelsize=6.5)
        for spine in ax.spines.values():
            spine.set_color("#252830")
        ax.grid(True, color=_MPL_GRID, linewidth=0.5, alpha=0.7)
        fig.tight_layout(pad=0.5)

        # ── Serialise to pygame Surface via in-memory PNG ─────────────────
        buf = io.BytesIO()
        fig.savefig(
            buf,
            format="png",
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
        )
        buf.seek(0)

        # Close figure explicitly to release matplotlib memory
        import matplotlib.pyplot as _plt
        _plt.close(fig)

        return pygame.image.load(buf, "png").convert()