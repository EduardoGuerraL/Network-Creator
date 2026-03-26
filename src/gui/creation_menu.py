import pygame, random, math
from pygame.locals import *
from src.gui.widgets import get_image_path

def show_creation_menu(screen):
    BG_COLOR = (12, 14, 18)
    ACCENT_COLOR = (0, 255, 200)
    TEXT_COLOR = (240, 245, 255)
    ZONE_COLOR = (22, 26, 33) # Un gris un poco más claro para las cajas
    
    title_font = pygame.font.SysFont("Arial", 40, bold=True)
    font_large = pygame.font.SysFont("Arial", 28, bold=True)
    font_small = pygame.font.SysFont("Arial", 18)

    # --- DEFINICIÓN DE ÁREAS (Layout de 2 columnas) ---
    screen_w, screen_h = screen.get_size()
    center_x = screen_w // 2
    
    # Columna Izquierda (Imagen)
    btn_browse = pygame.Rect(center_x - 450, 250, 400, 60)
    drop_zone = pygame.Rect(center_x - 450, 330, 400, 270)
    
    # Columna Derecha (Lienzo en blanco)
    btn_blank = pygame.Rect(center_x + 50, 250, 400, 350)
    
    # Botón Volver
    btn_back = pygame.Rect(40, 40, 120, 40)

    clock = pygame.time.Clock()
    
    while True:
        mouse_pos = pygame.mouse.get_pos()
        screen.fill(BG_COLOR)

        # --- DIBUJAR INTERFAZ ---
        # Título
        title_surf = title_font.render("CONFIGURACIÓN DEL ENTORNO", True, TEXT_COLOR)
        screen.blit(title_surf, (center_x - title_surf.get_width()//2, 100))

        # 1. Botón Buscar Archivo
        hover_browse = btn_browse.collidepoint(mouse_pos)
        pygame.draw.rect(screen, ACCENT_COLOR if hover_browse else ZONE_COLOR, btn_browse, border_radius=8)
        pygame.draw.rect(screen, ACCENT_COLOR, btn_browse, width=2, border_radius=8)
        txt_browse = font_large.render("Elegir desde el ordenador", True, BG_COLOR if hover_browse else ACCENT_COLOR)
        screen.blit(txt_browse, txt_browse.get_rect(center=btn_browse.center))

        # 2. Zona Drop (Arrastrar y Soltar)
        hover_drop = drop_zone.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (30, 35, 45) if hover_drop else ZONE_COLOR, drop_zone, border_radius=8)
        # Dibujar borde punteado (simulado con un rectángulo sólido por simplicidad, pero con acento)
        pygame.draw.rect(screen, (80, 90, 100), drop_zone, width=2, border_radius=8)
        
        txt_drop1 = font_large.render("Arrastra la imagen aquí", True, (150, 160, 170))
        txt_drop2 = font_small.render("Formatos soportados: JPG, PNG, BMP", True, (100, 110, 120))
        screen.blit(txt_drop1, txt_drop1.get_rect(center=(drop_zone.centerx, drop_zone.centery - 15)))
        screen.blit(txt_drop2, txt_drop2.get_rect(center=(drop_zone.centerx, drop_zone.centery + 20)))

        # 3. Botón Lienzo en Blanco
        hover_blank = btn_blank.collidepoint(mouse_pos)
        pygame.draw.rect(screen, ACCENT_COLOR if hover_blank else ZONE_COLOR, btn_blank, border_radius=8)
        pygame.draw.rect(screen, ACCENT_COLOR, btn_blank, width=2, border_radius=8)
        txt_blank1 = font_large.render("LIENZO EN BLANCO", True, BG_COLOR if hover_blank else ACCENT_COLOR)
        txt_blank2 = font_small.render("Espacio de trabajo infinito", True, BG_COLOR if hover_blank else (150, 160, 170))
        screen.blit(txt_blank1, txt_blank1.get_rect(center=(btn_blank.centerx, btn_blank.centery - 15)))
        screen.blit(txt_blank2, txt_blank2.get_rect(center=(btn_blank.centerx, btn_blank.centery + 20)))

        # 4. Botón Volver
        hover_back = btn_back.collidepoint(mouse_pos)
        pygame.draw.rect(screen, (50, 55, 65) if hover_back else BG_COLOR, btn_back, border_radius=5)
        txt_back = font_small.render("< Volver", True, TEXT_COLOR)
        screen.blit(txt_back, txt_back.get_rect(center=btn_back.center))

        # --- MANEJO DE EVENTOS ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "SALIR"
            
            # Detectar el soltar archivo (Drag & Drop)
            if event.type == pygame.DROPFILE:
                # Comprobamos si el mouse estaba sobre la zona de arrastre al soltar el archivo
                if drop_zone.collidepoint(mouse_pos) or btn_browse.collidepoint(mouse_pos):
                    return event.file # Retorna la ruta del archivo
            
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if btn_back.collidepoint(mouse_pos):
                    return "VOLVER"
                
                if btn_blank.collidepoint(mouse_pos):
                    return "BLANK"
                
                if btn_browse.collidepoint(mouse_pos) or drop_zone.collidepoint(mouse_pos):
                    # Abre la ventana de Tkinter
                    path = get_image_path()
                    if path: 
                        return path # Si eligió algo, lo retorna

        pygame.display.flip()
        clock.tick(60)