"""This file contains all the views for the recorder app.
"""
import os
import json
from typing import Union
from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpRequest, HttpResponse, JsonResponse
from src.main.analyzer import save_recording, check_audio_length, speech_to_text
import warnings
warnings.filterwarnings('ignore')


def index(req: HttpRequest) -> Union[HttpResponse, JsonResponse]:
    """ Loads main/index.html and processes POST data (audio input, form data).
    Args:
        req (HttpRequest): Contains information about the page request.

    Returns:
        Renders main/index.html with main_context OR in case of audio upload (AJAX call) returns
        a JsonResponse containing a wrapper rendered to a string (more info in notes). May also return
        a JsonResponse containing an error if an uploaded file is considered too short.

    Notes:
        - Currently the only way I've found to clear POST values and render the page after an AJAX call
        (without redirecting) has been to return the wrapper rendered to a string in JSON, save the JSON in
        session storage using JS, refresh the page, insert the wrapper on the page and then delete it from
        session storage. It's not optimal but it works for now.
    """

    # Create context from JSON and initialize some keys
    with open('main/config.json') as jsonfile:
        req.session.setdefault('context', json.load(jsonfile))

    GOOGLE_AUTHENTICATION_FILE_NAME = "dialogflow.json"
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), GOOGLE_AUTHENTICATION_FILE_NAME)
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = path

    # Create wrapper for session context and update model variables
    context = req.session["context"]

    # On audio upload or in-app recording:
    if req.method == 'POST' and (req.FILES.get("audio_upload", False) or req.FILES.get("audio_recording", False)):

        # Convert audio to .wav and save it
        is_recording = False if req.FILES.get("audio_upload", False) else True
        file = req.FILES['audio_recording'] if is_recording else req.FILES['audio_upload']
        context, to_be_analyzed = save_recording(context=context, file=file, is_recording=is_recording)
        context['text'] = ""
        context['text'] = speech_to_text(context['to_be_analyzed'])

        # Replace session context with wrapper
        req.session['context'] = context

        # Render wrapper and return it to AJAX call
        res = {"text": context['text']}
        return JsonResponse(res)

    context['text'] = ""
    context['to_be_analyzed'] = None
    # Replace session context with wrapper
    req.session['context'] = context
    return render(req, 'main/index.html', req.session['context'])


def info(req: HttpRequest) -> HttpResponse:
    """ Callback for the info view

    Args:
        req (HttpRequest): Incoming request

    Returns:
        HttpResponse: Response produced by this view
    """
    return render(req, "main/info.html")
