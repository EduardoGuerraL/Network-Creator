import pygame
import math

def draw_arrow(screen, color, start, end, trirad, circle_radius):
    rotation = math.degrees(math.atan2(start[1]-end[1], end[0]-start[0]))
    # Ajuste para que la flecha no quede dentro del círculo del nodo
    adj_end = (
        end[0] - 2 * circle_radius * math.cos(math.radians(rotation)), 
        end[1] + 2 * circle_radius * math.sin(math.radians(rotation))
    )
    pygame.draw.line(screen, color, start, adj_end, 2)
    
    rotation_poly = rotation + 90
    points = [
        (adj_end[0] + trirad * math.sin(math.radians(rotation_poly)), 
         adj_end[1] + trirad * math.cos(math.radians(rotation_poly))),
        (adj_end[0] + trirad * math.sin(math.radians(rotation_poly - 120)), 
         adj_end[1] + trirad * math.cos(math.radians(rotation_poly - 120))),
        (adj_end[0] + trirad * math.sin(math.radians(rotation_poly + 120)), 
         adj_end[1] + trirad * math.cos(math.radians(rotation_poly + 120)))
    ]
    pygame.draw.polygon(screen, color, points)