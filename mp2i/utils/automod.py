import logging

import torch
from detoxify import Detoxify

from mp2i import MODEL_DIR


logger = logging.getLogger(__name__)

_model_path = MODEL_DIR / "multilingual.pth"

if _model_path.exists():
    _model = torch.load(_model_path)
else:
    _model = Detoxify("multilingual")
    torch.save(_model, _model_path)


def is_toxic(text: str, treshold=0.95) -> float:
    """
    Returns True if the text is toxic, False otherwise.
    """
    results = _model.predict([text])[0]
    return results["toxicity"] >= treshold
