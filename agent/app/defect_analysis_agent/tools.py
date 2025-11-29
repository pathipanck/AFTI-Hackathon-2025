import os
import io
from PIL import Image, ImageDraw, ImageFont
from inference_sdk import InferenceHTTPClient
from langchain_core.tools import tool

# --- Configuration ---
# แนะนำให้เก็บ API KEY ใน .env เพื่อความปลอดภัยครับ
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY", "DinIFQuB3og5F3IQzf6e") 
ROBOFLOW_MODEL_ID = "circuit-board-defect-detection/1"

# Setup Client
CLIENT = InferenceHTTPClient(
    api_url="https://detect.roboflow.com",
    api_key=ROBOFLOW_API_KEY
)

# --- Helper Function (Internal Use) ---
def _draw_boxes_and_crop(image: Image.Image, predictions: list, output_dir: str):
    """ฟังก์ชันช่วยวาดกรอบและ Crop รูป (ไม่ใช่ Tool หลัก แต่เป็น Helper)"""
    draw = ImageDraw.Draw(image)
    
    # พยายามโหลด Font ถ้าไม่มีให้ใช้ Default
    try:
        font = ImageFont.truetype("arial.ttf", 15)
    except IOError:
        font = ImageFont.load_default()

    cropped_pcbs_paths = []
    
    for i, detection in enumerate(predictions):
        confidence = detection['confidence']
        
        # Filter Confidence (ปรับได้ตามต้องการ)
        if confidence >= 0.3:
            x, y = detection['x'], detection['y']
            w, h = detection['width'], detection['height']
            label = detection['class']

            # คำนวณพิกัด
            left = x - w / 2
            top = y - h / 2
            right = x + w / 2
            bottom = y + h / 2

            # วาดกรอบ
            draw.rectangle([left, top, right, bottom], outline="cyan", width=3)
            draw.text((left, top - 15), f'{label} {confidence:.2%}', font=font, fill="cyan")

            # Padding & Crop
            padding_x = w * 0.2
            padding_y = h * 0.2
            
            crop_left = max(0, left - padding_x)
            crop_top = max(0, top - padding_y)
            crop_right = min(image.width, right + padding_x)
            crop_bottom = min(image.height, bottom + padding_y)

            cropped_pcb = image.crop((crop_left, crop_top, crop_right, crop_bottom))
            cropped_pcb = cropped_pcb.resize((300, 300))
            
            # Save Cropped Image
            crop_filename = f"crop_{i}_{label}.jpg"
            crop_path = os.path.join(output_dir, crop_filename)
            cropped_pcb.save(crop_path)
            cropped_pcbs_paths.append(crop_path)

    return image, cropped_pcbs_paths

# --- Main Tool ---
@tool
def detect_pcb_defects(image_path: str) -> str:
    """
    Analyzes a PCB image to detect defects using a computer vision model.
    
    Args:
        image_path: The file path to the PCB image (e.g., 'data/input_images/pcb_01.jpg').
        
    Returns:
        A text summary of detected defects, their locations, and paths to the processed images.
    """
    # 1. ตรวจสอบไฟล์
    if not os.path.exists(image_path):
        return f"Error: Image file not found at {image_path}"

    try:
        # 2. เตรียม Folder สำหรับ Output
        output_dir = "processed_images"
        os.makedirs(output_dir, exist_ok=True)

        # 3. ส่งไป Roboflow
        # infer() ของ sdk รับ path ได้เลย
        result = CLIENT.infer(image_path, model_id=ROBOFLOW_MODEL_ID)

        if 'predictions' not in result:
            return "Analysis Complete: No predictions returned from the model."

        predictions = result['predictions']
        
        if not predictions:
            return "Analysis Complete: No defects detected in this image."

        # 4. วาดรูปและ Crop (Visualization)
        original_image = Image.open(image_path).convert("RGB")
        annotated_image, crop_paths = _draw_boxes_and_crop(original_image, predictions, output_dir)
        
        # Save Annotated Image
        annotated_path = os.path.join(output_dir, "detected_" + os.path.basename(image_path))
        annotated_image.save(annotated_path)

        # 5. สร้างข้อความสรุปส่งกลับให้ Agent (สำคัญมาก! Agent อ่านรูปไม่ได้ ต้องอ่าน Text)
        summary = f"✅ Analysis Complete for {image_path}.\n\n"
        summary += f"📊 **Total Defects Found: {len(predictions)}**\n\n"
        
        # แสดงรายละเอียดแต่ละจุดอย่างชัดเจน
        summary += "**Detailed Defect List:**\n"
        for i, p in enumerate(predictions):
            confidence_pct = p['confidence'] * 100
            summary += f"\n**Defect #{i+1}:**\n"
            summary += f"  - Type: {p['class']}\n"
            summary += f"  - Confidence: {confidence_pct:.2f}%\n"
            summary += f"  - Location: X={p['x']:.1f}, Y={p['y']:.1f}\n"
            summary += f"  - Size: Width={p['width']:.1f}, Height={p['height']:.1f}\n"
            if i < len(crop_paths):
                summary += f"  - Cropped Image: {crop_paths[i]}\n"
        
        summary += f"\n\n📂 **Visual Evidence Saved:**\n"
        summary += f"- Annotated Full Image: {annotated_path}\n"
        summary += f"- Total Cropped Images: {len(crop_paths)}\n"
        for i, crop_path in enumerate(crop_paths):
            summary += f"  - Crop #{i+1}: {crop_path}\n"

        return summary

    except Exception as e:
        return f"Error during defect detection: {str(e)}"