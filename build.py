import PyInstaller.__main__

PyInstaller.__main__.run([
    'Project-1.py',
    '--name=Dungeon Crawler',
    '--onefile',
    '--noconsole',
    '--icon=game_icon.ico',
    '--add-data=game_icon.png;.',
    '--add-data=player.png;.',
    '--add-data=enemy.png;.',
    '--add-data=wall.png;.',
    '--add-data=bush.png;.',
    '--add-data=walk.wav;.',
    '--add-data=run.wav;.',
    '--add-data=alert.wav;.',
    '--add-data=win.wav;.',
    '--add-data=lose.wav;.',
    '--add-data=hide.wav;.',
    '--add-data=skeleton.wav;.',
    '--add-data=background_music.mp3;.'
])
