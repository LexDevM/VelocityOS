# Guía Técnica para Contribuidores de VelocityOS

¡Gracias por tu interés en contribuir a VelocityOS! Esta guía contiene toda la información necesaria para entender la arquitectura del proyecto, configurar el entorno de desarrollo y realizar contribuciones de manera efectiva.

##  Filosofía del Proyecto

VelocityOS se basa en tres pilares fundamentales:

1.  **Eficacia:** Cada optimización debe tener un impacto real y medible.
2.  **Seguridad y Reversibilidad:** El programa nunca debe dejar el sistema en un estado inestable. Toda optimización principal debe ser reversible.
3.  **Transparencia:** El usuario debe tener control y conocimiento de los cambios que se realizan en su sistema.

Cualquier nueva contribución debe respetar estos principios.

## 🏗️ Arquitectura del Proyecto

El proyecto sigue una arquitectura modular para separar responsabilidades y facilitar el mantenimiento.

```
/VelocityOS/
├── assets/             # Recursos estáticos: iconos, hojas de estilo.
├── bin/                # Binarios externos, como el CLI de Ookla Speedtest.
├── config/             # Archivos JSON que definen los perfiles de optimización.
├── core/               # El "cerebro" de la aplicación. Contiene toda la lógica de backend.
│   ├── gpu_optimizer.py
│   ├── monitor.py
│   ├── network_optimizer.py
│   ├── registry_manager.py
│   ├── speed_test_worker.py
│   ├── state_manager.py
│   └── system_optimizer.py
├── gui/                # Módulos de la Interfaz Gráfica (Vistas, a reformar).
│   └── main_window.py
├── utils/              # Funciones de ayuda y utilidades agnósticas a la lógica principal.
│   ├── admin_checker.py
│   ├── resource_path.py
│   └── startup_manager.py
├── main.py             # Punto de entrada de la aplicación.
├── requirements.txt    # Lista de dependencias de Python.
├── VelocityOS.spec     # Archivo de configuración para PyInstaller.
└── installer_script.iss # Script de Inno Setup para crear el instalador.
```

### Flujo de Datos y Componentes Clave

-   **`main.py`**: Inicia la aplicación, solicita privilegios de administrador, carga la hoja de estilos y crea la `MainWindow`.
-   **`gui/main_window.py`**: Es el controlador principal de la UI. Orquesta las llamadas a los módulos del `core` basándose en las interacciones del usuario. Contiene los "slots" que responden a las señales (clics de botón, etc.).
-   **`core/`**:
    -   **`SystemOptimizer`, `NetworkOptimizer`, `GpuOptimizer`**: Cada uno encapsula un área específica de optimización. No guardan estado por sí mismos.
    -   **`StateManager`**: El componente más crítico. Es el único responsable de leer y escribir el `backup_state.json`. Los optimizadores le piden que guarde el estado *antes* de realizar un cambio.
    -   **`RegistryManager`**: Una clase de utilidad para abstraer y asegurar las interacciones con el Registro de Windows.
    -   **`SystemMonitor` y `SpeedTestWorker`**: Son `QThread` que se ejecutan en segundo plano para no congelar la GUI. Comunican sus resultados a `MainWindow` a través de señales de Qt (`pyqtSignal`).
-   **`utils/`**: Contiene helpers reutilizables, como la función `resource_path` para encontrar archivos de assets de forma fiable.

## ⚙️ Configuración del Entorno de Desarrollo

1.  **Clona el Repositorio:**
    ```bash
    git clone https://github.com/LexDevM/VelocityOS.git
    cd VelocityOS
    ```

2.  **Instala Python:** Asegúrate de tener **Python 3.11+** instalado. **Es crucial usar la versión descargada desde [python.org](https://www.python.org/downloads/windows/), NO la de la Microsoft Store**, y marcar la casilla "Add python.exe to PATH" durante la instalación.

3.  **Crea y Activa un Entorno Virtual:**
    ```bash
    # Crear el entorno
    python -m venv .venv

    # Activar en Windows (PowerShell)
    .\.venv\Scripts\Activate.ps1
    
    # Activar en Windows (CMD)
    .\.venv\Scripts\activate
    ```

4.  **Instala las Dependencias:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Descarga los Binarios Externos:**
    - Ve a la [página de Speedtest CLI](https://www.speedtest.net/es/apps/cli).
    - Descarga el ZIP para Windows.
    - Extrae `speedtest.exe` y `speedtest.md` dentro de la carpeta `bin/` del proyecto.

6.  **Ejecuta la Aplicación en Modo Desarrollo:**
    ```bash
    python main.py
    ```

## 📝 Cómo Añadir una Nueva Optimización

Para mantener la coherencia y la seguridad del proyecto, sigue estos pasos para añadir una nueva funcionalidad:

1.  **Identifica el Módulo Adecuado:** Decide si la nueva optimización pertenece a `SystemOptimizer`, `NetworkOptimizer` o si requiere un nuevo módulo en `core/`.
2.  **Crea la Función de Optimización:**
    - La función debe ser **idempotente** (comprobar si el ajuste ya está aplicado antes de hacer nada).
    - **Antes** de realizar cualquier cambio, llama al `StateManager` para guardar el estado original. Por ejemplo: `self.state_manager.save_state('mi_nuevo_ajuste', valor_original)`.
3.  **Crea la Función de Restauración:**
    - Crea un método correspondiente para revertir el cambio.
    - Debe leer el valor guardado del `StateManager` (`self.state_manager.get_state('mi_nuevo_ajuste')`) y restaurarlo.
4.  **Añade la Opción al Perfil:**
    - Abre los archivos `.json` en `config/`.
    - Añade una nueva clave para tu optimización, por ejemplo: `"mi_nueva_opt": {"enabled": true}`.
5.  **Integra en la GUI:**
    - En `gui/main_window.py`, en el método `run_optimization`, añade una llamada a tu nueva función, protegida por la configuración del perfil: `if opts.get('mi_nueva_opt', {}).get('enabled', False): self.system_optimizer.mi_funcion_de_opt()`.
    - Haz lo mismo en `run_restore` para la función de restauración.
6.  **Actualiza la Pestaña de Ajustes:**
    - En `gui/main_window.py`, añade tu nueva optimización al diccionario `option_map` en el método `populate_profile_settings` para que aparezca como un checkbox personalizable.

## 🎨 Guía de Estilo

- **Código:** Sigue el estándar **PEP 8**. Usa un formateador como `black` o `autopep8` si es posible.
- **Comentarios:** Documenta funciones complejas, especialmente aquellas que interactúan con APIs de bajo nivel de Windows. Explica el "porqué" del código, no solo el "qué".
- **Mensajes de Commit:** Usa mensajes de commit claros y descriptivos (ej. `feat: Añade optimización de caché de DNS`, `fix: Corrige deadlock en SpeedTestWorker`).

## 📦 Empaquetado y Creación del Instalador

El proyecto utiliza **PyInstaller** y **Inno Setup**.

1.  **Para crear el ejecutable:**
    ```bash
    # Asegúrate de tener un icono multi-resolución en assets/icons/velocityos.ico
    # y un archivo version.txt en la raíz.
    pyinstaller VelocityOS.spec
    ```
    El resultado estará en la carpeta `dist/VelocityOS/`.

2.  **Para crear el instalador:**
    - Abre el archivo `installer_script.iss` con **Inno Setup Compiler**.
    - Haz clic en "Build" -> "Compile".
    - El instalador final (`VelocityOS_vX.X.X_Setup.exe`) se generará en la carpeta `Output/`.
