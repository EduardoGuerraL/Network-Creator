from src.gui.app import NetworkApp, show_initial_splash
from src.gui.widgets import get_image_path

if __name__ == "__main__":
    # 1. Primero la portada (ventana sin bordes)
    show_initial_splash()
    
    # 2. Luego pedimos la imagen
    img_path = get_image_path()
    
    # 3. Finalmente abrimos la herramienta de trabajo
    if img_path:
        app = NetworkApp(img_path)
        app.run()