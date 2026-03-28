<div align="center">

```
███╗   ██╗███████╗████████╗██╗    ██╗ ██████╗ ██████╗ ██╗  ██╗
████╗  ██║██╔════╝╚══██╔══╝██║    ██║██╔═══██╗██╔══██╗██║ ██╔╝
██╔██╗ ██║█████╗     ██║   ██║ █╗ ██║██║   ██║██████╔╝█████╔╝ 
██║╚██╗██║██╔══╝     ██║   ██║███╗██║██║   ██║██╔══██╗██╔═██╗ 
██║ ╚████║███████╗   ██║   ╚███╔███╔╝╚██████╔╝██║  ██║██║  ██╗
╚═╝  ╚═══╝╚══════╝   ╚═╝    ╚══╝╚══╝  ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝
           C R E A T O R  —  Complex Systems & Graph Architecture
```

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white)
![Pygame](https://img.shields.io/badge/Pygame-2.x-00C8A0?style=flat-square&logo=python&logoColor=white)
![OpenCV](https://img.shields.io/badge/OpenCV-4.x-5C3EE8?style=flat-square&logo=opencv&logoColor=white)
![Status](https://img.shields.io/badge/Status-Alpha-orange?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-brightgreen?style=flat-square)

**Una herramienta interactiva para construir, visualizar y exportar grafos y redes complejas sobre imágenes reales.**

</div>

---

## ¿Qué es Network Creator?

Network Creator es una herramienta para visualizar y construir redes complejas de forma interactiva.

Cuando estudié Física en la Universidad de Chile, me interesé por el mundo de las redes complejas y sentí la necesidad de poder visualizarlas y crear mis propias redes. Por eso creé este programa, que en sus inicios era bastante más rudimentario.

Con el tiempo, esto me permitió desarrollar una aplicación interesante: la creación de redes de calles de ciudades, con la cual, junto a Chilean Complexity Cluster, llevamos adelante una investigación de optimización de tráfico vehicular. Este trabajo me dio la oportunidad de presentar en conferencias de física en dos ocasiones.

El resultado se puede exportar a JSON para integraciones externas o guardar en formato binario para continuar editando después.

El repositorio aún se encuentra en fase de mejora, por lo que puedes encontrar partes que no funcionan completamente. No soy programador de profesión, así que es posible que haya errores. Recibo con mucho gusto cualquier aporte u opinión.


---

## Algunas Características

- **Doble modo de lienzo** — carga una imagen propia como fondo o trabaja sobre un canvas infinito con cuadrícula.
- **Nodos y enlaces dirigidos** — con soporte para pesos/carriles múltiples (1, 2 o 3).
- **Zoom y paneo fluidos** — navega el mapa con scroll y arrastre; la cámara se ajusta al punto de enfoque.
- **Historial de acciones** — deshaz el último paso con `Ctrl+Z`.
- **Exportación dual** — guarda en `.pickle` para continuar editando o en `.json` para análisis externos.
- **Interfaz animada** — menú principal con red de nodos interactiva reactiva al mouse.
- **Drag & Drop** — arrastra una imagen directamente a la ventana para abrirla. (Aun no funciona)

---

## Instalación

**Requisitos:** Python 3.10 o superior.

```bash
# 1. Clona el repositorio
git clone https://github.com/tu-usuario/network-creator.git
cd network-creator

# 2. Crea un entorno virtual (recomendado)
python -m venv venv
source venv/bin/activate      # Linux / macOS
venv\Scripts\activate         # Windows

# 3. Instala las dependencias
pip install -r requirements.txt
```

---

## Uso

```bash
python3 main.py
```

Al iniciar, verás una pantalla de bienvenida animada seguida del **menú principal**. Desde allí puedes:

| Opción | Descripción |
|---|---|
| **Crear Red Nueva** | Elige una imagen de fondo o trabaja en lienzo en blanco |
| **Continuar Red Guardada** | _(Próximamente)_ Carga un proyecto `.pickle` existente _(funciona dentro de red infinita con ctrl\_o )_ |
| **Instrucciones** | _(Próximamente)_ Guía de uso integrada |

### Controles dentro del editor

| Acción | Control |
|---|---|
| Modo CREATE | `M` |
| Modo DELETE | `R` |
| Añadir nodo | Clic izquierdo (en modo CREATE) |
| Conectar nodos | Clic derecho en nodo origen → clic derecho en nodo destino|
| Cambiar peso del enlace | `1`, `2` o `3` (en busca de mejora)|
| Zoom | Scroll del ratón |
| Paneo | Arrastrar con boton central|
| Deshacer | `Ctrl + Z` |
| Guardar | `Ctrl + S` |
| Abrir | `Ctrl + O` |

<!--
---

## Estructura del Proyecto

```
network-creator/
├── main.py                  # Punto de entrada
├── requirements.txt
├── src/
│   ├── core/
│   │   ├── graph.py         # Lógica del grafo (NetworkManager)
│   │   └── export.py        # Exportación a .pickle y .json
│   ├── gui/
│   │   ├── app.py           # Editor principal (NetworkApp) + splash screen
│   │   ├── menu.py          # Menú principal y menú de creación
│   │   └── widgets.py       # Diálogos Tkinter (abrir archivo, guardar)
│   └── utils/
│       └── geometry.py      # Dibujado de flechas dirigidas
```

---
-->

## Formato de Exportación JSON

```json
{
    "nodes": [
        { "id": 0, "x": 0.312, "y": 0.458 },
        { "id": 1, "x": 0.671, "y": 0.203 }
    ],
    "edges": [
        { "from": 0, "to": 1, "w": 2 }
    ]
}
```

Las coordenadas `x` e `y` son **relativas** (entre `0.0` y `1.0`) respecto al tamaño del lienzo, lo que hace el formato independiente de la resolución.

---

## Roadmap

- [ ] Cargar imagen de fondo
- [ ] Soporte para grafos no dirigidos
- [ ] Cargar proyectos guardados desde el menú
- [ ] Algoritmos de análisis (camino mínimo, centralidad)
- [ ] Etiquetas editables en nodos y enlaces
- [ ] Pantalla de instrucciones integrada
- [ ] Exportación a SVG / PNG

---

## Dependencias

| Librería | Uso |
|---|---|
| `pygame` | Motor gráfico y gestión de eventos |
| `opencv-python` | Procesamiento de imágenes |
| `numpy >= 1.26` | Operaciones numéricas |
| `tkinter` | Diálogos de sistema (incluido en Python stdlib) |

---

## Contribuir

Las contribuciones son bienvenidas. Si encuentras un bug o tienes una idea, abre un _issue_ o un _pull request_.

1. Haz fork del repositorio
2. Crea una rama: `git checkout -b feature/mi-mejora`
3. Haz commit de tus cambios: `git commit -m 'feat: descripción'`
4. Push a la rama: `git push origin feature/mi-mejora`
5. Abre un Pull Request

---

<div align="center">

by **Eduardo Guerra**

_"Medite cada paso antemano, pero cuando crea poder justificarlo, no se detenga ante nada." - Max Plank_

</div>
