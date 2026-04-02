from src.gui.app import NetworkApp
from src.gui.splash import show_initial_splash
from src.gui.main_menu import show_main_menu
from src.gui.creation_menu import show_creation_menu
from src.gui.widgets import get_image_path
import pygame
import sys
import os

def main():
    pygame.init()
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    splash_size = (800, 300)
    screen = pygame.display.set_mode(splash_size, pygame.NOFRAME)
    show_initial_splash(screen)


    # --- PASO 2: Cambio al Tamaño de Menú (Grande y con bordes) ---
    # Al llamar a set_mode de nuevo, la ventana se agranda y recupera la barra superior
    menu_size = (1200, 800) 
    screen = pygame.display.set_mode(menu_size, pygame.NOFRAME) 
    pygame.display.set_caption("Network Creator - Main Menu")

    # Lanzamos la aplicación
    app = NetworkApp()
    app.run()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()