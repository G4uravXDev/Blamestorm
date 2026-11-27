# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules, collect_data_files
import os

block_cipher = None

# Collect all Django and application modules
django_datas, django_binaries, django_hiddenimports = collect_all('django')
blame_app_datas, blame_app_binaries, blame_app_hiddenimports = collect_all('blame_app')
google_genai_datas, google_genai_binaries, google_genai_hiddenimports = collect_all('google.genai')

datas = [
    ('blame_app/templates', 'blame_app/templates'),
    ('blame_app/static', 'blame_app/static'),
    ('blame_app/migrations', 'blame_app/migrations'),
] + django_datas + blame_app_datas + google_genai_datas

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
    'blame_core',
    'blame_core.settings',
    'blame_core.urls',
    'blame_core.wsgi',
    'blame_app',
    'blame_app.models',
    'blame_app.views',
    'blame_app.urls',
    'blame_app.context_processors',
    'blame_app.git_engine',
    'blame_app.git_engine.runner',
    'blame_app.git_engine.status',
    'blame_app.git_engine.diff',
    'blame_app.git_engine.log',
    'blame_app.git_engine.branch',
    'blame_app.git_engine.remote',
    'blame_app.git_engine.stash',
    'blame_app.git_engine.merge',
    'blame_app.git_engine.bisect',
    'blame_app.git_engine.cherry_pick',
    'blame_app.git_engine.time_travel',
    'blame_app.git_engine.reflog',
    'blame_app.git_engine.secrets',
    'blame_app.ai_engine',
    'blame_app.ai_engine.gemini_client',
    'blame_app.ai_engine.prompts',
    'blame_app.ai_engine.agent_runner',
] + django_hiddenimports + blame_app_hiddenimports + google_genai_hiddenimports

# Deduplicate hiddenimports
hiddenimports = list(set(hiddenimports))

a = Analysis(
    ['blamestorm.py'],
    pathex=['.'],
    binaries=django_binaries + blame_app_binaries + google_genai_binaries,
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

