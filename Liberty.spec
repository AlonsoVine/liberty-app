# -*- mode: python ; coding: utf-8 -*-
# PyInstaller: empaqueta la app en un único ejecutable (Liberty.exe).
# Construir:  pyinstaller Liberty.spec

a = Analysis(
    ["lanzar.py"],
    pathex=[],
    binaries=[],
    # Recursos de solo lectura que la app necesita en tiempo de ejecución.
    datas=[
        ("app/web", "app/web"),
        ("demo/cartera.json", "demo"),
        ("app/VERSION", "app"),
        ("app/prompt_ia.txt", "app"),
        ("app/prompt_ia_banco.txt", "app"),
    ],
    hiddenimports=["openpyxl"],
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "ruff", "PIL", "numpy"],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data)

# Metadatos de versión de Windows (nombre de producto, versión, autor…). Se generan a
# partir de app/VERSION. Un .exe con ficha de "producto" dispara bastantes menos falsos
# positivos en los antivirus que uno de PyInstaller sin metadatos ni firma.
import os as _os
_ver = open(_os.path.join("app", "VERSION"), encoding="utf-8").read().strip()
_vt = tuple((list(map(int, _ver.split("."))) + [0, 0, 0, 0])[:4])
_vinfo = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={_vt}, prodvers={_vt}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040a04b0', [
      StringStruct('CompanyName', 'Alonso Vine'),
      StringStruct('FileDescription', 'Liberty - gestor de patrimonio del hogar, 100% local'),
      StringStruct('FileVersion', '{_ver}'),
      StringStruct('InternalName', 'Liberty'),
      StringStruct('LegalCopyright', 'Alonso Vine. Fork de Rumbo (Dani Dominguez Quant).'),
      StringStruct('OriginalFilename', 'Liberty.exe'),
      StringStruct('ProductName', 'Liberty'),
      StringStruct('ProductVersion', '{_ver}')])]),
    VarFileInfo([VarStruct('Translation', [0x040a, 1200])])])
"""
_os.makedirs("build", exist_ok=True)
_vpath = _os.path.join("build", "version_info.txt")
open(_vpath, "w", encoding="utf-8").write(_vinfo)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Liberty",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,            # deja la "ventana negra" mientras usas la app
    icon="app/web/favicon.ico",
    version=_vpath,          # ficha de versión de Windows (metadatos)
)
