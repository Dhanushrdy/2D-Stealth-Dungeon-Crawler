import PyInstaller.__main__

PyInstaller.__main__.run([
    'Project-1.py',
    '--name=Dungeon Crawler',
    '--onefile',
    '--noconsole',
    '--icon=Assets/Image Assets/game_icon.ico',
    '--add-data=Assets;Assets'
])
