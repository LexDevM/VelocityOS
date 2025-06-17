# utils/os_detector.py
import platform

def get_windows_version():
    """
    Devuelve un string simple identificando la versión de Windows.
    Retorna 'Windows 10', 'Windows 11', o 'Unknown'.
    """
    version = platform.version()
    # La build 22000 es la primera versión pública de Windows 11
    if '10.0.22000' in version or '10.0.22621' in version: # 22H2
        return "Windows 11"
    elif '10.0.1904' in version: # 2004, 20H2, 21H1, 21H2, 22H2
        return "Windows 10"
    elif '10.0' in version: # Otras versiones de Win10
        return "Windows 10"
    else:
        return "Unknown"