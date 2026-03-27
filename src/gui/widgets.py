import tkinter as tk
from tkinter import filedialog, simpledialog
import os

def get_image_path():
    root = tk.Tk()
    root.withdraw()
    root.update()
    root.lift()
    file_path = filedialog.askopenfilename(
        parent=root,
        title="Seleccionar imagen de fondo",
        initialdir=os.getcwd(),
        filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos", "*.*")]
    )
    root.destroy()
    return file_path if file_path else None

def get_save_path(default_name="proyecto"):
    """Retorna ruta .json elegida por el usuario, o None."""
    root = tk.Tk()
    root.withdraw()
    root.update()
    path = filedialog.asksaveasfilename(
        title="Guardar proyecto",
        initialfile=default_name,
        defaultextension=".json",
        filetypes=[("Network JSON", "*.json")]
    )
    root.destroy()
    return path if path else None

def get_open_path():
    """Retorna ruta .json elegida para abrir, o None."""
    root = tk.Tk()
    root.withdraw()
    root.update()
    path = filedialog.askopenfilename(
        title="Abrir proyecto",
        filetypes=[("Network JSON", "*.json"), ("Pickle legacy", "*.pickle")]
    )
    root.destroy()
    return path if path else None

def ask_node_label(current_label=""):
    """Diálogo inline para etiquetar un nodo. Retorna string o None si cancela."""
    root = tk.Tk()
    root.withdraw()
    label = simpledialog.askstring(
        "Etiqueta del nodo",
        "Nombre:",
        initialvalue=current_label
    )
    root.destroy()
    return label  # None si el usuario canceló