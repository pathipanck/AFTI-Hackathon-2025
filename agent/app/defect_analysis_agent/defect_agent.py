import os
from dotenv import load_dotenv
from typing_extensions import Annotated, Literal
from langchain import tools
from langchain.tools import tool
from langchain.chat_models import init_chat_model
from langchain_google_genai import ChatGoogleGenerativeAI
from deepagents import create_deep_agent
from .prompts import DEFECT_ANALYSIS_PROMPT
from .tools import detect_pcb_defects

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

load_dotenv()

# Model Gemini 
model = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.0)

# Sub Agent
defect_analysis_agent = {
    "name": "defect-analysis-agent",
    "description": "Uses computer vision to detect physical defects on PCB images. Returns a list of defects.",
    "system_prompt": DEFECT_ANALYSIS_PROMPT,
    "tools": [detect_pcb_defects],
    "model": model,
}

# # Main agent (for test)
# agent = create_deep_agent(
#     system_prompt = DEFECT_ANALYSIS_PROMPT,
#     model = model,
#     tools = [detect_pcb_defects]
# )


# # Test 
# console = Console()

# if __name__ == "__main__":
#     # 1. ระบุตำแหน่งไฟล์รูปภาพ (ต้องมีอยู่จริง!)
#     image_path_to_test = "./data/Screenshot 2024-10-16 044651.png"

#     # ตรวจสอบก่อนว่ามีไฟล์ไหม
#     if not os.path.exists(image_path_to_test):
#         print(f"❌ Error: ไม่เจอไฟล์รูปภาพที่ {image_path_to_test}")
#         print("กรุณาสร้างโฟลเดอร์ 'data' และใส่รูป 'test_pcb.jpg' ก่อนรันครับ")
#         exit()

#     print(f"🚀 กำลังส่งรูป {image_path_to_test} ให้ Agent วิเคราะห์...\n")

#     # 2. สร้าง Prompt ที่ "ระบุ Path ชัดเจน"
#     # Agent จะอ่าน Path นี้แล้วส่งต่อให้ detect_pcb_defects(image_path=...)
#     user_input = f"Analyze the PCB image located at: {image_path_to_test}"

#     # 3. สั่งรัน Agent (Invoke)
#     try:
#         result = agent.invoke({
#             "messages": [{"role": "user", "content": user_input}]
#         })

#         # 4. แสดงผลลัพธ์
#         last_message = result["messages"][-1]
        
#         # Handle case where content might be a list (multimodal) or string
#         if isinstance(last_message.content, list):
#             # Extract text from list of content blocks
#             ai_content = "\n".join([
#                 item.get("text", str(item)) if isinstance(item, dict) else str(item)
#                 for item in last_message.content
#             ])
#         else:
#             ai_content = last_message.content
        
#         print("\n" + "="*50)
#         print("🔍 **ANALYSIS REPORT**")
#         print("="*50)
#         if console:
#             console.print(Panel(Markdown(ai_content), title="🔍 Analysis Report", border_style="green"))
#         else:
#             print(ai_content) # แบบธรรมดาถ้าไม่มี rich
#         print("="*50)
        
#         # 5. แจ้งเตือนไฟล์ output
#         if os.path.exists("processed_images"):
#             print("\n📂 เช็คผลลัพธ์รูปภาพได้ที่โฟลเดอร์: processed_images/")
#             # แสดงรายชื่อไฟล์ที่สร้างขึ้น
#             import glob
#             image_files = glob.glob("processed_images/*.jpg") + glob.glob("processed_images/*.png")
#             if image_files:
#                 print(f"   พบไฟล์รูปภาพ {len(image_files)} ไฟล์:")
#                 for img_file in sorted(image_files):
#                     print(f"   - {img_file}")

#     except Exception as e:
#         print(f"💥 เกิดข้อผิดพลาด: {e}")
#         import traceback
#         traceback.print_exc()  # แสดง full error traceback เพื่อ debug