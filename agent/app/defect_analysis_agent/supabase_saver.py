# supabase_saver.py
from io import BytesIO
from typing import List, Dict, Any, Optional

from PIL import Image
from defect_analysis_agent.pcb_db import save_detection_from_agent_bytes_and_get_urls


def save_via_supabase_from_agent(
    annotated_img: Image.Image,
    crops_data: List[Dict[str, Any]],
    original_filename: Optional[str] = None,
    board_code: Optional[str] = None,
    note: Optional[str] = None,
):
    """
    ใช้ใน defect-analysis-agent:
    - annotated_img: รูป detect หลัก (PIL Image)
    - crops_data: list ของ dict:
        {
          "image": PIL.Image,
          "prediction": str,
          "confidence": float,
          "bbox": {"x": int, "y": int, "w": int, "h": int}  # optional
        }
    """
    # main image → bytes
    main_buf = BytesIO()
    annotated_img.save(main_buf, format="PNG")
    main_buf.seek(0)
    main_bytes = main_buf.getvalue()

    main_image = {
        "bytes": main_bytes,
        "width": annotated_img.width,
        "height": annotated_img.height,
        "original_filename": original_filename,
    }

    # crops → bytes
    crops_payload: List[Dict[str, Any]] = []
    for c in crops_data:
        img = c["image"]  # PIL.Image
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        crop_bytes = buf.getvalue()

        crops_payload.append(
            {
                "bytes": crop_bytes,
                "width": img.width,
                "height": img.height,
                "prediction": c["prediction"],
                "confidence": c["confidence"],
                "bbox": c.get("bbox"),
            }
        )

    # เรียกฟังก์ชันใน pcb_db.py ที่เธอเตรียมไว้แล้ว
    return save_detection_from_agent_bytes_and_get_urls(
        main_image=main_image,
        crops=crops_payload,
        board_code=board_code,
        note=note,
    )
