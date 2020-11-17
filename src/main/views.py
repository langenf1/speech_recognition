"""This file contains all the views for the recorder app.
"""
import os
import json
from typing import Union
from django.shortcuts import render
from django.template.loader import render_to_string
from django.http import HttpRequest, HttpResponse, JsonResponse
from src.main.analyzer import save_recording, check_audio_length
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

    # Create wrapper for session context and update model variables
    context = req.session["context"]

    # On audio upload or in-app recording:
    if req.method == 'POST' and (req.FILES.get("audio_upload", False)):

        # Convert audio to .wav and save it
        file = req.FILES['audio_upload']
        context, to_be_analyzed = save_recording(context=context, file=file)

        if not check_audio_length(to_be_analyzed):
            # Audio file too short, remove file and return error
            os.remove(to_be_analyzed)
            return JsonResponse({"error": "Audio file is too short"}, status=400)

        # Replace session context with wrapper
        req.session['context'] = context

        # Render wrapper and return it to AJAX call
        res = {"html": render_to_string('main/result.html', context=req.session['context'], request=req)}
        return JsonResponse(res)

    # Reset file/result handler
    context['analyzed_file'] = None

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
