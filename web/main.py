from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import os
import sys
import time

# 将项目根目录加入路径，以便导入 core/api_client.py
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.api_client import ImageGenerationClient, get_size_from_ratio

app = FastAPI(title="ImageGenPro Web v2")

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
                    reference_images=config.reference_images or None,
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


@app.get("/api/image")
async def get_image(path: str):
    """
    读取本地生成的图片文件，供前端预览
    """
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found")

    def iterfile():
        with open(path, "rb") as f:
            yield from f

    return StreamingResponse(iterfile(), media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
