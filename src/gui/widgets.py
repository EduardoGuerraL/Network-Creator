import tkinter as tk
from tkinter import filedialog, simpledialog

def get_image_path():
    root = tk.Tk()
    root.withdraw()
    return filedialog.askopenfilename(title="Selecciona la imagen de base")

def get_save_name():
    root = tk.Tk()
    root.withdraw()
    return simpledialog.askstring("Guardar", "Nombre del proyecto:")