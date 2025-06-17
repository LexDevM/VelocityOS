; Script para Inno Setup de VelocityOS
; Creado por Álex Macías León

[Setup]
; --- Información Básica y Branding ---
AppName=VelocityOS
AppVersion=1.0.0
AppPublisher=Álex Macías León
AppPublisherURL=https://github.com/LexDevM
AppId={{E6A3B8D9-C5E1-4F2A-9A8B-3F1D7E9A0B1C}}

; --- Directorios y Nombres de Archivo ---
DefaultDirName={autopf}\VelocityOS
DefaultGroupName=VelocityOS
OutputBaseFilename=VelocityOS_v1.0.0_Setup
SetupIconFile=assets\icons\velocityos.ico
UninstallDisplayIcon={app}\VelocityOS.exe

; --- Configuración de la Compresión y Apariencia ---
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; ====================================================================
; --- SECCIÓN DE PRIVILEGIOS ---
;
; PrivilegesRequired=admin asegura que el instalador pida elevación.
PrivilegesRequired=admin
;
; PrivilegesRequiredOverridesAllowed especifica qué opciones tendrá el
; usuario si no es administrador. Al poner solo 'commandline', forzamos
; a que la única forma de no pedir elevación sea mediante un argumento
; de línea de comandos, lo cual en la práctica obliga a que siempre la pida.
PrivilegesRequiredOverridesAllowed=commandline
;
; ====================================================================


[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"


[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}";


[Files]
Source: "dist\VelocityOS\VelocityOS.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\VelocityOS\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "license.txt"; DestDir: "{app}"; Flags: isreadme


[Icons]
Name: "{group}\VelocityOS"; Filename: "{app}\VelocityOS.exe"
Name: "{autodesktop}\VelocityOS"; Filename: "{app}\VelocityOS.exe"; Tasks: desktopicon


[Run]
Filename: "{app}\VelocityOS.exe"; Description: "{cm:LaunchProgram,VelocityOS}"; Flags: nowait postinstall skipifsilent
