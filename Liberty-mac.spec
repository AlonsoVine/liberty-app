# -*- mode: python ; coding: utf-8 -*-
# PyInstaller (macOS): empaqueta la app en «Liberty.app».
# Se construye en un Mac (o en el runner macOS de GitHub Actions, ver
# .github/workflows/build-mac.yml):
#     pyinstaller Liberty-mac.spec --noconfirm --clean
# El icono (build/Liberty.icns) lo genera el workflow a partir de app/web/icono-512.png;
# si no existe, se compila sin icono (útil para una prueba local rápida).
import os

_ver = open(os.path.join("app", "VERSION"), encoding="utf-8").read().strip()
_icns = os.path.join("build", "Liberty.icns")
_icono = _icns if os.path.exists(_icns) else None

a = Analysis(
    ["lanzar.py"],
    pathex=[],
    binaries=[],
    # Mismos recursos de solo lectura que la versión de Windows.
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

# onedir + BUNDLE = un Liberty.app propio de macOS (lo normal para apps de escritorio).
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Liberty",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,          # app de ventana: aparece en el Dock y se sale con «Salir»
    icon=_icono,
    # universal2 = un solo binario con las dos arquitecturas (Apple Silicon + Intel).
    # Requiere un Python universal2 (el del instalador de python.org) y que toda
    # extensión C (aquí solo markupsafe._speedups) sea también universal2: lo asegura
    # el workflow build-mac.yml. En un Mac de una sola arquitectura, deja target_arch=None.
    target_arch=os.environ.get("LIBERTY_TARGET_ARCH") or None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="Liberty",
)
app = BUNDLE(
    coll,
    name="Liberty.app",
    icon=_icono,
    bundle_identifier="com.alonsovine.liberty",
    version=_ver,
    info_plist={
        "CFBundleName": "Liberty",
        "CFBundleDisplayName": "Liberty",
        "CFBundleShortVersionString": _ver,
        "CFBundleVersion": _ver,
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.finance",
        "NSHumanReadableCopyright": "Alonso Vine. Fork de Rumbo (Dani Dominguez Quant).",
    },
)
