"""
src/gui/stats_panel.py
──────────────────────
Side panel for Network Creator (310 × 800 px).

Layout (two vertical halves)
─────────────────────────────
  TOP — analytics
    • Header bar
    • Compact metric selector (4 horizontal buttons)
    • Real-time KDE density plot  (background thread)

  BOTTOM — controls
    • Network generator  (BA / ER / WS  ×  Random / Parametrised)
    • Shortest-path mode toggle + status
    • Quick graph statistics

Thread-safety
─────────────
The background worker writes only to ``_plot_surf`` (under ``_lock``).
The main thread reads it in draw().  No other shared mutation occurs.

Action protocol
───────────────
``handle_click(local_x, local_y)`` returns either ``None`` or a dict:

  {"type": "generate", "model": "ba"|"er"|"ws", "mode": "random"|"params"}
  {"type": "toggle_path", "active": bool}

The caller (NetworkApp) interprets and executes these actions.
"""

from __future__ import annotations

import io
import threading
from typing import Dict, List, Optional, Tuple

import numpy as np
import pygame

import matplotlib
matplotlib.use("Agg")
import matplotlib.figure as mpl_figure

import networkx as nx

# ═══════════════════════════════════════════════════════════════════════════
# Centrality metrics registry
# ═══════════════════════════════════════════════════════════════════════════

def _safe_eigenvector(G: nx.DiGraph):
    try:
        return nx.eigenvector_centrality_numpy(G)
    except Exception:
        return nx.degree_centrality(G)


METRICS: List[Tuple[str, str, callable]] = [
    ("degree",      "Degree",   nx.degree_centrality),
    ("betweenness", "Between",  nx.betweenness_centrality),
    ("closeness",   "Closeness",nx.closeness_centrality),
    ("eigenvector", "Eigenvec", _safe_eigenvector),
]

# ═══════════════════════════════════════════════════════════════════════════
# Panel dimensions & layout y-positions
# ═══════════════════════════════════════════════════════════════════════════

PANEL_W = 310
PANEL_H = 800

_Y_HEADER   = 0;    _H_HEADER   = 36
_Y_METRICS  = 36;   _H_METRICS  = 30
_Y_PLOT     = 72;   _H_PLOT     = 298   # ends at 370
_Y_SEP1     = 374
_Y_GEN_LBL  = 378;  _H_GEN_LBL  = 20
_Y_MDL_BTNS = 400;  _H_MDL_BTNS = 30   # BA / ER / WS
_Y_MOD_BTNS = 434;  _H_MOD_BTNS = 30   # Random / Params
_Y_SEP2     = 470
_Y_PATH_LBL = 474;  _H_PATH_LBL = 20
_Y_PATH_TOG = 496;  _H_PATH_TOG = 32
_Y_PATH_STA = 532;  _H_PATH_STA = 56
_Y_SEP3     = 594
_Y_QS_LBL   = 598;  _H_QS_LBL   = 20
_Y_QS_ROWS  = 620;  _H_QS_ROW   = 20
_Y_FOOTER   = 770;  _H_FOOTER   = 30

_BTN_PAD = 8

# ═══════════════════════════════════════════════════════════════════════════
# Colour palette (matches Network Creator dark theme)
# ═══════════════════════════════════════════════════════════════════════════

_BG      = (12,  14,  18)
_DARK    = (20,  23,  30)
_DARKER  = (16,  19,  24)
_ACCENT  = (0,   255, 200)
_WARM    = (255, 140, 66)
_GREEN   = (60,  210, 110)
_RED     = (220, 70,  70)
_TEXT_HI = (240, 245, 255)
_TEXT_DIM= (85,  98,  115)
_BORDER  = (32,  37,  48)
_SEP     = (30,  34,  44)

_MPL_BG     = "#0C0E12"
_MPL_DARK   = "#14171E"
_MPL_ACCENT = "#00FFC8"
_MPL_WARM   = "#FF8C42"
_MPL_DIM    = "#556070"
_MPL_GRID   = "#181D26"

# ── Generation model definitions ───────────────────────────────────────────
_GEN_MODELS: List[Tuple[str, str]] = [
    ("ba", "BA"),
    ("er", "ER"),
    ("ws", "WS"),
]


# ═══════════════════════════════════════════════════════════════════════════
# StatsPanel
# ═══════════════════════════════════════════════════════════════════════════

class StatsPanel:
    """Full side panel: analytics (top) + controls (bottom)."""

    PANEL_W = PANEL_W

    def __init__(self) -> None:
        # Analytics
        self._metric_idx:  int                      = 0
        self._plot_surf:   Optional[pygame.Surface] = None
        self._lock                                  = threading.Lock()
        self._computing:   bool                     = False
        self._dirty:       bool                     = True
        self._prev_state:  Tuple[int, int, int]     = (-1, -1, -1)

        # Generation
        self._gen_model:      str = "ba"
        self._last_gen_label: str = ""

        # Shortest path
        self._path_active: bool = False
        self._path_status: str  = ""
        self._path_error:  bool = False

        # Quick stats
        self._qs_lines: List[str] = []

        # Fonts (lazy init)
        self._font_hdr:   Optional[pygame.font.Font] = None
        self._font_lbl:   Optional[pygame.font.Font] = None
        self._font_btn:   Optional[pygame.font.Font] = None
        self._font_small: Optional[pygame.font.Font] = None

    # ── Public API ─────────────────────────────────────────────────────────

    @property
    def path_active(self) -> bool:
        return self._path_active

    def set_path_status(self, msg: str, error: bool = False) -> None:
        """NetworkApp calls this to update the path-mode status line."""
        self._path_status = msg
        self._path_error  = error

    def set_last_gen_label(self, label: str) -> None:
        """NetworkApp calls this after a successful generation."""
        self._last_gen_label = label

    def next_metric(self) -> None:
        """Cycle to next centrality metric (Tab key)."""
        self._metric_idx = (self._metric_idx + 1) % len(METRICS)
        self._dirty = True

    def handle_click(self, lx: int, ly: int) -> Optional[Dict]:
        """
        Dispatch a panel-local click. Returns an action dict or None.

        Returned action types
        ─────────────────────
          {"type": "generate", "model": str, "mode": "random"|"params"}
          {"type": "toggle_path", "active": bool}
        """
        # Metric selector
        for i in range(len(METRICS)):
            if self._metric_btn_rect(i).collidepoint(lx, ly):
                if i != self._metric_idx:
                    self._metric_idx = i
                    self._dirty = True
                return None

        # Generator model selector
        for i, (key, _) in enumerate(_GEN_MODELS):
            if self._model_btn_rect(i).collidepoint(lx, ly):
                self._gen_model = key
                return None

        # Generator launch buttons
        if self._mode_btn_rect(0).collidepoint(lx, ly):
            return {"type": "generate", "model": self._gen_model, "mode": "random"}
        if self._mode_btn_rect(1).collidepoint(lx, ly):
            return {"type": "generate", "model": self._gen_model, "mode": "params"}

        # Path toggle
        if self._path_toggle_rect().collidepoint(lx, ly):
            self._path_active = not self._path_active
            if not self._path_active:
                self._path_status = ""
                self._path_error  = False
            return {"type": "toggle_path", "active": self._path_active}

        return None

    def update(self, network_manager) -> None:
        """Non-blocking update. Call every frame."""
        state = (
            len(network_manager.nodes),
            len(network_manager.links),
            self._metric_idx,
        )
        if state != self._prev_state:
            self._dirty      = True
            self._prev_state = state
            self._refresh_quick_stats(network_manager)

        if not self._dirty or self._computing:
            return

        nodes   = list(network_manager.nodes)
        links   = list(network_manager.links)
        weights = list(network_manager.weights)
        metric  = self._metric_idx

        self._computing = True
        threading.Thread(
            target=self._worker,
            args=(nodes, links, weights, metric),
            daemon=True,
        ).start()

    def draw(self, screen: pygame.Surface, x: int = 1200, y: int = 0) -> None:
        """Blit the complete panel at (x, y) on screen."""
        self._init_fonts()
        surf = pygame.Surface((PANEL_W, PANEL_H))
        surf.fill(_BG)
        pygame.draw.line(surf, _BORDER, (0, 0), (0, PANEL_H), 2)

        self._draw_header(surf)
        self._draw_metrics_row(surf)
        self._draw_plot_area(surf)
        self._draw_sep(surf, _Y_SEP1)
        self._draw_generation_section(surf)
        self._draw_sep(surf, _Y_SEP2)
        self._draw_path_section(surf)
        self._draw_sep(surf, _Y_SEP3)
        self._draw_quick_stats(surf)
        self._draw_footer(surf)

        screen.blit(surf, (x, y))

    # ── Geometry helpers ───────────────────────────────────────────────────

    def _metric_btn_rect(self, idx: int) -> pygame.Rect:
        avail = PANEL_W - _BTN_PAD * 2
        bw    = (avail - 3 * 4) // 4
        return pygame.Rect(_BTN_PAD + idx * (bw + 4), _Y_METRICS, bw, _H_METRICS)

    def _model_btn_rect(self, idx: int) -> pygame.Rect:
        avail = PANEL_W - _BTN_PAD * 2
        bw    = (avail - 2 * 4) // 3
        return pygame.Rect(_BTN_PAD + idx * (bw + 4), _Y_MDL_BTNS, bw, _H_MDL_BTNS)

    def _mode_btn_rect(self, idx: int) -> pygame.Rect:
        half = (PANEL_W - _BTN_PAD * 2 - 6) // 2
        return pygame.Rect(_BTN_PAD + idx * (half + 6), _Y_MOD_BTNS, half, _H_MOD_BTNS)

    def _path_toggle_rect(self) -> pygame.Rect:
        return pygame.Rect(_BTN_PAD, _Y_PATH_TOG, PANEL_W - _BTN_PAD * 2, _H_PATH_TOG)

    # ── Drawing ────────────────────────────────────────────────────────────

    def _init_fonts(self) -> None:
        if self._font_hdr is None:
            self._font_hdr   = pygame.font.SysFont("Arial", 14, bold=True)
            self._font_lbl   = pygame.font.SysFont("Arial", 11, bold=True)
            self._font_btn   = pygame.font.SysFont("Arial", 11, bold=True)
            self._font_small = pygame.font.SysFont("Arial", 11)

    def _draw_header(self, s: pygame.Surface) -> None:
        pygame.draw.rect(s, _DARKER, (0, 0, PANEL_W, _H_HEADER))
        pygame.draw.line(s, _BORDER, (0, _H_HEADER - 1), (PANEL_W, _H_HEADER - 1))
        t = self._font_hdr.render("ANÁLISIS DE RED", True, _ACCENT)
        s.blit(t, (PANEL_W // 2 - t.get_width() // 2,
                   _H_HEADER // 2 - t.get_height() // 2))

    def _draw_metrics_row(self, s: pygame.Surface) -> None:
        for i, (_, lbl, _) in enumerate(METRICS):
            r   = self._metric_btn_rect(i)
            sel = i == self._metric_idx
            pygame.draw.rect(s, _ACCENT if sel else _DARK, r, border_radius=4)
            pygame.draw.rect(s, _ACCENT if sel else _BORDER, r, width=1, border_radius=4)
            t = self._font_btn.render(lbl[:8].upper(), True, _BG if sel else _TEXT_HI)
            s.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))

    def _draw_plot_area(self, s: pygame.Surface) -> None:
        with self._lock:
            plot = self._plot_surf
        if plot is not None:
            s.blit(pygame.transform.smoothscale(plot, (PANEL_W, _H_PLOT)), (0, _Y_PLOT))
        else:
            msg = "Calculando…" if self._computing else "Sin datos"
            t = self._font_small.render(msg, True, _TEXT_DIM)
            s.blit(t, (PANEL_W//2 - t.get_width()//2,
                       _Y_PLOT + _H_PLOT//2 - t.get_height()//2))

    def _draw_sep(self, s: pygame.Surface, y: int) -> None:
        pygame.draw.line(s, _SEP, (0, y), (PANEL_W, y))

    def _draw_section_label(self, s: pygame.Surface, text: str, y: int, h: int) -> None:
        t = self._font_lbl.render(text, True, _TEXT_DIM)
        s.blit(t, (_BTN_PAD, y + (h - t.get_height()) // 2))

    def _draw_generation_section(self, s: pygame.Surface) -> None:
        self._draw_section_label(s, "─ GENERACIÓN DE REDES", _Y_GEN_LBL, _H_GEN_LBL)

        # Model buttons (BA / ER / WS)
        for i, (key, lbl) in enumerate(_GEN_MODELS):
            r   = self._model_btn_rect(i)
            sel = key == self._gen_model
            pygame.draw.rect(s, _WARM if sel else _DARK, r, border_radius=4)
            pygame.draw.rect(s, _WARM if sel else _BORDER, r, width=1, border_radius=4)
            t = self._font_btn.render(lbl, True, _BG if sel else _TEXT_HI)
            s.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))

        # Action buttons (Aleatorio / Parámetros)
        for i, lbl in enumerate(("Aleatorio", "Parámetros")):
            r = self._mode_btn_rect(i)
            pygame.draw.rect(s, _DARK, r, border_radius=4)
            pygame.draw.rect(s, _BORDER, r, width=1, border_radius=4)
            t = self._font_btn.render(lbl, True, _TEXT_HI)
            s.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))

        # Last generation info line
        if self._last_gen_label:
            t = self._font_small.render(f"↑ {self._last_gen_label[:36]}", True, (70, 160, 120))
            s.blit(t, (_BTN_PAD, _Y_MOD_BTNS + _H_MOD_BTNS + 5))

    def _draw_path_section(self, s: pygame.Surface) -> None:
        self._draw_section_label(s, "─ CAMINO MÁS CORTO", _Y_PATH_LBL, _H_PATH_LBL)

        r      = self._path_toggle_rect()
        active = self._path_active
        bg     = _GREEN if active else _DARK
        br     = _GREEN if active else _BORDER
        label  = "● Modo activo  (clic en nodos)" if active else "○ Activar modo camino"
        pygame.draw.rect(s, bg, r, border_radius=5)
        pygame.draw.rect(s, br, r, width=1, border_radius=5)
        t = self._font_btn.render(label, True, _BG if active else _TEXT_HI)
        s.blit(t, (r.centerx - t.get_width()//2, r.centery - t.get_height()//2))

        if self._path_status:
            col = _RED if self._path_error else (140, 220, 180)
            # Simple word-wrap over max ~36 chars per line
            words, lines, cur = self._path_status.split(), [], []
            max_w = PANEL_W - _BTN_PAD * 2
            for w in words:
                test = " ".join(cur + [w])
                if self._font_small.size(test)[0] > max_w and cur:
                    lines.append(" ".join(cur)); cur = [w]
                else:
                    cur.append(w)
            if cur:
                lines.append(" ".join(cur))
            for li, line in enumerate(lines[:3]):
                t2 = self._font_small.render(line, True, col)
                s.blit(t2, (_BTN_PAD, _Y_PATH_STA + li * 18))

    def _draw_quick_stats(self, s: pygame.Surface) -> None:
        self._draw_section_label(s, "─ MÉTRICAS RÁPIDAS", _Y_QS_LBL, _H_QS_LBL)
        for i, line in enumerate(self._qs_lines[:4]):
            t = self._font_small.render(line, True, _TEXT_DIM)
            s.blit(t, (_BTN_PAD, _Y_QS_ROWS + i * (_H_QS_ROW + 2)))

    def _draw_footer(self, s: pygame.Surface) -> None:
        n, e, _ = self._prev_state
        pygame.draw.line(s, _SEP, (0, _Y_FOOTER), (PANEL_W, _Y_FOOTER))
        t = self._font_small.render(
            f"nodos: {max(0,n)}   enlaces: {max(0,e)}", True, _TEXT_DIM)
        s.blit(t, (PANEL_W//2 - t.get_width()//2,
                   _Y_FOOTER + _H_FOOTER//2 - t.get_height()//2))
        hint = self._font_small.render("[Tab] métrica", True, (42, 50, 64))
        s.blit(hint, (PANEL_W - hint.get_width() - 6, _Y_FOOTER + 2))

    # ── Quick stats (main thread) ──────────────────────────────────────────

    def _refresh_quick_stats(self, nm) -> None:
        n, e = len(nm.nodes), len(nm.links)
        if n == 0:
            self._qs_lines = ["red vacía"]
            return
        density = e / (n * (n - 1)) if n > 1 else 0.0
        avg_deg = (2 * e / n) if n > 0 else 0.0
        in_degs = [0] * n
        for s_idx, t_idx in nm.links:
            if 0 <= t_idx < n:
                in_degs[t_idx] += 1
        max_hub = max(in_degs) if in_degs else 0
        self._qs_lines = [
            f"densidad:   {density:.4f}",
            f"grado med:  {avg_deg:.2f}",
            f"hub máx:    {max_hub} ent.",
        ]

    # ── Background worker ──────────────────────────────────────────────────

    def _worker(self, nodes, links, weights, metric_idx: int) -> None:
        try:
            values = _compute_centrality(nodes, links, weights, metric_idx)
            surf   = _render_kde(values, metric_idx, PANEL_W, _H_PLOT)
            with self._lock:
                self._plot_surf = surf
                self._dirty     = False
        except Exception as exc:
            print(f"[StatsPanel] worker error: {exc}")
        finally:
            self._computing = False


# ═══════════════════════════════════════════════════════════════════════════
# Module-level helpers (run in worker thread or main thread)
# ═══════════════════════════════════════════════════════════════════════════

def _compute_centrality(nodes, links, weights, metric_idx: int) -> List[float]:
    _, _, fn = METRICS[metric_idx]
    G = nx.DiGraph()
    G.add_nodes_from(range(len(nodes)))
    for (s, t), w in zip(links, weights):
        G.add_edge(s, t, weight=w)
    if not nodes:
        return []
    try:
        return [float(v) for v in fn(G).values()]
    except Exception:
        return [float(v) for v in nx.degree_centrality(G).values()]


def _gaussian_kde(data: np.ndarray, n_pts: int = 300):
    if len(data) < 2:
        return None, None
    std = data.std()
    if std == 0.0:
        return None, None
    n  = len(data)
    bw = 1.06 * std * n ** (-0.2)
    x  = np.linspace(data.min() - 3*bw, data.max() + 3*bw, n_pts)
    diff = (x[:, None] - data[None, :]) / bw
    kde  = np.exp(-0.5 * diff**2).sum(axis=1)
    kde /= n * bw * np.sqrt(2.0 * np.pi)
    return x, kde


def _render_kde(
    values: List[float], metric_idx: int, w_px: int, h_px: int
) -> pygame.Surface:
    """Render a matplotlib KDE figure → pygame.Surface. Runs in worker thread."""
    import matplotlib.pyplot as _plt
    _, label, _ = METRICS[metric_idx]

    fig = mpl_figure.Figure(figsize=(w_px/100, h_px/100), dpi=100)
    fig.patch.set_facecolor(_MPL_BG)
    ax = fig.add_subplot(111)
    ax.set_facecolor(_MPL_DARK)

    if len(values) >= 2:
        data = np.asarray(values, dtype=float)
        x, kde = _gaussian_kde(data)
        if kde is not None:
            ax.fill_between(x, kde, color=_MPL_ACCENT, alpha=0.12)
            ax.plot(x, kde, color=_MPL_ACCENT, linewidth=1.5, zorder=3)
            ax.plot(data, np.zeros_like(data), "|",
                    color=_MPL_ACCENT, alpha=0.5, markersize=7, zorder=2)
            mean = float(data.mean())
            ax.axvline(mean, color=_MPL_WARM, linewidth=1.2, linestyle="--",
                       alpha=0.85, label=f"μ={mean:.3f}", zorder=4)
            ax.axvline(data.min(), color=_MPL_DIM, lw=0.7, ls=":", alpha=0.5)
            ax.axvline(data.max(), color=_MPL_DIM, lw=0.7, ls=":", alpha=0.5)
            leg = ax.legend(fontsize=7, facecolor="#1A1D24",
                            labelcolor=_MPL_WARM, framealpha=0.75,
                            loc="upper right", edgecolor="#2A2D35")
            leg.get_frame().set_linewidth(0.5)
        else:
            ax.axvline(values[0], color=_MPL_ACCENT, linewidth=2)
            ax.text(0.5, 0.55, f"cte = {values[0]:.4f}", ha="center",
                    transform=ax.transAxes, color=_MPL_ACCENT, fontsize=8)
    else:
        ax.text(0.5, 0.5, "red vacía" if not values else "1 nodo",
                ha="center", va="center", transform=ax.transAxes,
                color=_MPL_DIM, fontsize=9)

    ax.set_title(f"{label} centrality  (n={len(values)})",
                 color=_MPL_ACCENT, fontsize=8, pad=3, fontweight="bold")
    ax.set_xlabel("valor",    color=_MPL_DIM, fontsize=7)
    ax.set_ylabel("densidad", color=_MPL_DIM, fontsize=7)
    ax.tick_params(colors=_MPL_DIM, labelsize=6)
    for sp in ax.spines.values():
        sp.set_color("#252830")
    ax.grid(True, color=_MPL_GRID, linewidth=0.5, alpha=0.7)
    fig.tight_layout(pad=0.5)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight",
                facecolor=fig.get_facecolor())
    buf.seek(0)
    _plt.close(fig)
    return pygame.image.load(buf, "png").convert()