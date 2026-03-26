import pygame
from pygame.locals import QUIT, MOUSEBUTTONDOWN, MOUSEMOTION, MOUSEBUTTONUP, KEYDOWN, K_n, K_l, K_z, K_s, K_1, K_2, K_3, KMOD_CTRL
from src.core.graph import NetworkManager
from src.utils.geometry import draw_arrow
from src.core.export import save_as_pickle, export_to_json
from src.gui.widgets import get_save_name

class NetworkApp:
    def __init__(self, img_path = None):
        pygame.init()

        if img_path:
            # Opción 1: Imagen
            self.bg_image = pygame.image.load(img_path).convert()
            self.width, self.height = self.bg_image.get_size()
        else:
            # Opción 2: Lienzo Blanco (Resolución de trabajo ajustable)
            self.width, self.height = 2000, 1500 # Un lienzo grande para trabajar
            self.bg_image = pygame.Surface((self.width, self.height))
            self.bg_image.fill((35, 38, 43)) 
            # Dibujamos una rejilla tenue para que el usuario no se sienta "perdido" en el blanco
            for x in range(0, self.width, 100):
                pygame.draw.line(self.bg_image, (50, 53, 58), (x, 0), (x, self.height))
            for y in range(0, self.height, 100):
                pygame.draw.line(self.bg_image, (50, 53, 58), (0, y), (self.width, y))

        # --- FIX: Definir screen_size correctamente ---
        # La ventana física puede ser de un tamaño fijo (ej: 1200x800) 
        # mientras que el lienzo/imagen interno es el que tiene zoom.
        self.screen_size = (1200, 800) 
        self.screen = pygame.display.set_mode(self.screen_size)
        pygame.display.set_caption("Network Creator")
        
        # El rect debe representar el espacio de la imagen/lienzo
        self.image_rect = self.bg_image.get_rect()
        
        # Estado de la Red (Lógica separada)
        self.network = NetworkManager()
        
        # Estado de la Interfaz
        self.zoom = 1.0
        self.offset = [0, 0]
        self.dragging = False
        self.mode = "MOVE" # MOVE, NODE, LINK
        self.selected_node = None
        self.current_weight = 1
        
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 18)

    def run(self):
        running = True
        while running:
            self.clock.tick(60)
            running = self.handle_events()
            self.draw()
        pygame.quit()

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == QUIT:
                return False
            
            elif event.type == KEYDOWN:
                self._handle_keydown(event)
                
            elif event.type == MOUSEBUTTONDOWN:
                self._handle_mousedown(event)
                
            elif event.type == MOUSEBUTTONUP:
                if event.button == 1: self.dragging = False
                
            elif event.type == MOUSEMOTION:
                self._handle_mousemotion(event)
        return True

    def _handle_keydown(self, event):
        # Cambio de modos (Usando tu lógica original de 'n' y 'l')
        if event.key == K_n:
            self.mode = "NODE" if self.mode != "NODE" else "MOVE"
        elif event.key == K_l:
            self.mode = "LINK" if self.mode != "LINK" else "MOVE"
        
        # Atajos de teclado (Ctrl+Z, Ctrl+S)
        if event.mod & KMOD_CTRL:
            if event.key == K_z:
                self.network.undo()
            elif event.key == K_s:
                name = get_save_name()
                if name:
                    save_as_pickle(f"{name}.pickle", self.network)
                    export_to_json(f"{name}.json", self.network)
        
        # Pesos/Pistas (1, 2, 3)
        if event.key in [K_1, K_2, K_3]:
            self.current_weight = int(event.unicode)

    def _handle_mousedown(self, event):
        mouse_pos = event.pos
        
        # Zoom con Scroll
        if event.button in [4, 5]:
            self._handle_zoom(event.button, mouse_pos)
            
        elif event.button == 1: # Click izquierdo
            rel_pos = self._screen_to_rel(mouse_pos)
            
            if self.mode == "NODE":
                self.network.add_node(rel_pos)
            elif self.mode == "LINK":
                node_idx = self._get_node_at(mouse_pos)
                if node_idx is not None:
                    if self.selected_node is None:
                        self.selected_node = node_idx
                    else:
                        self.network.add_link(self.selected_node, node_idx, self.current_weight)
                        self.selected_node = None
            else:
                self.dragging = True
                self.mouse_start_x, self.mouse_start_y = mouse_pos
                self.offset_start_x, self.offset_start_y = self.image_rect.topleft

    def _screen_to_rel(self, pos):
        """Convierte coordenadas de pantalla a relativas (0.0 a 1.0)"""
        rel_x = (pos[0] - self.image_rect.x) / (self.zoom * self.image_rect.width)
        rel_y = (pos[1] - self.image_rect.y) / (self.zoom * self.image_rect.height)
        return (rel_x, rel_y)

    def _rel_to_screen(self, rel_pos):
        """Convierte coordenadas relativas a posición en pantalla"""
        screen_x = int(self.image_rect.x + rel_pos[0] * self.zoom * self.image_rect.width)
        screen_y = int(self.image_rect.y + rel_pos[1] * self.zoom * self.image_rect.height)
        return (screen_x, screen_y)

    def _get_node_at(self, mouse_pos):
        for i, node_rel in enumerate(self.network.nodes):
            node_screen = self._rel_to_screen(node_rel)
            dist = ((mouse_pos[0] - node_screen[0])**2 + (mouse_pos[1] - node_screen[1])**2)**0.5
            if dist <= 10: return i
        return None

    def draw(self):
        self.screen.fill((30, 30, 30)) # Fondo gris oscuro profesional
        
        # Dibujar Imagen con Zoom
        scaled_w = int(self.image_rect.width * self.zoom)
        scaled_h = int(self.image_rect.height * self.zoom)
        scaled_img = pygame.transform.smoothscale(self.bg_image, (scaled_w, scaled_h))
        self.screen.blit(scaled_img, self.image_rect.topleft)
        
        # Dibujar Enlaces
        for i, (start_idx, end_idx) in enumerate(self.network.links):
            p1 = self._rel_to_screen(self.network.nodes[start_idx])
            p2 = self._rel_to_screen(self.network.nodes[end_idx])
            draw_arrow(self.screen, (200, 0, 0), p1, p2, 7, 5)
            
        # Dibujar Nodos
        for i, node_rel in enumerate(self.network.nodes):
            color = (0, 255, 0) if i == self.selected_node else (0, 0, 255)
            pygame.draw.circle(self.screen, color, self._rel_to_screen(node_rel), 5)
            
        # UI Overlay
        info = f"MODO: {self.mode} | PESO: {self.current_weight} | NODOS: {len(self.network.nodes)}"
        text = self.font.render(info, True, (255, 255, 255))
        self.screen.blit(text, (10, self.screen_size[1] - 30))
        
        pygame.display.flip()


    def _handle_zoom(self, button, mouse_pos):
        # Guardamos la posición relativa del mouse antes del zoom para mantener el foco
        rel_x = (mouse_pos[0] - self.image_rect.x) / (self.zoom * self.image_rect.width)
        rel_y = (mouse_pos[1] - self.image_rect.y) / (self.zoom * self.image_rect.height)

        # Factor de escala
        if button == 4: # Scroll Up (Zoom In)
            new_zoom = self.zoom * 1.1
            if new_zoom <= 10.0: # Límite máximo de zoom
                self.zoom = new_zoom
        elif button == 5: # Scroll Down (Zoom Out)
            new_zoom = self.zoom / 1.1
            if new_zoom >= 1.0: # No alejarse más del tamaño original
                self.zoom = new_zoom
            else:
                self.zoom = 1.0

        # Ajustamos el rect de la imagen para que el punto bajo el mouse no se mueva
        self.image_rect.x = mouse_pos[0] - rel_x * self.zoom * self.image_rect.width
        self.image_rect.y = mouse_pos[1] - rel_y * self.zoom * self.image_rect.height
        
        self._constrain_boundaries()

    def _handle_mousemotion(self, event):
        # Solo movemos la cámara si estamos en modo MOVE y arrastrando
        if self.dragging and self.mode == "MOVE":
            self.image_rect.x = self.offset_start_x + (event.pos[0] - self.mouse_start_x)
            self.image_rect.y = self.offset_start_y + (event.pos[1] - self.mouse_start_y)
            self._constrain_boundaries()

    def _constrain_boundaries(self):
        """Evita que la imagen se salga de la pantalla al arrastrar o alejar el zoom"""
        # Límites derechos e inferiores
        if self.image_rect.x > 0:
            self.image_rect.x = 0
        if self.image_rect.y > 0:
            self.image_rect.y = 0
            
        # Límites izquierdos y superiores basados en el zoom actual
        min_x = self.screen_size[0] - (self.image_rect.width * self.zoom)
        min_y = self.screen_size[1] - (self.image_rect.height * self.zoom)
        
        if self.image_rect.x < min_x:
            self.image_rect.x = int(min_x)
        if self.image_rect.y < min_y:
            self.image_rect.y = int(min_y)
