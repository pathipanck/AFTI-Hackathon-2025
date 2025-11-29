# app/main.py
import os
import glob
import shutil

from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel

# ดึง agent จากไฟล์เดิม
from PCB_supervisor_agent import agent

app = FastAPI(
    title="PCB Supervisor Agent API",
    version="1.0.0",
)

# --------- Pydantic models ---------
class TextRequest(BaseModel):
    text: str

class TextResponse(BaseModel):
    reply: str

class ImageResponse(BaseModel):
    reply: str
    input_image: str
    processed_images: list[str]


# --------- Helper: ดึงข้อความสุดท้ายของ assistant ---------
def extract_last_assistant_text(messages) -> str:
    """
    รองรับทั้ง:
    - list ของ dict: [{"role": "...", "content": ...}, ...]
    - list ของ LangChain messages: AIMessage, HumanMessage, ...
    """
    last_content = None

    for m in reversed(messages):
        # --- ดึง role / type ---
        if isinstance(m, dict):
            role = m.get("role")
            content = m.get("content", "")
        else:
            # LangChain BaseMessage (AIMessage, HumanMessage, SystemMessage, ToolMessage ฯลฯ)
            role = getattr(m, "type", None)      # ปกติจะเป็น "ai", "human", "system", "tool"
            content = getattr(m, "content", "")

        # มองว่า "assistant" หรือ "ai" คือฝั่งตอบ
        if role in ("assistant", "ai"):
            last_content = content
            break

    if last_content is None:
        return ""

    content = last_content

    # --- แปลง content เป็น string ---
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts = []
        for part in content:
            # กรณี content แบบ structured (เช่น [{"type": "text", "text": "..."}])
            if isinstance(part, dict) and "text" in part:
                parts.append(part["text"])
            else:
                parts.append(str(part))
        return "\n".join(parts)

    return str(content)


# --------- Health check ---------
@app.get("/")
def root():
    return {"status": "ok", "message": "PCB Supervisor Agent API is running"}


# --------- Text endpoint ---------
@app.post("/chat", response_model=TextResponse)
async def chat(req: TextRequest):
    """
    ใช้คุยกับ Supervisor ด้วยข้อความธรรมดา
    """
    try:
        result = agent.invoke({
            "messages": [
                {"role": "user", "content": req.text}
            ]
        })
        reply_text = extract_last_assistant_text(result["messages"])
        return {"reply": reply_text}
    except Exception as e:
        # โยน error ออกไปให้ client เห็น
        raise HTTPException(status_code=500, detail=str(e))


# --------- Image endpoint ---------
@app.post("/analyze-image", response_model=ImageResponse)
async def analyze_image(file: UploadFile = File(...)):
    """
    อัพโหลดรูป PCB ให้ agent วิเคราะห์
    """
    # โฟลเดอร์ input image
    data_dir = os.path.join("defect_analysis_agent", "data")
    os.makedirs(data_dir, exist_ok=True)

    input_path = os.path.join(data_dir, file.filename)

    try:
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cannot save uploaded file: {e}")

    # สร้างข้อความให้ supervisor เหมือนที่ CLI ใช้
    user_input = f"Analyze the PCB image located at: {input_path}"

    try:
        result = agent.invoke({
            "messages": [
                {"role": "user", "content": user_input}
            ]
        })
        reply_text = extract_last_assistant_text(result["messages"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # หาไฟล์ processed images
    processed_dirs = [
        os.path.join("defect_analysis_agent", "processed_images"),
        "processed_images",
    ]
    processed_files: list[str] = []

    for d in processed_dirs:
        if os.path.exists(d):
            processed_files.extend(
                sorted(
                    glob.glob(os.path.join(d, "*.jpg"))
                    + glob.glob(os.path.join(d, "*.png"))
                )
            )

    return {
        "reply": reply_text,
        "input_image": input_path,
        "processed_images": processed_files,
    }
