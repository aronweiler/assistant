import logging
import numpy as np
from openwakeword.model import Model


class WakeWord:
    def get_highest_ranked_prediction(self, predictions, wake_word_models):
        prediction = None
        for wake_word_model in wake_word_models:
            a_prediction = max(
                predictions,
                key=lambda item: item["prediction"][wake_word_model.model_name],
            )
            if (
                prediction is None
                or a_prediction["prediction"][wake_word_model.model_name]
                > prediction["prediction"][wake_word_model.model_name]
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

    def create_verifier_models(self, wake_word_models):
        # Can only have one custom verifier per model.  See https://github.com/dscripka/openWakeWord/issues/34
        # Create a model for each custom verifier in our wake word models configuration
        self.verifier_models = []
        for wake_word_model in wake_word_models:
            if wake_word_model.training_data is None:
                # No training data is available, create the model without the custom verifier
                model = Model(wakeword_models=[wake_word_model.model_path])
            else:
                # Training data is available, use a custom verifier
                model = Model(
                    wakeword_models=[wake_word_model.model_path],
                    custom_verifier_models={
                        wake_word_model.model_name: wake_word_model.training_data
                    },
                    custom_verifier_threshold=0.5,
                )

            self.verifier_models.append(
                {"wake_word_model": wake_word_model, "model": model}
            )
