""" Contains a module used for analyzing/saving audio files that are sent to the server by recording or upload and
manages some backend tasks for views.py. Also contains a class and method for creating/loading the models as described
in settings.py. The models will only be loaded one time at server start if create_global_models() is used properly.
"""

import logging
import time
import subprocess
from typing import Tuple
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import FileSystemStorage
import librosa
import src.recorder.settings as cfg
import os
import dialogflow_v2 as dialogflow
import mutagen.mp3
import jiwer


def save_recording(context: dict, file: UploadedFile, is_recording: bool = False) -> Tuple[dict, str]:
    """ Converts recording from .webm to .wav if necessary and saves it after.
    TODO: Work for more filetypes (only webm to wav is supported at the moment).

    Arguments:
        context (dict): Context dictionary containing project wide variables.
        file (File): File uploaded to POST (most likely through request.FILES).
        is_recording (bool): Specifies whether the file is a recording or an uploaded file.

    Returns:
        The path to the saved .wav recording (str).
    """
    fs = FileSystemStorage(cfg.MEDIA_ROOT)

    if file:
        if is_recording:
            try:
                # On audio recording:
                filename = fs.save(file.name + '.webm', file)
                # Convert file from webm to wav using FFMPEG:
                webm_path = os.path.join(cfg.MEDIA_ROOT, filename)
                subprocess.call('ffmpeg -y -i {} -acodec pcm_s16le -ac 1 -ar 48000 {}.wav'
                                .format(webm_path,
                                        os.path.join(cfg.MEDIA_ROOT, filename.split('.webm')[0])),
                                shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

                os.remove(webm_path)
                filename = filename.replace(filename.split('.')[-1], 'wav')
                assert (os.path.exists(os.path.join(cfg.MEDIA_ROOT, filename))), \
                    "FFPMEG failed to convert the file to wav, please check if you have FFMPEG installed."

            except Exception as ex:
                logging.error("An error occurred while saving and converting the recording from .webm to .wav.")
                raise ex

        else:
            try:
                filename = fs.save(file.name, file)
                filename = os.path.join(cfg.MEDIA_ROOT, filename)
                if filename.split(".")[-1] == "wav":
                    subprocess.call('ffmpeg -y -i {} -acodec pcm_s16le -ac 1 -ar 48000 {}_converted.wav'
                                    .format(filename, filename[:-4]),
                                    shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    os.remove(filename)
                    filename = filename[:-4] + "_converted.wav"

            except Exception as ex:
                logging.error("An error occurred while saving the uploaded recording.")
                raise ex

        context["filename"] = filename
        context["to_be_analyzed"] = os.path.join(cfg.MEDIA_ROOT, filename)
        if filename.split(".")[-1] == "wav":
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

    except Exception as e:
        try:
            # Call FFMPEG and convert values to 16bit int values (_TEMP_ is added because FFMPEG doesn't support
            # in-place file editing)
            subprocess.call('ffmpeg -y -i {} -acodec pcm_s16le -ar 48000 {}_TEMP_.wav'
                            .format(audio_path, audio_path[:-4]),
                            shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            audio_path = audio_path[:-4] + "_TEMP_.wav"
            assert (os.path.exists(audio_path)), "FFMPEG Could not convert the file properly."

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


def speech_to_text(audio_file_path, language_code="en", project_id="clean-pilot-296112", session_id="me"):
    """Returns the result of detect intent with an audio file as input and the RTF (Real Time Factor)
    Using the same `session_id` between requests allows continuation
    of the conversation."""
    session_client = dialogflow.SessionsClient()

    # Note: hard coding audio_encoding and sample_rate_hertz for simplicity.
    audio_encoding = dialogflow.enums.AudioEncoding.AUDIO_ENCODING_UNSPECIFIED
    if audio_file_path.split(".")[-1] == "wav":
        sample_rate_hertz, length = get_audio_features(audio_file_path)
    else:
        audio = mutagen.mp3.MP3(audio_file_path)
        length = audio.info.length
        sample_rate_hertz = audio.info.sample_rate

    session = session_client.session_path(project_id, session_id)

    with open(audio_file_path, 'rb') as audio_file:
        input_audio = audio_file.read()

    audio_config = dialogflow.types.InputAudioConfig(
        audio_encoding=audio_encoding, language_code=language_code,
        sample_rate_hertz=sample_rate_hertz)
    query_input = dialogflow.types.QueryInput(audio_config=audio_config)

    start = time.time()
    response = session_client.detect_intent(
        session=session, query_input=query_input,
        input_audio=input_audio)

    end = time.time()
    rtf = round((end - start) / length, 2)
    return response.query_result.query_text, rtf


def calculate_metrics(context: dict, truth, hypothesis):
    """ Calculates the relevant metrics for speech recognition model analysis. """
    try:
        hypo_dict = {}
        truth_dict = {}

        for word in hypothesis:
            hypo_dict[word] = hypo_dict[word] + 1 if word in hypo_dict else 1

        for word in truth:
            truth_dict[word] = truth_dict[word] + 1 if word in truth_dict else 1

    except (ZeroDivisionError, ValueError):
        hypo_dict = truth_dict = None

    # WER
    try:
        context['wer'] = round(jiwer.wer(truth=truth, hypothesis=hypothesis), 2)
    except (ZeroDivisionError, ValueError):
        context['wer'] = 0.00

    # WCR
    if hypo_dict and truth_dict:
        try:
            correct = 0
            for key in truth_dict.keys():
                if key in hypo_dict:
                    correct += min(hypo_dict[key], truth_dict[key])

            context['wcr'] = round(correct / len(truth), 2)
        except (ZeroDivisionError, ValueError):
            context['wcr'] = 0.00
    else:
        context['wcr'] = 0.00

    # Precision Micro
    try:
        true_positives = 0
        for true, hypo in zip(truth, hypothesis):
            if true == hypo:
                true_positives += 1

        context["precision_micro"] = round(true_positives / len(hypothesis), 2)
    except (ZeroDivisionError, ValueError):
        context["precision_micro"] = 0.00

    # Precision Macro
    try:
        match_dict = {}
        for word_index in range(len(hypothesis)):
            if word_index < len(truth):
                if hypothesis[word_index] == truth[word_index]:
                    match_dict[hypothesis[word_index]] = match_dict[hypothesis[word_index]] + 1 \
                        if hypothesis[word_index] in match_dict else 1

        sum_precision = sum(match_dict[key] / hypo_dict[key] if key in match_dict else 0 for key in hypo_dict.keys())
        context["precision_macro"] = round(1 / (len(hypo_dict.keys())) * sum_precision, 2)

    except (ZeroDivisionError, ValueError):
        context["precision_macro"] = 0.00

    # Recall Micro
    try:
        true_positives = 0
        for true, hypo in zip(truth, hypothesis):
            if true == hypo:
                true_positives += 1

        context["recall_micro"] = round(true_positives / len(truth), 2)
    except (ZeroDivisionError, ValueError):
        context["recall_micro"] = 0.00

    # Recall Macro
    try:
        match_dict = {}
        for word_index in range(len(truth)):
            if word_index < len(hypothesis):
                if truth[word_index] == hypothesis[word_index]:
                    match_dict[truth[word_index]] = match_dict[truth[word_index]] + 1 \
                        if truth[word_index] in match_dict else 1

        sum_recall = sum(match_dict[key] / truth_dict[key] if key in match_dict else 0 for key in truth_dict.keys())
        context["recall_macro"] = round((1 / len(truth_dict.keys())) * sum_recall, 2)
    except (ZeroDivisionError, ValueError):
        context["recall_macro"] = 0.00

    # F1 Micro
    try:
        context["f1_micro"] = round((2 * context["precision_micro"] * context["recall_micro"]) / \
                                    (context["precision_micro"] + context["recall_micro"]), 2)
    except (ZeroDivisionError, ValueError):
        context["f1_micro"] = 0.00

    # F1 Macro
    try:
        context["f1_macro"] = round((2 * context["precision_macro"] * context["recall_macro"]) / \
                                    (context["precision_macro"] + context["recall_macro"]), 2)
    except (ZeroDivisionError, ValueError):
        context["f1_macro"] = 0.00

    return context
