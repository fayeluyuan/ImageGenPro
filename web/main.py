from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import mimetypes
import uvicorn
import os
import sys
import time
import re
import tempfile
import base64

# 将项目根目录加入路径，以便导入 core/api_client.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.api_client import ImageGenerationClient, get_size_from_ratio

app = FastAPI(title="ImageGenPro Web v2")

# CORS 中间件（支持局域网访问和跨域调试）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
async def root():
    return FileResponse(os.path.join(static_dir, "index.html"))


@app.get("/api/health")
async def health():
    return {"status": "ok"}


class GenerateTask(BaseModel):
    id: str
    prompt: str
    filename: str


class GenerateConfig(BaseModel):
    api_key: str
    api_url: str = "https://lnapi.com/v1beta/models/gemini-3-pro-image-preview:generateContent"
    model: str = "gemini-3-pro-image-preview"
    aspect_ratio: str = "1:1"
    quality: str = "2k"
    output_dir: str


class GenerateRequest(BaseModel):
    tasks: List[GenerateTask]
    config: GenerateConfig
    reference_images: List[str] = []


class TaskResult(BaseModel):
    id: str
    success: bool
    filename: Optional[str] = None
    error: Optional[str] = None
    skipped: bool = False


@app.post("/api/generate", response_model=List[TaskResult])
async def generate_batch(req: GenerateRequest):
    """
    批量图片生成接口
    支持断点续传和自动重试
    """
    config = req.config
    size = get_size_from_ratio(config.aspect_ratio, config.quality, config.model)

    client = ImageGenerationClient(
        api_key=config.api_key,
        api_url=config.api_url,
        model=config.model,
    )

    os.makedirs(config.output_dir, exist_ok=True)
    results: List[TaskResult] = []

    # 预处理 reference_images：将 base64 data URL 写入临时文件
    temp_files = []
    processed_reference_images = []
    for img in (req.reference_images or []):
        if isinstance(img, str) and img.startswith("data:image"):
            match = re.match(r"data:image/([^;]+);base64,(.+)", img)
            if match:
                ext = match.group(1).split("+")[0]
                b64_data = match.group(2)
                with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
                    tmp.write(base64.b64decode(b64_data))
                    temp_files.append(tmp.name)
                    processed_reference_images.append(tmp.name)
            else:
                processed_reference_images.append(img)
        else:
            processed_reference_images.append(img)

    try:
        for task in req.tasks:
            output_path = os.path.join(config.output_dir, f"{task.filename}.png")

            # 断点续传检查
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1024:
                results.append(
                    TaskResult(
                        id=task.id,
                        success=True,
                        filename=f"{task.filename}.png",
                        skipped=True,
                    )
                )
                continue

            # 自动重试机制
            success = False
            error_msg = None
            image_data = None
            max_retries = 3

            for attempt in range(1, max_retries + 1):
                try:
                    result = client.generate(
                        prompt=task.prompt,
                        size=size,
                        aspect_ratio=config.aspect_ratio,
                        quality=config.quality,
                        reference_images=processed_reference_images or None,
                    )

                    if result.success:
                        image_data = result.image_data
                        if not image_data and result.image_url:
                            image_data = client.download_image(result.image_url)

                        if image_data:
                            with open(output_path, "wb") as f:
                                f.write(image_data)
                            success = True
                            break
                        else:
                            error_msg = "无法获取图片数据"
                    else:
                        error_msg = result.error_message or "生成失败"

                except Exception as e:
                    error_msg = str(e)

                if attempt < max_retries:
                    time.sleep(2 * attempt)  # 逐次增加等待时间

            if success:
                results.append(
                    TaskResult(
                        id=task.id,
                        success=True,
                        filename=f"{task.filename}.png",
                    )
                )
            else:
                results.append(
                    TaskResult(
                        id=task.id,
                        success=False,
                        error=error_msg or "未知错误",
                    )
                )

            # 请求间隔，避免触发API限流
            if task != req.tasks[-1]:
                time.sleep(1.5)

        return results
    finally:
        for f in temp_files:
            try:
                os.remove(f)
            except Exception:
                pass


@app.get("/api/image")
async def get_image(path: str):
    """
    读取本地生成的图片文件，供前端预览
    安全校验：禁止路径遍历和非图片文件
    """
    # 路径遍历防护
    if ".." in path or "~" in path or path.startswith(("/etc", "/sys", "/proc", "/dev", "C:\\Windows", "C:\\Program")):
        raise HTTPException(status_code=400, detail="Invalid path")
    
    # 只允许常见图片格式
    ext = Path(path).suffix.lower()
    if ext not in (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"):
        raise HTTPException(status_code=400, detail="Unsupported file type")
    
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")
    
    mime_type, _ = mimetypes.guess_type(path)
    if not mime_type:
        mime_type = "image/png"
    
    def iterfile():
        with open(path, "rb") as f:
            yield from f
    
    return StreamingResponse(iterfile(), media_type=mime_type)


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
