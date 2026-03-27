from src.core.export import save_project, load_project, migrate_pickle
from src.gui.widgets import get_save_path, get_open_path, ask_node_label
from pygame.locals import (QUIT, MOUSEBUTTONDOWN, MOUSEMOTION, MOUSEBUTTONUP,
                            KEYDOWN, K_n, K_l, K_z, K_s, K_o, K_d, K_e,
                            K_1, K_2, K_3, KMOD_CTRL)
import pygame
from src.core.graph import NetworkManager
from src.utils.geometry import draw_arrow

class NetworkApp:
    def __init__(self, img_path = None):
        self.mode = "MOVE"  # MOVE, NODE, LINK, DELETE
        self.hovered_node = None  # para resaltar en modo DELETE
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
        if event.key == K_n:
            self.mode = "NODE" if self.mode != "NODE" else "MOVE"
        elif event.key == K_l:
            self.mode = "LINK" if self.mode != "LINK" else "MOVE"
        elif event.key == K_d:          # nuevo: modo borrar
            self.mode = "DELETE" if self.mode != "DELETE" else "MOVE"
        elif event.key == K_e:          # nuevo: editar etiqueta del nodo bajo cursor
            node_idx = self._get_node_at(pygame.mouse.get_pos())
            if node_idx is not None:
                current = self.network.nodes[node_idx]["label"]
                new_label = ask_node_label(current)
                if new_label is not None:
                    self.network.set_label(node_idx, new_label)

        if event.mod & KMOD_CTRL:
            if event.key == K_z:
                self.network.undo()
            elif event.key == K_s:
                path = get_save_path()
                if path:
                    save_project(path, self.network)
            elif event.key == K_o:      # nuevo: abrir
                path = get_open_path()
                if path:
                    if path.endswith(".pickle"):
                        self.network = migrate_pickle(path, path.replace(".pickle", ".json"))
                    else:
                        self.network = load_project(path)

        if event.key in [K_1, K_2, K_3]:
            self.current_weight = int(event.unicode)


    def _handle_mousedown(self, event):
        mouse_pos = event.pos
        if event.button in [4, 5]:
            self._handle_zoom(event.button, mouse_pos)
            return

        if event.button == 1:
            rel_pos = self._screen_to_rel(mouse_pos)
            if self.mode == "NODE":
                # Pedir etiqueta al crear — puede dejarse vacía
                label = ask_node_label("")
                if label is not None:           # None = canceló el diálogo
                    self.network.add_node(rel_pos, label=label)
            elif self.mode == "LINK":
                node_idx = self._get_node_at(mouse_pos)
                if node_idx is not None:
                    if self.selected_node is None:
                        self.selected_node = node_idx
                    else:
                        self.network.add_link(self.selected_node, node_idx, self.current_weight)
                        self.selected_node = None
            elif self.mode == "DELETE":
                node_idx = self._get_node_at(mouse_pos)
                if node_idx is not None:
                    self.network.remove_node(node_idx)
                    self.selected_node = None   # reset por si estaba seleccionado
            else:  # MOVE
                self.dragging = True
                self.mouse_start_x, self.mouse_start_y = mouse_pos
                self.offset_start_x, self.offset_start_y = self.image_rect.topleft

        elif event.button == 3:         # clic derecho = borrar enlace
            node_idx = self._get_node_at(mouse_pos)
            if node_idx is not None and self.selected_node is not None:
                self.network.remove_link(self.selected_node, node_idx)
                self.selected_node = None
    def _screen_to_rel(self, pos):
        rel_x = (pos[0] - self.image_rect.x) / (self.zoom * self.image_rect.width)
        rel_y = (pos[1] - self.image_rect.y) / (self.zoom * self.image_rect.height)
        return (rel_x, rel_y)

    def _rel_to_screen(self, rel_pos):
        # Ahora rel_pos puede ser una tupla directa O el dict de nodo
        if isinstance(rel_pos, dict):
            rel_pos = rel_pos["pos"]
        screen_x = int(self.image_rect.x + rel_pos[0] * self.zoom * self.image_rect.width)
        screen_y = int(self.image_rect.y + rel_pos[1] * self.zoom * self.image_rect.height)
        return (screen_x, screen_y)

    def _get_node_at(self, mouse_pos):
        for i, node in enumerate(self.network.nodes):
            node_screen = self._rel_to_screen(node["pos"])
            dist = ((mouse_pos[0] - node_screen[0])**2 +
                    (mouse_pos[1] - node_screen[1])**2) ** 0.5
            if dist <= 10:
                return i
        return None

    def draw(self):
        self.screen.fill((30, 30, 30))

        scaled_w = int(self.image_rect.width * self.zoom)
        scaled_h = int(self.image_rect.height * self.zoom)
        scaled_img = pygame.transform.smoothscale(self.bg_image, (scaled_w, scaled_h))
        self.screen.blit(scaled_img, self.image_rect.topleft)

        # Enlaces
        for i, (start_idx, end_idx) in enumerate(self.network.links):
            p1 = self._rel_to_screen(self.network.nodes[start_idx]["pos"])
            p2 = self._rel_to_screen(self.network.nodes[end_idx]["pos"])
            draw_arrow(self.screen, (200, 0, 0), p1, p2, 7, 5)

        # Nodos + etiquetas
        for i, node in enumerate(self.network.nodes):
            if i == self.selected_node:
                color = (0, 255, 0)
            elif self.mode == "DELETE" and i == self._get_node_at(pygame.mouse.get_pos()):
                color = (255, 80, 80)   # rojo al hover en modo DELETE
            else:
                color = (0, 120, 255)

            screen_pos = self._rel_to_screen(node["pos"])
            pygame.draw.circle(self.screen, color, screen_pos, 6)

            if node["label"]:
                label_surf = self.font.render(node["label"], True, (255, 255, 255))
                self.screen.blit(label_surf, (screen_pos[0] + 9, screen_pos[1] - 9))

        # HUD
        mode_colors = {"MOVE": (180,180,180), "NODE": (80,220,80),
                    "LINK": (80,160,255), "DELETE": (255,80,80)}
        color = mode_colors.get(self.mode, (255,255,255))
        info = f"MODO: {self.mode}  |  PESO: {self.current_weight}  |  NODOS: {len(self.network.nodes)}  |  [N] nodo  [L] link  [D] borrar  [E] etiquetar  [Ctrl+S] guardar  [Ctrl+O] abrir"
        text = self.font.render(info, True, color)
        self.screen.blit(text, (10, self.screen_size[1] - 28))

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
