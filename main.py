from src.gui.app import NetworkApp, show_initial_splash
from src.gui.menu import show_main_menu, show_creation_menu
from src.gui.widgets import get_image_path
import pygame
import sys
import os

def main():
    pygame.init()
    os.environ['SDL_VIDEO_CENTERED'] = '1'
    
    # --- PASO 1: Tamaño de Portada (Pequeño y sin bordes) ---
    splash_size = (800, 300)
    screen = pygame.display.set_mode(splash_size, pygame.NOFRAME)
    show_initial_splash(screen)


    # --- PASO 2: Cambio al Tamaño de Menú (Grande y con bordes) ---
    # Al llamar a set_mode de nuevo, la ventana se agranda y recupera la barra superior
    menu_size = (1200, 800) 
    screen = pygame.display.set_mode(menu_size, pygame.NOFRAME) 
    pygame.display.set_caption("Network Creator - Main Menu")


    # 3. Bucle del Menú (Escena 2)
    while True:
        # El menú toma el control y nos devuelve qué botón presionó el usuario
        choice = show_main_menu(screen)
        
        if choice == "CREAR RED NUEVA":
            resultado = show_creation_menu(screen)
            
            if resultado == "SALIR":
                break
            elif resultado == "VOLVER":
                continue
            else:
                # Si no es VOLVER ni SALIR, 'resultado' contiene "BLANK" o la ruta del archivo.
                img_path = None if resultado == "BLANK" else resultado
                
                # Lanzamos la aplicación
                app = NetworkApp(img_path)
                app.run()
                
                # Al cerrar la red, restauramos la pantalla del menú
                screen = pygame.display.set_mode((1200, 800))
        
        elif choice == "CONTINUAR RED GUARDADA":
            # Aquí iría la lógica para cargar el archivo .pickle o .json
            print("Funcionalidad en construcción: Cargar red")
            
        elif choice == "INSTRUCCIONES":
            # Aquí llamaremos a una escena de instrucciones
            print("Funcionalidad en construcción: Instrucciones")
            
        elif choice == "SALIR":
            break

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()