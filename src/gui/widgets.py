import subprocess
import sys
import os
import textwrap
from tkinter import filedialog, simpledialog

def _run_dialog(script):
    result = subprocess.run(
        [sys.executable, '-c', textwrap.dedent(script)],
        capture_output=True, text=True
    )
    path = result.stdout.strip()
    return path if path else None

def get_image_path():
    return _run_dialog(f"""
        import tkinter as tk
        from tkinter import filedialog
        import os
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Seleccionar imagen de fondo',
            initialdir=os.getcwd(),
            filetypes=[('Imágenes', '*.png *.jpg *.jpeg *.bmp'), ('Todos', '*.*')]
        )
        print(path)
    """)

def get_save_path(default_name="proyecto"):
    return _run_dialog(f"""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.asksaveasfilename(
            title='Guardar proyecto',
            initialfile='{default_name}',
            defaultextension='.json',
            filetypes=[('Network JSON', '*.json')]
        )
        print(path)
    """)

def get_open_path():
    return _run_dialog("""
        import tkinter as tk
        from tkinter import filedialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        path = filedialog.askopenfilename(
            title='Abrir proyecto',
            filetypes=[('Network JSON', '*.json'), ('Pickle legacy', '*.pickle')]
        )
        print(path)
    """)

def ask_node_label(current_label=""):
    return _run_dialog(f"""
        import tkinter as tk
        from tkinter import simpledialog
        root = tk.Tk()
        root.withdraw()
        root.attributes('-topmost', True)
        label = simpledialog.askstring('Etiqueta del nodo', 'Nombre:', initialvalue='{current_label}')
        print(label or '')
    """)