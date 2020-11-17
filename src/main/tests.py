""" Contains the tests for this application """

import io
from django.test import TestCase, RequestFactory
from django.urls import reverse
from pydub import AudioSegment
from src.recorder import settings as cfg
from src.main.analyzer import *
from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.storage import FileSystemStorage
import json


class UnitTestCase(TestCase):
    """ Unit test class for main app """

    @classmethod
    def setUpTestData(cls):
        """ Runs at the beginning of the unit tests """
        cls.factory = RequestFactory()
        #  Initialize request and session variables
        cls.request = cls.factory.get('index')
        middleware = SessionMiddleware()
        middleware.process_request(cls.request)
        cls.request.session.save()

        with open('main/config.json') as jsonfile:
            cls.request.session.setdefault('context', json.load(jsonfile))

        # Set up test audio with proper length
        cls.test_audio = AudioSegment.silent(duration=cfg.MIN_LEN * 1000 + 1)\
            .export(io.BytesIO(), format="wav")
        cls.test_audio.name = "testing.wav"
        cls.test_audio.seek(0)
        cls.test_audio_path = os.path.join(cfg.MEDIA_ROOT, "input",
                                           FileSystemStorage(os.path.join(cfg.MEDIA_ROOT, "input"))
                                           .save(cls.test_audio.name, cls.test_audio))

        cls.request.session['context']["to_be_analyzed"] = cls.test_audio_path

    @classmethod
    def tearDownClass(cls):
        """ Runs at the end of the unit tests """
        if os.path.exists(cls.test_audio_path):
            os.remove(cls.test_audio_path)

    def test_home_get(self):
        """ Test home page (GET) """
        # Test home page existence
        res = self.client.get(reverse("index"))
        self.assertTemplateUsed(res, "main/index.html")
        self.assertContains(res, "Record Audio")

    def test_home_post(self):
        """ Test home page(POST) """

        # Test record/upload audio processing
        audio = self.test_audio
        audio.name = "testing2.wav"
        audio.seek(0)
        form_data = {
            "audio_upload": audio
        }

        res = self.client.post(reverse("index"), form_data)
        self.assertContains(res, "Results")

        # Remove uploaded test file
        file_path = os.path.join(cfg.MEDIA_ROOT, "input", audio.name)
        if os.path.exists(file_path):
            os.remove(file_path)

    def test_home_post_too_short(self):
        """ Test home page with too short audio file (POST) """
        # Create too short silent audio file
        f = AudioSegment.silent(duration=cfg.MIN_LEN * 1000 - 100) \
                        .export(io.BytesIO(), format="wav")
        f.name = "testing2.wav"
        f.seek(0)

        # Test record/upload audio processing too short audio file
        form_data = {
            "audio_upload": f
        }

        res = self.client.post(reverse("index"), form_data)
        self.assertContains(res, "too short", status_code=400)

        # Remove uploaded test file
        file_path = os.path.join(cfg.MEDIA_ROOT, "input", f.name)
        if os.path.exists(file_path):
            os.remove(file_path)

    def test_info_page(self):
        """ Test info page (GET) """
        # Test info page existence
        res = self.client.get(reverse("info"))
        self.assertTemplateUsed(res, "main/info.html")
        self.assertContains(res, "Datasets")

    # analyzer.py Tests

    def test_analyzer_save_audio_upload(self):
        """ Analyzer save a wav file with save_recording() """

        _, file_path = save_recording(self.request.session['context'], self.test_audio, False)
        exists = os.path.exists(file_path)
        self.assertTrue(exists)
        os.remove(file_path)

    def test_analyzer_check_audio_length(self):
        # Test proper length audio file
        check1 = check_audio_length(self.test_audio_path)

        # Test too short audio file
        f = AudioSegment.silent(duration=cfg.MIN_LEN * 1000 - 100) \
                        .export(io.BytesIO(), format="wav")
        f.name = "testing2.wav"
        f.seek(0)
        _, file_path = save_recording(self.request.session['context'], f, False)
        check2 = check_audio_length(file_path)

        self.assertTrue(check1)
        self.assertFalse(check2)

        if os.path.exists(file_path):
            os.remove(file_path)
