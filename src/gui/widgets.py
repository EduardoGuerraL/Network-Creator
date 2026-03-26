import tkinter as tk
from tkinter import filedialog, simpledialog
import os

def get_image_path():
    root = tk.Tk()
    root.withdraw() # Oculta la ventana principal de TK
    
    # --- TRUCO PARA LINUX/UBUNTU ---
    root.update() # Procesa eventos pendientes
    root.lift()   # Trae la instancia al frente
    
    # Forzar que la ventana sea "modal" y esté encima de todo
    file_path = filedialog.askopenfilename(
        parent=root,
        title="Seleccionar imagen de fondo",
        initialdir=os.getcwd(),
        filetypes=[("Imágenes", "*.png *.jpg *.jpeg *.bmp"), ("Todos", "*.*")]
    )
    
    root.destroy()
    return file_path if file_path else None

def get_save_name():
    root = tk.Tk()
    root.withdraw()
    return simpledialog.askstring("Guardar", "Nombre del proyecto:")