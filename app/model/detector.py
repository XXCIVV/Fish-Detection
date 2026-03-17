import io
import logging
import torch
from pathlib import Path
from PIL import Image
from ultralytics import YOLO
from config import config 

logger = logging.getLogger(__name__)


class FishDetector:
    def __init__(self):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()

    def _load_model(self):
        """Load YOLO model with a clear error if the file is missing."""
        model_path = Path(config.MODEL_PATH)
        if not model_path.exists():
            raise FileNotFoundError(
                f"Model file not found: {model_path}\n"
                f"Check MODEL_PATH in your .env file."
            )
        try:
            self.model = YOLO(str(model_path))
            self.model.to(self.device)
            logger.info("YOLO model loaded on %s", self.device)
        except Exception as e:
            raise RuntimeError(f"Failed to load YOLO model: {e}") from e

    def predict(self, image_bytes: bytes) -> list[dict]:
        """
        Run detection on raw image bytes.
        Returns a list of dicts: {species, confidence, bbox}
        """
        # decode image — catch corrupt/invalid uploads early
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            raise ValueError(f"Could not decode image: {e}") from e

        results = self.model.predict(
            source=img,
            conf=config.CONFIDENCE_THRESHOLD,
            imgsz=config.IMG_SIZE,
            device=self.device,
            verbose=False,
        )

        detections = []
        result = results[0]

        if result.boxes:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                detections.append({
                    "species":    result.names[cls_id],
                    "confidence": round(float(box.conf[0]), 4),
                    "bbox":       box.xyxy[0].tolist(),
                })

        logger.info("Detected %d object(s)", len(detections))
        return detections  # raw result no longer leaked to callers

    def predict_with_result(self, image_bytes: bytes):
        """
        Extended version that also returns the raw Ultralytics result —
        use this only inside draw_boxes.py where you need it.
        """
        try:
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        except Exception as e:
            raise ValueError(f"Could not decode image: {e}") from e

        results = self.model.predict(
            source=img,
            conf=config.CONFIDENCE_THRESHOLD,
            imgsz=640,
            device=self.device,
            verbose=False,
        )
        result = results[0]
        detections = []
        if result.boxes:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                detections.append({
                    "species":    result.names[cls_id],
                    "confidence": round(float(box.conf[0]), 4),
                    "bbox":       box.xyxy[0].tolist(),
                })
        return detections, result

try:
    detector = FishDetector()
except (FileNotFoundError, RuntimeError) as e:
    logger.error("Could not initialize FishDetector: %s", e)
    detector = None  # routes must check for None and return 503