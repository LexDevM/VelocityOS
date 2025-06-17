# main.py
import sys
import os
import logging
from PyQt6.QtWidgets import QApplication

# --- CONFIGURACIÓN DE LOGGING PROFESIONAL ---
# El lugar correcto para guardar logs es AppData\Local
log_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'VelocityOS')
os.makedirs(log_dir, exist_ok=True) # Crear la carpeta si no existe
log_file = os.path.join(log_dir, 'debug.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, mode='w'),
        logging.StreamHandler()
    ]
)
# ---------------------------------------------

logging.info("Inicio del programa.")

try:
    logging.info("Importando módulos...")
    from utils import admin_checker
    from gui.main_window import MainWindow
    from utils.resource_path import resource_path # Importar para el estilo
    logging.info("Módulos importados correctamente.")

    def main():
        logging.info("Entrando en la función main().")
        
        logging.info("Verificando privilegios de administrador...")
        if not admin_checker.run_as_admin():
            logging.warning("No es admin. Solicitando elevación y saliendo.")
            sys.exit()
        logging.info("Privilegios de administrador confirmados.")

        logging.info("Creando instancia de QApplication.")
        app = QApplication(sys.argv)
        
        logging.info("Cargando hoja de estilos...")
        try:
            style_path = resource_path(os.path.join('assets', 'styles', 'main.qss'))
            with open(style_path, "r") as f:
                app.setStyleSheet(f.read())
            logging.info("Hoja de estilos cargada con éxito.")
        except FileNotFoundError:
            logging.warning(f"No se encontró el archivo de estilos en {style_path}")
        except Exception as e:
            logging.error(f"Error cargando la hoja de estilos: {e}")

        logging.info("Creando instancia de MainWindow.")
        window = MainWindow()
        logging.info("Mostrando la ventana principal.")
        window.show()
        
        logging.info("Iniciando el bucle de eventos de la aplicación.")
        sys.exit(app.exec())

    if __name__ == "__main__":
        logging.info("Bloque __main__ alcanzado. Llamando a main().")
        main()

except Exception as e:
    logging.critical(f"ERROR FATAL INESPERADO: {e}", exc_info=True)