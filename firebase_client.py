import json
import os

import firebase_admin
from firebase_admin import credentials, firestore

_app = None


def _init_app():
    global _app
    if _app is None:
        cred_dict = json.loads(os.environ["FIREBASE_SERVICE_ACCOUNT_JSON"])
        cred = credentials.Certificate(cred_dict)
        _app = firebase_admin.initialize_app(cred)
    return _app


def get_firestore_client():
    _init_app()
    return firestore.client()
