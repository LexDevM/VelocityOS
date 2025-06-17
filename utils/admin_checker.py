# utils/admin_checker.py
import ctypes
import sys
import os

def is_admin():
    """Verifica si el script se está ejecutando con privilegios de administrador."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Vuelve a ejecutar el script actual con privilegios de administrador."""
    if is_admin():
        return True
    
    # Re-lanza el script con el verbo 'runas' para solicitar elevación UAC
    ctypes.windll.shell32.ShellExecuteW(
        None,           # Hwnd
        "runas",        # lpOperation
        sys.executable, # lpFile
        " ".join(sys.argv), # lpParameters
        None,           # lpDirectory
        1               # nShowCmd
    )
    return False