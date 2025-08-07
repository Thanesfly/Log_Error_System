# ai_model/model.py

import os
import joblib
import numpy as np
from functools import lru_cache

@lru_cache(maxsize=1)
def load_model_and_vectorizer():
    _dir = os.path.dirname(__file__)
    model = joblib.load(os.path.join(_dir, "model.pkl"))
    vectorizer = joblib.load(os.path.join(_dir, "vectorizer.pkl"))
    return model, vectorizer

def predict_solution(message, return_confidence=False):
    model, vectorizer = load_model_and_vectorizer()
    vect_msg = vectorizer.transform([message])
    prediction = model.predict(vect_msg)[0]

    if return_confidence and hasattr(model, "predict_proba"):
        confidence = np.max(model.predict_proba(vect_msg))
        return prediction, confidence
    return prediction

print("✅ AI model loaded.")