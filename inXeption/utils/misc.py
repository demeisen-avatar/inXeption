'''
Miscellaneous utility functions for inXeption.
'''

import datetime
import logging
import os
import subprocess
from pathlib import Path

# Initialize logger
logger = logging.getLogger(__name__)

# Sound file directory
SOUNDS_DIR = Path('/opt/inXeption/media/sounds')


def timestamp(t=None):
    if t is None:
        t = datetime.datetime.now()

    return t.strftime('%Y-%m-%d--%H-%M-%S')


def create_or_replace_symlink(symlink_path, target_path):
    symlink_path = Path(symlink_path)

    if symlink_path.is_symlink():
        symlink_path.unlink()

    os.symlink(target_path, symlink_path)


def play_sound(sound_filename, timeout=5.0):
    '''
    Play an audio file using mpg123 in the background.

    Args:
        sound_filename (str): Name of the sound file in the sounds directory
        timeout (float): Timeout in seconds for playback

    Returns:
        bool: True if sound playback was initiated successfully, False otherwise
    '''
    # Check if sound file exists before launching thread
    sound_path = SOUNDS_DIR / sound_filename
    if not sound_path.exists():
        logger.warning(f'Sound file not found: {sound_path}')
        return False

    # Define sound player function
    def _play_sound_thread():
        try:
            subprocess.run(
                ['mpg123', '-q', str(sound_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
            )
        except subprocess.TimeoutExpired:
            logger.warning(f'Sound playback timed out: {sound_filename}')
        except Exception as e:
            logger.error(f'Failed to play sound {sound_filename}: {e}')

    # Always run in a background thread
    import threading

    thread = threading.Thread(target=_play_sound_thread)
    thread.daemon = True  # Don't let this thread block program exit
    thread.start()
    return True
