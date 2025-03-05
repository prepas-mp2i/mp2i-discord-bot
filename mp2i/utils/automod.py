from typing import Dict

import logging
from pathlib import Path

import discord
import numpy as np
import onnxruntime as ort
from tokenizers import Tokenizer

from mp2i import MODEL_DIR
from mp2i.wrappers.guild import GuildWrapper

logger = logging.getLogger(__name__)


def softmax(x, axis=None):
    """
    Applies the softmax function to the model's raw output.
    """
    e_x = np.exp(x - np.max(x, axis=axis, keepdims=True))
    return e_x / e_x.sum(axis=axis, keepdims=True)


def is_toxic(msg: discord.Message) -> bool:
    """
    Check if a message is toxic or not.
    """
    return _classifier.predict(msg.content, treshold=0.9)


async def moderate(msg: discord.Message) -> None:
    """
    Moderates a message by deleting it and sending logs.
    """
    await msg.delete()  # Will trigger on_message_delete event
    embed = discord.Embed(
        title="Message modéré pour contenu inapproprié",
        description=f">>> {msg.content}",
        colour=0xFFA325,
    )
    guild = GuildWrapper(msg.guild)
    await guild.log_channel.send(embed=embed)


class ToxicityClassifier:
    """
    A class for handling text toxicity classification using an ONNX model.
    """

    def __init__(self, name: str, model_dir: Path) -> None:
        """
        Initializes the classifier by loading the tokenizer and the ONNX session.

        Args:
            model_name: The name of the model used for classification.
            model_dir: The directory containing the model and tokenizer files.
        """
        self.name = name
        self.model_dir = model_dir / name.rpartition("/")[2]
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

    def encode_text(self, text: str, max_length=32) -> Dict:
        """
        Encodes a text input into a representation with token IDs and an attention mask.
        """
        encoded = self._tokenizer.encode(text)
        input_ids = np.zeros((1, max_length), dtype=np.int64)
        input_ids[0, : min(max_length, len(encoded.ids))] = encoded.ids[:max_length]
        attention_mask = (input_ids != 0).astype(np.int64)
        return dict(input_ids=input_ids, attention_mask=attention_mask)

    def predict(self, text: str, treshold=0.9) -> bool:
        """
        Predict whether the given text is toxic or not based on a probability threshold.

        Args:
            text: The text to classify.
            threshold: The probability threshold to determine if the text is toxic.

        Returns:
            bool: True if the text is toxic, otherwise False.
        """
        inputs = self.encode_text(text)
        outputs = self._session.run(None, inputs)
        results = softmax(outputs[0], axis=1)
        return results[0][0] >= treshold

    @classmethod
    def export_model(cls, name: str, export_dir: Path) -> None:
        """
        Exports a pre-trained model to the ONNX format.
        """
        from transformers import AutoModelForSequenceClassification
        from optimum.exporters.onnx import onnx_export_from_model

        model = AutoModelForSequenceClassification.from_pretrained(name)
        onnx_export_from_model(
            model, export_dir, task="text-classification", optimize=None, opset=14
        )


_classifier = ToxicityClassifier(
    "citizenlab/distilbert-base-multilingual-cased-toxicity", MODEL_DIR
)
