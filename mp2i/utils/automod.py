import logging

import torch
from detoxify import Detoxify

from mp2i import MODEL_DIR


logger = logging.getLogger(__name__)

_model_path = MODEL_DIR / "multilingual.pth"

if _model_path.exists():
    logger.info("Loading the automod model from cache...")
    _model = torch.load(_model_path, weights_only=False)
else:
    _model = Detoxify("multilingual")  # Download the model from the internet
    torch.save(_model, _model_path)


def is_toxic(text: str, treshold=0.95) -> bool:
    """
    Returns True if the text is toxic, False otherwise.
    """
    results = _model.predict([text])
    return results["toxicity"][0] >= treshold
