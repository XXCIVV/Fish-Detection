import hashlib
import logging
import uuid
from pathlib import Path
from typing import TypedDict

import cv2
import numpy as np

from config import config

logger = logging.getLogger(__name__)


class Detection(TypedDict):
    species: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2]


def _species_color(species: str) -> tuple[int, int, int]:
    digest = hashlib.md5(species.encode()).hexdigest()
    r = max(80, int(digest[0:2], 16))
    g = max(80, int(digest[2:4], 16))
    b = max(80, int(digest[4:6], 16))
    return (r, g, b)


def draw_detections(image_bytes: bytes, detections: list[Detection]) -> np.ndarray:
    """
    Draw bounding boxes and labels onto an image.
    Raises ValueError if image bytes cannot be decoded.
    """
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        raise ValueError("Could not decode image bytes — file may be corrupt or not a valid image.")

    img_h = img.shape[0]

    for det in detections:
        x1, y1, x2, y2 = map(int, det["bbox"])
        species = det["species"]
        conf = det["confidence"]
        color = _species_color(species)
        label_text = f"{species}: {conf:.2f}"

        # bounding box
        cv2.rectangle(img, (x1, y1), (x2, y2), color, 2)

        # measure label background
        (text_w, text_h), _ = cv2.getTextSize(
            label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1
        )
        pad = 4

        # draw label above box, or below if too close to top edge
        if y1 - text_h - pad * 2 >= 0:
            bg_y1, bg_y2 = y1 - text_h - pad * 2, y1
            txt_y = y1 - pad
        else:
            bg_y1, bg_y2 = y2, y2 + text_h + pad * 2
            txt_y = y2 + text_h + pad

        cv2.rectangle(img, (x1, bg_y1), (x1 + text_w + pad, bg_y2), color, -1)
        cv2.putText(
            img, label_text, (x1 + pad // 2, txt_y),
            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1,
            lineType=cv2.LINE_AA,  # anti-aliased text — sharper on screen
        )

    return img


def encode_image(image_array: np.ndarray, quality: int = 92) -> bytes:
    """Encode a numpy array to JPEG bytes. Raises RuntimeError on failure."""
    success, buffer = cv2.imencode(
        ".jpg", image_array, [cv2.IMWRITE_JPEG_QUALITY, quality]
    )
    if not success:
        raise RuntimeError("Failed to encode image to JPEG.")
    return buffer.tobytes()


def save_image(image_array: np.ndarray, filename: str | None = None) -> Path:
    """
    Save annotated image to static/outputs/.
    Returns the saved file path.
    """
    output_dir = Path(config.OUTPUT_FOLDER)
    output_dir.mkdir(parents=True, exist_ok=True)

    if filename is None:
        filename = f"{uuid.uuid4().hex}.jpg"

    output_path = output_dir / filename
    success, buffer = cv2.imencode(
        ".jpg", image_array, [cv2.IMWRITE_JPEG_QUALITY, 92]
    )
    if not success:
        raise RuntimeError("Failed to encode image for saving.")

    output_path.write_bytes(buffer.tobytes())
    logger.info("Saved annotated image to %s", output_path)
    return output_path