""" Contains a module used for analyzing/saving audio files that are sent to the server by recording or upload and
manages some backend tasks for views.py. Also contains a class and method for creating/loading the models as described
in settings.py. The models will only be loaded one time at server start if create_global_models() is used properly.
"""

import logging
import shutil
import subprocess
from typing import Tuple
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import FileSystemStorage
import librosa
import src.recorder.settings as cfg
import os


def save_recording(context: dict, file: UploadedFile) -> Tuple[dict, str]:
    """ Saves recordings.

    Arguments:
        context (dict): Context dictionary containing project wide variables.
        file (File): File uploaded to POST (most likely through request.FILES).

    Returns:
        The path to the saved .wav recording (str).
    """
    fs = FileSystemStorage(cfg.MEDIA_ROOT)

    if file:
        try:
            filename = fs.save(file.name, file)
        except Exception as ex:
            logging.error("An error occurred while saving the uploaded recording.")
            raise ex

        context["filename"] = filename
        context["to_be_analyzed"] = os.path.join(cfg.MEDIA_ROOT, filename)
        context["audio_bitrate"], context["audio_length"] = \
            get_audio_features(context["to_be_analyzed"], round_duration=True)

        if filename:
            context["audio_extension"] = filename.split('.')[-1]

        return context, context["to_be_analyzed"]


def get_audio_features(audio_path: str, round_duration: bool = False) -> Tuple[int, float]:
    """ Gets audio features (bitrate, length).

    Arguments:
        audio_path (str): Path to the audio file (wav).
        round_duration (bool): Should the duration in seconds be rounded to 2 decimals?

    Returns:
        2 audio features (audio_bitrate, audio_length).
    """
    # If opening file gives Exception, convert with FFMPEG and try again, if it still doesn't work raise Exception.
    try:
        y, sr = librosa.load(audio_path, sr=None)
        duration = librosa.core.get_duration(y, sr)

    except Exception:
        try:
            # Call FFMPEG and convert values to 16bit int values (_TEMP_ is added because FFMPEG doesn't support
            # in-place file editing)
            subprocess.call('ffmpeg -y -i {} -acodec pcm_s16le -ar 44100 {}_TEMP_.wav'
                            .format(audio_path, audio_path[:-4]),
                            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            audio_path = audio_path[:-4] + "_TEMP_.wav"
            assert(os.path.exists(audio_path)), "FFMPEG Could not convert the file properly."

            y, sr = librosa.load(audio_path, sr=None)
            duration = librosa.core.get_duration(y, sr)

        except Exception as ex:
            logging.error("Audio features could not be resolved.")
            raise ex

        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)

    if round_duration:
        duration = int(duration * 100) / 100.00

    return sr, duration


def check_audio_length(file_path: str) -> bool:
    """ Checks whether or not an audio file is long enough to predict with.

    Args:
        file_path (str): Path to the audio file.

    Returns:
        bool: True if the file is long enough, otherwise False.
    """
    try:
        _, duration = get_audio_features(file_path)

        return duration >= cfg.MIN_LEN

    except Exception as ex:
        logging.error("Something went wrong while checking the duration of the file (is file valid?).")
        raise ex
