# main.py

import sys
import os
import logging
from PyQt6.QtWidgets import QApplication

# --- CONFIGURACIÓN DE LOGGING ---
try:
    log_dir = os.path.join(os.getenv('LOCALAPPDATA'), 'VelocityOS')
    os.makedirs(log_dir, exist_ok=True) # Crear la carpeta si no existe
    log_file = os.path.join(log_dir, 'debug.log')

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, mode='w', encoding='utf-8'), # Especificar UTF-8
            logging.StreamHandler()
        ]
    )
except Exception as e:
    # Fallback muy básico si el logging falla
    print(f"FATAL: No se pudo configurar el logging: {e}")
# ---------------------------------------------

logging.info("Inicio del programa.")

try:
    logging.info("Importando módulos...")
    from utils import admin_checker
    from gui.main_window import MainWindow
    from utils.resource_path import resource_path
    logging.info("Módulos importados correctamente.")

    def main():
        """
        Punto de entrada principal de la aplicación.
        """
        logging.info("Entrando en la función main().")
        
        # Esta comprobación es una salvaguarda, especialmente para el modo de desarrollo.
        if not admin_checker.is_admin():
            logging.critical("Error: La aplicación debe ejecutarse con privilegios de administrador.")
            # En un futuro, podríamos mostrar un QMessageBox aquí antes de salir.
            sys.exit(1) # Salir con un código de error.
        
        logging.info("Privilegios de administrador confirmados.")

        logging.info("Creando instancia de QApplication.")
        app = QApplication(sys.argv)
        
        logging.info("Cargando hoja de estilos...")
        try:
            style_path = resource_path(os.path.join('assets', 'styles', 'main.qss'))
            with open(style_path, "r", encoding='utf-8') as f:
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
    # Este bloque atrapará cualquier error catastrófico que ocurra durante la inicialización.
    logging.critical(f"ERROR FATAL INESPERADO: {e}", exc_info=True)
    # exc_info=True añade el 'traceback' completo al log para ver exactamente dónde ocurrió el error.