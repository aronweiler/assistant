import logging
import os
from typing import Any
import numpy as np
from openwakeword.model import Model


class WakeWord:
    def __init__(self, wake_word_model_paths) -> None:
        self.verifier_models = []               
        
        for wake_word_model_path in wake_word_model_paths:
            # Get the name of the model (last part of the path without the extension)
            wake_word_model_name = os.path.splitext(os.path.basename(wake_word_model_path))[0]
            model = Model(wakeword_models=[wake_word_model_path])

            self.verifier_models.append(
                {"wake_word_model": wake_word_model_name, "model": model}
            )
        
    
    def get_highest_ranked_prediction(self, predictions, wake_word_model_paths):
        prediction = None
        for wake_word_model_path in wake_word_model_paths:
            # Get the name of the model (last part of the path without the extension)
            wake_word_model_name = os.path.splitext(os.path.basename(wake_word_model_path))[0]
            
            a_prediction = max(
                predictions,
                key=lambda item: item["prediction"][wake_word_model_name],
            )
            if (
                prediction is None
                or a_prediction["prediction"][wake_word_model_name]
                > prediction["prediction"][wake_word_model_name]
            ):
                prediction = a_prediction

        return prediction

    def get_wake_word_predictions(self, frame):
        predictions = []
        for model in self.verifier_models:
            predictions.append(
                {
                    "prediction": model["model"].predict(
                        np.frombuffer(frame, dtype=np.int16)
                    ),
                    "wake_word_model": model["wake_word_model"],
                }
            )

        return predictions