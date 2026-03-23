import pygame
import random
import math
import datetime

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
        author_txt = info_font.render("DEV: Eduardo Guerra", True, METADATA_COLOR)
        screen.blit(author_txt, (20, screen.get_height() - 30))
        
        # Esquina Inferior Derecha: Versión y Fecha
        ver_txt = info_font.render(f"BUILD: v1.0.4-ALPHA", True, METADATA_COLOR)
        screen.blit(ver_txt, (screen.get_width() - ver_txt.get_width() - 20, screen.get_height() - 30))

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