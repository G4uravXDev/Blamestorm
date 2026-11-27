# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
import os

block_cipher = None

# Collect all Django and application modules
django_datas, django_binaries, django_hiddenimports = collect_all('django')
zit_app_datas, zit_app_binaries, zit_app_hiddenimports = collect_all('zit_app')
google_genai_datas, google_genai_binaries, google_genai_hiddenimports = collect_all('google.genai')

datas = [
    ('zit_app/templates', 'zit_app/templates'),
    ('zit_app/static', 'zit_app/static'),
    ('zit_app/migrations', 'zit_app/migrations'),
] + django_datas + zit_app_datas + google_genai_datas

hiddenimports = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sessions.backends.db',
    'django.contrib.auth.middleware',
    'django.contrib.messages.middleware',
    'django.contrib.sessions.middleware',
    'django.middleware.security',
    'django.middleware.common',
    'django.middleware.csrf',
    'django.middleware.clickjacking',
    'django.template.backends.django',
    'django.db.backends.sqlite3',
    'django.core.management.commands.runserver',
    'django.core.management.commands.migrate',
    'zit_core',
    'zit_core.settings',
    'zit_core.urls',
    'zit_core.wsgi',
    'zit_app',
    'zit_app.models',
    'zit_app.views',
    'zit_app.urls',
    'zit_app.context_processors',
    'zit_app.git_engine',
    'zit_app.git_engine.runner',
    'zit_app.git_engine.status',
    'zit_app.git_engine.diff',
    'zit_app.git_engine.log',
    'zit_app.git_engine.branch',
    'zit_app.git_engine.remote',
    'zit_app.git_engine.stash',
    'zit_app.git_engine.merge',
    'zit_app.git_engine.bisect',
    'zit_app.git_engine.cherry_pick',
    'zit_app.git_engine.time_travel',
    'zit_app.git_engine.reflog',
    'zit_app.git_engine.secrets',
    'zit_app.ai_engine',
    'zit_app.ai_engine.gemini_client',
    'zit_app.ai_engine.prompts',
    'zit_app.ai_engine.agent_runner',
] + django_hiddenimports + zit_app_hiddenimports + google_genai_hiddenimports

# Deduplicate hiddenimports
hiddenimports = list(set(hiddenimports))

a = Analysis(
    ['blamestorm.py'],
    pathex=['.'],
    binaries=django_binaries + zit_app_binaries + google_genai_binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'numpy', 'torch', 'pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='blamestorm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
