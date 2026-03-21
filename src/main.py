# main.py
from src.gui.app import NetworkApp
from src.gui.widgets import get_image_path

if __name__ == "__main__":
    img_path = get_image_path()
    if img_path:
        app = NetworkApp(img_path)
        app.run()