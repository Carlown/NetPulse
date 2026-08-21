# -*- mode: python ; coding: utf-8 -*-
# NetPulse 打包配置（onedir 模式，供 Inno Setup 打安装包）：
# 排除环境中无关的可编辑安装包（phantom_backend 等），
# 避免把 torch/scipy 等巨型依赖拖进 exe。

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('app.ico', '.'), ('app_logo.png', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio', 'tensorflow', 'numpy.testing',
        'scipy', 'pandas', 'matplotlib', 'phantom_backend', 'IPython',
        'jupyter', 'notebook', 'cv2', 'PIL.ImageQt',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='NetPulse',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NetPulse',
)
