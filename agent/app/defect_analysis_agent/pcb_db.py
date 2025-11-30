# pcb_db.py
import os
import uuid

from dotenv import load_dotenv
from supabase import create_client, Client


from typing import List, Dict, Any

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # หรือ SUPABASE_KEY ถ้าใช้ชื่ออื่น
BUCKET_NAME = os.getenv("SUPABASE_BUCKET_NAME", "pcb-images")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ---------- Helper: upload to Storage ----------

def upload_to_storage(bytes_data: bytes, folder: str, ext: str = "png") -> tuple[str, str]:
    """
    อัพโหลดไฟล์ไป Supabase Storage
    return (storage_path, public_url)
    """
    filename = f"{uuid.uuid4().hex}.{ext}"
    storage_path = f"{folder}/{filename}"

    # ถ้า error มันจะ throw exception เอง
    supabase.storage.from_(BUCKET_NAME).upload(
        path=storage_path,
        file=bytes_data,
        file_options={"content-type": f"image/{ext}"},
    )

    public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(storage_path)
    return storage_path, public_url


# ---------- DB Insert Helpers ----------

def insert_main_image(
    storage_path: str,
    public_url: str,
    width: int,
    height: int,
    original_filename: str | None = None,
    board_code: str | None = None,
    note: str | None = None,
) -> str:
    """
    Insert row ลง pcb_main_images แล้วคืน id (string)
    """
    data = {
        "storage_path": storage_path,
        "public_url": public_url,
        "width": width,
        "height": height,
        "original_filename": original_filename,
        "board_code": board_code,
        "note": note,
    }
    res = supabase.table("pcb_main_images").insert(data).execute()
    row = res.data[0]
    return row["id"]


def insert_defect_crop(
    main_image_id: str,
    crop_storage_path: str,
    crop_public_url: str,
    crop_width: int,
    crop_height: int,
    prediction: str,
    confidence: float,
    bbox: dict | None = None,
):
    """
    Insert row ลง pcb_defect_crops
    bbox: dict เช่น {"x": 100, "y": 120, "w": 50, "h": 40} หรือ None
    """
    data = {
        "main_image_id": main_image_id,
        "crop_storage_path": crop_storage_path,
        "crop_public_url": crop_public_url,
        "crop_width": crop_width,
        "crop_height": crop_height,
        "prediction": prediction,
        "confidence": confidence,
    }

    if bbox:
        data["bbox_x"] = bbox.get("x")
        data["bbox_y"] = bbox.get("y")
        data["bbox_width"] = bbox.get("w")
        data["bbox_height"] = bbox.get("h")

    res = supabase.table("pcb_defect_crops").insert(data).execute()
    return res.data[0]


def save_detection_from_agent_bytes_and_get_urls(
    main_image: Dict[str, Any],
    crops: List[Dict[str, Any]],
    board_code: str | None = None,
    note: str | None = None,
):
    """
    ใช้ในกรณีที่ agent มีรูปหลัก + crop อยู่แล้ว (เป็น bytes + meta)
    main_image: {
        "bytes": ...,
        "width": int,
        "height": int,
        "original_filename": str | None,
    }
    crops: [
        {
            "bytes": ...,
            "width": int,
            "height": int,
            "prediction": str,
            "confidence": float,
            "bbox": {"x": int, "y": int, "w": int, "h": int}  # optional
        },
        ...
    ]
    """
    # 1) upload main image
    main_storage_path, main_public_url = upload_to_storage(
        main_image["bytes"],
        folder="pcb/main",
        ext="png",
    )

    # 2) insert main image row
    main_image_id = insert_main_image(
        storage_path=main_storage_path,
        public_url=main_public_url,
        width=int(main_image["width"]),
        height=int(main_image["height"]),
        original_filename=main_image.get("original_filename"),
        board_code=board_code,
        note=note,
    )

    main_payload = {
        "id": main_image_id,
        "storage_path": main_storage_path,
        "public_url": main_public_url,
        "width": int(main_image["width"]),
        "height": int(main_image["height"]),
        "original_filename": main_image.get("original_filename"),
        "board_code": board_code,
        "note": note,
    }

    # 3) upload crops + insert defects
    crops_payload: List[Dict[str, Any]] = []

    for crop in crops:
        crop_storage_path, crop_public_url = upload_to_storage(
            crop["bytes"],
            folder="pcb/crops",
            ext="png",
        )

        bbox = crop.get("bbox")

        defect_row = insert_defect_crop(
            main_image_id=main_image_id,
            crop_storage_path=crop_storage_path,
            crop_public_url=crop_public_url,
            crop_width=int(crop["width"]),
            crop_height=int(crop["height"]),
            prediction=str(crop["prediction"]),
            confidence=float(crop["confidence"]),
            bbox=bbox,
        )

        crops_payload.append(
            {
                "id": defect_row["id"],
                "crop_storage_path": crop_storage_path,
                "crop_public_url": crop_public_url,
                "width": int(crop["width"]),
                "height": int(crop["height"]),
                "prediction": str(crop["prediction"]),
                "confidence": float(crop["confidence"]),
                "bbox": bbox,
            }
        )

    return {
        "main_image": main_payload,
        "crops": crops_payload,
    }
