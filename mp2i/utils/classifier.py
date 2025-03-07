from typing import Dict

import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from mp2i import MODEL_DIR

logger = logging.getLogger(__name__)


class ToxicityClassifier:
    """
    A class for handling text toxicity classification using an ONNX model.
    """

    def __init__(self, model_dir: Path) -> None:
        """
        Initializes the classifier by loading the tokenizer and the ONNX session.

        Args:
            model_dir: The directory containing the model and tokenizer files.
        """
        self.model_dir = model_dir
        self._tokenizer = self._load_tokenizer()
        self._session = self._load_onnx_session()

    def _load_tokenizer(self) -> Tokenizer:
        tokenizer_path = self.model_dir / "tokenizer.json"
        if not tokenizer_path.exists():
            raise FileNotFoundError(f"Tokenizer file not found at {tokenizer_path}")

        return Tokenizer.from_file(tokenizer_path.as_posix())

    def _load_onnx_session(self) -> ort.InferenceSession:
        onnx_path = self.model_dir / "model.onnx"
        if not onnx_path.exists():
            raise FileNotFoundError(f"ONNX model file not found at {onnx_path}")

        return ort.InferenceSession(onnx_path.as_posix())

    @staticmethod
    def export_model(model_name: str) -> None:
        """
        Exports a pre-trained model to the ONNX format and quantizes it.
        """
        from transformers import AutoModelForSequenceClassification
        from optimum.exporters.onnx import onnx_export_from_model
        from onnxruntime.quantization import quantize_dynamic

        export_dir = MODEL_DIR / model_name.rpartition("/")[2]
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        onnx_export_from_model(
            model,
            output=export_dir,
            task="text-classification",
            monolith=True,
            optimize="O1",
            opset=15,
        )
        quantize_dynamic(export_dir / "model.onnx", export_dir / "model.onnx")

    @staticmethod
    def softmax(x, axis=None):
        e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
        return e_x / e_x.sum(axis=axis, keepdims=True)

    @staticmethod
    def sigmoid(x):
        return 1 / (1 + np.exp(-x))

    def _encode_text(self, text: str, max_length=256) -> Dict:
        """
        Encodes a text input into a representation with token IDs and an attention mask.
        """
        encoded = self._tokenizer.encode(text)
        input_ids = np.array(encoded.ids[:max_length])[np.newaxis, :]
        return dict(
            input_ids=input_ids.astype(np.int64),
            attention_mask=(input_ids != 0).astype(np.int64),
        )

    def _probabilities(self, logits: np.ndarray) -> np.ndarray:
        if logits.shape[1] == 1:
            return self.sigmoid(logits)
        return self.softmax(logits, axis=1)

    def predict(self, text: str, threshold=0.9) -> bool:
        """
        Predict whether the given text is toxic or not based on a probability threshold.

        Args:
            text: The text to classify.
            threshold: The probability threshold to determine if the text is toxic.
        """
        inputs = self._encode_text(text)
        output = self._session.run(None, inputs)
        probs = self._probabilities(output[0])
        return probs[0][0] >= threshold
