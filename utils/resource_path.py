# utils/resource_path.py
import sys
import os

def resource_path(relative_path):
    """
    Obtiene la ruta absoluta a un recurso, funciona tanto para desarrollo
    como para el ejecutable de PyInstaller.
    """
    if hasattr(sys, '_MEIPASS'):
        # Estamos en un bundle de PyInstaller
        base_path = sys._MEIPASS
    else:
        # Estamos en modo de desarrollo, la base es el directorio del script principal
        # os.path.dirname(__file__) nos da la ruta del archivo actual (resource_path.py)
        # os.path.abspath(os.path.join(..., "..")) sube un nivel para llegar a la raíz del proyecto
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

    return os.path.join(base_path, relative_path)