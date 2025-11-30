# defect_analysis_agent/tools.py
import os
from typing import Dict, Any, List

from PIL import Image, ImageDraw, ImageFont
from inference_sdk import InferenceHTTPClient
from langchain_core.tools import tool

from .supabase_saver import save_via_supabase_from_agent

# --- Configuration ---
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")
ROBOFLOW_MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID")
ROBOFLOW_API_URL = os.getenv("ROBOFLOW_API_URL")

CLIENT = InferenceHTTPClient(
    api_url=ROBOFLOW_API_URL,
    api_key=ROBOFLOW_API_KEY,
)


def _pred_to_xyxy(pred: Dict[str, Any]) -> tuple[int, int, int, int]:
    """
    Roboflow prediction (x, y, width, height) center-format
    -> (x1, y1, x2, y2) top-left / bottom-right
    """
    xc = float(pred["x"])
    yc = float(pred["y"])
    w = float(pred["width"])
    h = float(pred["height"])

    x1 = int(xc - w / 2)
    y1 = int(yc - h / 2)
    x2 = int(xc + w / 2)
    y2 = int(yc + h / 2)
    return x1, y1, x2, y2


@tool
def detect_pcb_defects(image_path: str) -> str:
    """
    Analyze a PCB image using Roboflow,
    draw boxes, crop defects, SAVE annotated+crop images to Supabase,
    and return a human-readable summary (with Supabase URLs).

    Args:
        image_path: path ของรูป PCB (เช่น 'defect_analysis_agent/data/Test1.png')
    """
    print(f"[detect_pcb_defects] Start on image: {image_path}")

    if not os.path.exists(image_path):
        return f"Error: Image file not found at {image_path}"

    try:
        # 1) local debug folder
        base_dir = os.path.dirname(__file__)
        output_dir = os.path.join(base_dir, "processed_images")
        os.makedirs(output_dir, exist_ok=True)

        # 2) Roboflow infer
        result = CLIENT.infer(image_path, model_id=ROBOFLOW_MODEL_ID)
        print("[detect_pcb_defects] Roboflow result keys:", result.keys())

        if "predictions" not in result:
            return "Analysis complete: No predictions returned from the model."

        predictions = result["predictions"]
        if not predictions:
            return "Analysis complete: No defects detected in this image."

        # 3) load original image
        original_image = Image.open(image_path).convert("RGB")

        # 4) build annotated + crops
        annotated_image = original_image.copy()
        draw = ImageDraw.Draw(annotated_image)

        try:
            font = ImageFont.truetype("arial.ttf", 15)
        except IOError:
            font = ImageFont.load_default()

        crops_data: List[Dict[str, Any]] = []
        crop_paths: List[str] = []

        for i, detection in enumerate(predictions):
            confidence = float(detection["confidence"])
            if confidence < 0.3:
                continue

            label = detection["class"]
            x1, y1, x2, y2 = _pred_to_xyxy(detection)

            # draw box + label
            draw.rectangle([x1, y1, x2, y2], outline="cyan", width=3)
            draw.text((x1 + 2, y1 - 15), f"{label} {confidence:.2%}", font=font, fill="cyan")

            # crop with padding
            w = x2 - x1
            h = y2 - y1
            padding_x = w * 0.2
            padding_y = h * 0.2

            crop_left = max(0, int(x1 - padding_x))
            crop_top = max(0, int(y1 - padding_y))
            crop_right = min(original_image.width, int(x2 + padding_x))
            crop_bottom = min(original_image.height, int(y2 + padding_y))

            cropped_pcb = original_image.crop((crop_left, crop_top, crop_right, crop_bottom))
            cropped_pcb = cropped_pcb.resize((300, 300))

            crop_filename = f"crop_{i}_{label}.jpg"
            crop_path = os.path.join(output_dir, crop_filename)
            cropped_pcb.save(crop_path)
            crop_paths.append(crop_path)

            crops_data.append(
                {
                    "image": cropped_pcb,
                    "prediction": label,
                    "confidence": confidence,
                    "bbox": {
                        "x": x1,
                        "y": y1,
                        "w": w,
                        "h": h,
                    },
                }
            )

        annotated_filename = "detected_" + os.path.basename(image_path)
        annotated_path = os.path.join(output_dir, annotated_filename)
        annotated_image.save(annotated_path)

        # 5) SAVE TO SUPABASE
        print("[detect_pcb_defects] Calling Supabase saver...")
        supabase_payload = save_via_supabase_from_agent(
            annotated_img=annotated_image,
            crops_data=crops_data,
            original_filename=os.path.basename(image_path),
            board_code=None,
            note="Saved from defect-analysis-agent",
        )
        # print("[detect_pcb_defects] Supabase payload:", supabase_payload)

        main_image = supabase_payload.get("main_image", {})
        crops_supabase = supabase_payload.get("crops", [])

        # 6) build summary text (with URLs)
        summary = f"✅ Analysis complete for `{image_path}`.\n\n"
        summary += f"📊 **Total Defects Found: {len(crops_data)}**\n\n"

        if main_image:
            summary += "**Main Detected Image (Supabase):**\n"
            summary += f"- ID: `{main_image.get('id')}`\n"
            summary += f"- URL: {main_image.get('public_url')}\n"
            summary += f"- Size: {main_image.get('width')} x {main_image.get('height')}\n\n"

        summary += "**Detailed Defect List (with Supabase crop URLs):**\n"
        for i, (p, s_crop) in enumerate(zip(predictions, crops_supabase), start=1):
            confidence_pct = float(p["confidence"]) * 100
            summary += f"\n**Defect #{i}:**\n"
            summary += f"  - Type: {p['class']}\n"
            summary += f"  - Confidence: {confidence_pct:.2f}%\n"
            summary += f"  - Location (center): X={p['x']:.1f}, Y={p['y']:.1f}\n"
            summary += f"  - Size: Width={p['width']:.1f}, Height={p['height']:.1f}\n"
            summary += f"  - Supabase Crop URL: {s_crop.get('crop_public_url')}\n"

        summary += "\n\n📂 **Local Visual Evidence (for debugging):**\n"
        summary += f"- Annotated Full Image: {annotated_path}\n"
        summary += f"- Total Cropped Images (local): {len(crop_paths)}\n"
        for i, crop_path in enumerate(crop_paths, start=1):
            summary += f"  - Crop #{i}: {crop_path}\n"

        return summary

    except Exception as e:
        # ถ้า Supabase พัง / อะไรผิด จะเห็น error ตรงนี้
        return f"Error during defect detection: {str(e)}"
