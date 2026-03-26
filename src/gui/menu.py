import pygame
import random
import math
import datetime
from .widgets import get_image_path

def show_main_menu(screen):
  # --- Configuración de Estilo ---
    BG_COLOR = (12, 14, 18)
    ACCENT_COLOR = (0, 255, 200)
    TEXT_COLOR = (240, 245, 255)
    METADATA_COLOR = (80, 90, 100) # Gris tenue para datos de versión
    
    option_font = pygame.font.SysFont("Arial", 22)
    info_font = pygame.font.SysFont("Monospace", 14) # Fuente tipo consola para autoría

    # --- Lógica de Nodos (Interactivo) ---
    N = 50
    nodes = [[random.randint(0, screen.get_width()), 
              random.randint(0, screen.get_height()), 
              random.uniform(-0.3, 0.3), 
              random.uniform(-0.3, 0.3)] for _ in range(N)]

    options = ["CREAR RED NUEVA", "CONTINUAR RED GUARDADA", "INSTRUCCIONES", "SALIR"]
    hover_states = [0.0] * len(options)
    
    clock = pygame.time.Clock()

    def draw_ui_element(surface, text, rect, hover_val):
        # Efecto de cristal sutil
        alpha = int(15 + (hover_val * 35)) 
        bg_rect_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        pygame.draw.rect(bg_rect_surf, (*ACCENT_COLOR, alpha), (0, 0, rect.width, rect.height), border_radius=4)
        surface.blit(bg_rect_surf, rect.topleft)

        # Indicador lateral cinético
        if hover_val > 0.1:
            h = int(rect.height * hover_val * 0.6)
            pygame.draw.line(surface, ACCENT_COLOR, 
                             (rect.left - 15, rect.centery - h//2),
                             (rect.left - 15, rect.centery + h//2), 2)

        # Texto
        text_color = ACCENT_COLOR if hover_val > 0.5 else TEXT_COLOR
        txt_surf = option_font.render(text, True, text_color)
        surface.blit(txt_surf, (rect.left + 20 + (hover_val * 5), rect.centery - txt_surf.get_height() // 2))

    while True:
        mouse_pos = pygame.mouse.get_pos()
        screen.fill(BG_COLOR)
        
        # --- 1. FONDO DE RED INTERACTIVA ---
        temp_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        for i, node in enumerate(nodes):
            # Movimiento base
            node[0] += node[2]
            node[1] += node[3]
            
            # Reacción al mouse (los nodos se alejan sutilmente)
            d_mouse = math.hypot(node[0] - mouse_pos[0], node[1] - mouse_pos[1])
            if d_mouse < 150:
                angle = math.atan2(node[1] - mouse_pos[1], node[0] - mouse_pos[0])
                node[0] += math.cos(angle) * 0.8
                node[1] += math.sin(angle) * 0.8

            # Rebote
            if node[0] < 0 or node[0] > screen.get_width(): node[2] *= -1
            if node[1] < 0 or node[1] > screen.get_height(): node[3] *= -1
            
            pygame.draw.circle(temp_surface, (*ACCENT_COLOR, 60), (int(node[0]), int(node[1])), 2)

        # Conexiones entre nodos
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                dist = math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1])
                if dist < 110:
                    alpha = int((1 - dist/110) * 80)
                    pygame.draw.line(temp_surface, (*ACCENT_COLOR, alpha), 
                                     (nodes[i][0], nodes[i][1]), (nodes[j][0], nodes[j][1]), 1)
        screen.blit(temp_surface, (0,0))

        # --- 2. METADATOS (Toque Profesional) ---
        # Esquina Inferior Izquierda: Autoría y Departamento
        author_txt = info_font.render("by Eduardo Guerra", True, METADATA_COLOR)
        screen.blit(author_txt, (20, screen.get_height() - 30))
        
        # Esquina Inferior Derecha: Versión y Fecha
        #ver_txt = info_font.render(f"BUILD: v1.0.4-ALPHA", True, METADATA_COLOR)
        #screen.blit(ver_txt, (screen.get_width() - ver_txt.get_width() - 20, screen.get_height() - 30))

        # --- 3. BOTONES (Centrados Verticalmente) ---
        total_menu_h = len(options) * 70
        start_y = (screen.get_height() // 2) - (total_menu_h // 2)
        
        for i, opt in enumerate(options):
            rect = pygame.Rect(screen.get_width()//2 - 150, start_y + (i * 70), 300, 45)
            
            if rect.collidepoint(mouse_pos):
                hover_states[i] = min(1.0, hover_states[i] + 0.1)
            else:
                hover_states[i] = max(0.0, hover_states[i] - 0.1)
            
            draw_ui_element(screen, opt, rect, hover_states[i])

        # Eventos
        for event in pygame.event.get():
            if event.type == pygame.QUIT: return "SALIR"
            if event.type == pygame.MOUSEBUTTONDOWN:
                for i, rect in enumerate([pygame.Rect(screen.get_width()//2 - 150, start_y + (j * 70), 300, 45) for j in range(len(options))]):
                    if rect.collidepoint(mouse_pos):
                        return options[i]

        pygame.display.flip()
        clock.tick(60)

import pygame

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