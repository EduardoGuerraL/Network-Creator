import pygame, random, math
from pygame.locals import *

#Mejorando lo bonito del programa con una pantalla de bienvenida
def show_initial_splash(screen):
    # --- Función interna para dibujar la red animada ---
    def draw_network(surface, alpha_fade):
        surface.fill(BG_COLOR)
        # Mover y dibujar nodos
        for node in nodes:
            node[0] += node[2] # Movimiento en X
            node[1] += node[3] # Movimiento en Y
            # Rebote en los bordes
            if node[0] < 0 or node[0] > surface.get_width(): node[2] *= -1
            if node[1] < 0 or node[1] > surface.get_height(): node[3] *= -1
            
            # Dibujar el nodo (brillo sutil)
            pygame.draw.circle(surface, (*ACCENT_COLOR, int(alpha_fade * 0.5)), (int(node[0]), int(node[1])), 2)

        # Conectar nodos cercanos
        for i in range(len(nodes)):
            for j in range(i + 1, len(nodes)):
                dist = math.hypot(nodes[i][0] - nodes[j][0], nodes[i][1] - nodes[j][1])
                if dist < 100: # Si están cerca, se conectan
                    # El grosor y la opacidad dependen de la distancia
                    line_alpha = int(max(0, (1 - dist/100) * alpha_fade * 0.3))
                    if line_alpha > 0:
                        pygame.draw.line(surface, (*ACCENT_COLOR, line_alpha), 
                                         (int(nodes[i][0]), int(nodes[i][1])), 
                                         (int(nodes[j][0]), int(nodes[j][1])), 1)
    
    pygame.init()

  # --- Paleta de colores Deep Tech ---
    BG_COLOR = (12, 14, 18)        # Azul grafito muy oscuro, casi abismo
    ACCENT_COLOR = (0, 255, 200)   # Cyan tecnológico para los nodos
    TEXT_COLOR = (240, 245, 255)   # Blanco perla
    #Titulo grande y bonito
    title_font = pygame.font.SysFont("Arial", 65, bold=True)
    text_surf = title_font.render("NETWORK CREATOR", True, TEXT_COLOR)
    text_rect = text_surf.get_rect(center=(screen.get_width()//2, screen.get_height()//2 - 10))
    
    #subtitulo
    subtitle_font = pygame.font.SysFont("Arial", 20)
    subtitle_surf = subtitle_font.render("Complex Systems & Graph Architecture", True, (120, 130, 140))
    subtitle_rect = subtitle_surf.get_rect(center=(screen.get_width()//2, screen.get_height()//2 + 45))
    
    # Creamos nodos flotantes en posiciones aleatorias
    N = 50
    nodes = [[random.randint(0, screen.get_width()), random.randint(0, screen.get_height()), 
              random.choice([-1, 1])*random.uniform(0.2, 0.5), 
              random.choice([-1, 1])*random.uniform(0.2, 0.5)] for _ in range(N)]
    
    clock = pygame.time.Clock()
    
    # Animación de Fade In y Fade Out
    for alpha in range(0, 255, 2): # Aparece
        for event in pygame.event.get(): pass # Evita que la ventana se congele
        
        # Usamos una superficie temporal para manejar la transparencia global
        temp_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        draw_network(temp_surface, alpha)
        
        text_surf.set_alpha(alpha)
        subtitle_surf.set_alpha(alpha)
        temp_surface.blit(text_surf, text_rect)
        temp_surface.blit(subtitle_surf, subtitle_rect)
        
        screen.fill(BG_COLOR)
        screen.blit(temp_surface, (0,0))
        pygame.display.flip()
        clock.tick(60)

    # --- Pausa Dramática de Lectura ---
    for _ in range(100): # 1.5 segundos de animación a 60fps
        for event in pygame.event.get(): pass
        temp_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        draw_network(temp_surface, 255)
        temp_surface.blit(text_surf, text_rect)
        temp_surface.blit(subtitle_surf, subtitle_rect)
        screen.fill(BG_COLOR)
        screen.blit(temp_surface, (0,0))
        pygame.display.flip()
        clock.tick(60)

    # --- Secuencia de Salida (Fade Out) ---
    for alpha in range(255, 0, -5):
        for event in pygame.event.get(): pass
        temp_surface = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        draw_network(temp_surface, alpha)
        text_surf.set_alpha(alpha)
        subtitle_surf.set_alpha(alpha)
        temp_surface.blit(text_surf, text_rect)
        temp_surface.blit(subtitle_surf, subtitle_rect)
        screen.fill(BG_COLOR)
        screen.blit(temp_surface, (0,0))
        pygame.display.flip()
        clock.tick(60)