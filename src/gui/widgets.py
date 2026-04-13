"""
src/gui/widgets.py
──────────────────
All Tkinter dialogs for Network Creator.

Each function spawns an independent Python subprocess that runs a tiny
Tkinter script. This avoids the Pygame ↔ Tkinter event-loop conflict and
works on all platforms.

New in this version
───────────────────
  ask_ba_params()  — Barabási-Albert parameters  (n, m)
  ask_er_params()  — Erdős-Rényi parameters      (n, p)
  ask_ws_params()  — Watts-Strogatz parameters   (n, k, p)
"""

import subprocess
import sys
import os
import textwrap


# ── Subprocess helper ───────────────────────────────────────────────────────

def _run_dialog(script: str) -> str | None:
    """
    Run *script* in a fresh Python process and return stripped stdout,
    or None if the output is empty (user cancelled).
    """
    result = subprocess.run(
        [sys.executable, "-c", textwrap.dedent(script)],
        capture_output=True,
        text=True,
    )
    out = result.stdout.strip()
    return out if out else None


# ── Existing dialogs (unchanged) ────────────────────────────────────────────

def get_image_path() -> str | None:
    return _run_dialog(f"""
        import tkinter as tk
        from tkinter import filedialog
        import os
        root = tk.Tk(); root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Seleccionar imagen de fondo',
            initialdir=os.getcwd(),
            filetypes=[('Imágenes', '*.png *.jpg *.jpeg *.bmp'), ('Todos', '*.*')]
        )
        print(path)
    """)


def get_save_path(default_name: str = "proyecto") -> str | None:
    return _run_dialog(f"""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.asksaveasfilename(
            title='Guardar proyecto',
            initialfile='{default_name}',
            defaultextension='.json',
            filetypes=[('Network JSON', '*.json')]
        )
        print(path)
    """)


def get_open_path() -> str | None:
    return _run_dialog("""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk(); root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Abrir proyecto',
            filetypes=[('Network JSON', '*.json'), ('Pickle legacy', '*.pickle')]
        )
        print(path)
    """)


def ask_node_label(current_label: str = "") -> str | None:
    return _run_dialog(f"""
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk(); root.withdraw()
        root.attributes('-topmost', True)
        label = simpledialog.askstring(
            'Etiqueta del nodo', 'Nombre:',
            initialvalue='{current_label}'
        )
        print(label or '')
    """)


# ── New: network generator parameter dialogs ────────────────────────────────

def ask_ba_params() -> tuple[int, int] | None:
    """
    Ask for Barabási-Albert parameters.

    Returns
    -------
    (n, m) on success, None if the user cancelled.
    """
    raw = _run_dialog("""
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk(); root.withdraw()
        root.attributes('-topmost', True)

        n = simpledialog.askinteger(
            'Barabási-Albert', 'Número de nodos (n):',
            initialvalue=30, minvalue=5, maxvalue=1000
        )
        if n is None:
            print('')
        else:
            m = simpledialog.askinteger(
                'Barabási-Albert', f'Conexiones por nuevo nodo (m < {n}):',
                initialvalue=2, minvalue=1, maxvalue=n - 1
            )
            print(f'{n},{m}' if m else '')
    """)
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def ask_er_params() -> tuple[int, float] | None:
    """
    Ask for Erdős-Rényi parameters.

    Returns
    -------
    (n, p) on success, None if cancelled.
    """
    raw = _run_dialog("""
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk(); root.withdraw()
        root.attributes('-topmost', True)

        n = simpledialog.askinteger(
            'Erdős-Rényi', 'Número de nodos (n):',
            initialvalue=30, minvalue=2, maxvalue=1000
        )
        if n is None:
            print('')
        else:
            p = simpledialog.askfloat(
                'Erdős-Rényi', 'Probabilidad de enlace (0 < p < 1):',
                initialvalue=0.15, minvalue=0.001, maxvalue=0.999
            )
            print(f'{n},{p}' if p is not None else '')
    """)
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 2:
        return None
    try:
        return int(parts[0]), float(parts[1])
    except ValueError:
        return None


def ask_ws_params() -> tuple[int, int, float] | None:
    """
    Ask for Watts-Strogatz parameters.

    Returns
    -------
    (n, k, p) on success, None if cancelled.
    """
    raw = _run_dialog("""
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk(); root.withdraw()
        root.attributes('-topmost', True)

        n = simpledialog.askinteger(
            'Watts-Strogatz', 'Número de nodos (n):',
            initialvalue=30, minvalue=4, maxvalue=1000
        )
        if n is None:
            print('')
        else:
            k = simpledialog.askinteger(
                'Watts-Strogatz',
                'Vecinos por nodo (k, par, k < n):',
                initialvalue=4, minvalue=2, maxvalue=n - 1
            )
            if k is None:
                print('')
            else:
                p = simpledialog.askfloat(
                    'Watts-Strogatz', 'Probabilidad de rewiring (0 ≤ p ≤ 1):',
                    initialvalue=0.2, minvalue=0.0, maxvalue=1.0
                )
                print(f'{n},{k},{p}' if p is not None else '')
    """)
    if not raw:
        return None
    parts = raw.split(",")
    if len(parts) != 3:
        return None
    try:
        return int(parts[0]), int(parts[1]), float(parts[2])
    except ValueError:
        return None