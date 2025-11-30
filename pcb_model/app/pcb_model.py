# app/pcb_model.py
import os
from io import BytesIO

from PIL import Image, ImageDraw
from inference_sdk import InferenceHTTPClient


# ===== Roboflow config =====
API_URL = os.getenv("ROBOFLOW_API_URL")
API_KEY = os.getenv("ROBOFLOW_API_KEY")
MODEL_ID = os.getenv("ROBOFLOW_MODEL_ID")

CLIENT = InferenceHTTPClient(
    api_url=API_URL,
    api_key=API_KEY,
)


def _pred_to_xyxy(pred: dict) -> tuple[int, int, int, int]:
    """
    Roboflow คืน x,y,width,height แบบ center-format
    แปลงเป็น x1,y1,x2,y2 (มุมซ้ายบน–ขวาล่าง)
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


def run_pcb_detection(
    image_path: str,
    model_path: str = "best.pt",  # ไม่ได้ใช้แล้ว แต่คง argument ไว้ให้โค้ดอื่นไม่พัง
):
    """
    รัน Roboflow model กับรูป PCB 1 รูป
    * ไม่ยุ่งกับ Supabase
    * คืนผลลัพธ์เป็น dict ที่มี
      - annotated_image: bytes + meta
      - crops: list ของ defect crop (bytes + prediction + confidence + bbox)
    โครงสร้างเหมือนเวอร์ชัน YOLO เดิม เพื่อให้ส่วนอื่นใช้ต่อได้เลย
    """
    # 1) โหลดรูป input (raw image) ด้วย PIL
    img = Image.open(image_path).convert("RGB")

    # 2) เรียก Roboflow inference
    result = CLIENT.infer(image_path, model_id=MODEL_ID)

    preds = result.get("predictions", [])
    img_w = result.get("image", {}).get("width", img.width)
    img_h = result.get("image", {}).get("height", img.height)

    # 3) สร้าง annotated image (วาดกล่อง defect ลงรูปหลัก)
    annotated_img = img.copy()
    draw = ImageDraw.Draw(annotated_img)

    # วาดกล่องครอบ / label
    for p in preds:
        x1, y1, x2, y2 = _pred_to_xyxy(p)
        cls_name = p.get("class", "unknown")
        conf = float(p.get("confidence", 0.0))

        # วาด rect
        draw.rectangle([(x1, y1), (x2, y2)], outline="yellow", width=3)
        # วาด text เล็ก ๆ ด้านบนซ้ายของ box
        label = f"{cls_name} {conf:.2f}"
        # note: ไม่ใส่ font custom ก็ใช้ default ได้
        draw.text((x1 + 2, y1 + 2), label, fill="yellow")

    # แปลง annotated image เป็น bytes (PNG)
    main_buf = BytesIO()
    annotated_img.save(main_buf, format="PNG")
    main_buf.seek(0)
    main_bytes = main_buf.getvalue()

    detection_result = {
        "annotated_image": {
            "bytes": main_bytes,
            "width": img_w,
            "height": img_h,
            "original_filename": os.path.basename(image_path),
        },
        "crops": [],
    }

    print("\n==== DETECTIONS (from Roboflow) ====")
    if not preds:
        print("No defects detected.")
        return detection_result

    # 4) loop แต่ละ prediction → crop + เก็บ prediction/confidence + bbox
    for i, p in enumerate(preds):
        cls_name = p.get("class", "unknown")
        conf = float(p.get("confidence", 0.0))
        x1, y1, x2, y2 = _pred_to_xyxy(p)

        print(f"- {cls_name} ({conf:.2f}) box: {x1},{y1},{x2},{y2}")

        # crop จากรูปต้นฉบับ
        crop_img = img.crop((x1, y1, x2, y2))

        crop_buf = BytesIO()
        crop_img.save(crop_buf, format="PNG")
        crop_buf.seek(0)
        crop_bytes = crop_buf.getvalue()

        crop_info = {
            "bytes": crop_bytes,
            "width": crop_img.width,
            "height": crop_img.height,
            "prediction": cls_name,
            "confidence": conf,
            "bbox": {
                "x": x1,
                "y": y1,
                "w": x2 - x1,
                "h": y2 - y1,
            },
        }
        detection_result["crops"].append(crop_info)

    return detection_result


if __name__ == "__main__":
    # ตัวอย่างใช้รันเดี่ยว ๆ เพื่อเช็คว่า model ทำงาน
    result = run_pcb_detection("test2.png")
    print("\nSummary:")
    print(
        " Annotated image size:",
        result["annotated_image"]["width"],
        "x",
        result["annotated_image"]["height"],
    )
    print(" Num crops:", len(result["crops"]))
