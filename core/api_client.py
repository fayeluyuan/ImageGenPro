import requests
import json
import time
import base64
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from pathlib import Path
from PIL import Image
import io


@dataclass
class GenerationResult:
    """生成结果"""
    success: bool
    image_data: Optional[bytes] = None
    image_url: Optional[str] = None
    error_message: Optional[str] = None
    task_id: Optional[str] = None


class ImageGenerationClient:
    """图像生成API客户端"""

    def __init__(self, api_url: str, api_key: str, model: str = ""):
        self.api_url = api_url
        self.api_key = api_key
        self.model = model
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        })

    def _prepare_image_base64(self, image_path: str) -> str:
        """将图片转为base64"""
        if not Path(image_path).exists():
            raise FileNotFoundError(f"参考图文件不存在: {image_path}")
        with open(image_path, "rb") as f:
            return base64.b64encode(f.read()).decode('utf-8')

    def _get_image_mime_type(self, image_path: str) -> str:
        """根据文件扩展名获取图片MIME类型"""
        if not Path(image_path).exists():
            raise FileNotFoundError(f"参考图文件不存在: {image_path}")
        ext = Path(image_path).suffix.lower()
        mime_types = {
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.webp': 'image/webp',
            '.gif': 'image/gif',
            '.bmp': 'image/bmp'
        }
        return mime_types.get(ext, 'image/png')

    def _detect_api_type(self) -> str:
        """检测API类型"""
        # 烈鸟API的Gemini原生端点
        if "generateContent" in self.api_url or "/v1beta/models/" in self.api_url:
            return "gemini"
        # 烈鸟API的OpenAI兼容端点
        elif "/v1/images/generations" in self.api_url:
            return "openai"
        elif "task" in self.api_url.lower() or "job" in self.api_url.lower():
            return "polling"
        else:
            return "direct"

    def generate_openai_format(
        self,
        prompt: str,
        size: str = "1024x1024",
        reference_images: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """OpenAI格式API调用 - 支持烈鸟API的任意模型"""
        if reference_images and len(reference_images) > 0:
            return self._generate_image_edit(prompt, reference_images[0], size, progress_callback)

        try:
            if progress_callback:
                progress_callback("正在准备请求...")

            payload = {
                "model": self.model or "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "response_format": "b64_json"
            }

            # 注：烈鸟API统一使用 OpenAI 兼容格式，包括 Gemini 模型
            # 不需要为 Gemini 做特殊处理

            if progress_callback:
                progress_callback("正在发送请求...")

            response = self.session.post(self.api_url, json=payload, timeout=60)

            # 处理错误响应
            if response.status_code != 200:
                raw_body = response.text[:500]
                print(f"[API RAW {response.status_code}] body={raw_body!r}")
                error_msg = f"HTTP错误 {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"]
                        if isinstance(error_detail, dict):
                            error_msg += f": {error_detail.get('message', str(error_detail))}"
                        else:
                            error_msg += f": {str(error_detail)}"
                    elif "message" in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {raw_body}"

                if response.status_code == 401:
                    error_msg += "\n\n授权失败，请检查API Key是否正确或已过期"
                elif response.status_code == 503:
                    error_msg += "\n\n服务不可用，可能原因：\n"
                    error_msg += f"1. 当前分组不支持模型: {self.model}\n"
                    error_msg += "2. 该模型暂时无可用渠道\n"
                    error_msg += "3. 请检查烈鸟API官网状态或联系客服"

                return GenerationResult(success=False, error_message=error_msg)

            response.raise_for_status()

            data = response.json()

            if progress_callback:
                progress_callback("正在处理响应...")

            # 尝试提取图片数据
            image_data, image_url, error = self._extract_image_from_json(data)

            if image_data:
                return GenerationResult(success=True, image_data=image_data)
            elif image_url:
                return GenerationResult(success=True, image_url=image_url)
            elif error:
                return GenerationResult(success=False, error_message=error)

            return GenerationResult(success=False, error_message="API返回格式异常，无法提取图片数据")

        except requests.exceptions.RequestException as e:
            return GenerationResult(success=False, error_message=f"网络请求错误: {str(e)}")
        except Exception as e:
            return GenerationResult(success=False, error_message=f"生成失败: {str(e)}")

    def _generate_image_edit(
        self,
        prompt: str,
        image_path: str,
        size: str = "1024x1024",
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """OpenAI图像编辑API调用（使用参考图）"""
        try:
            if progress_callback:
                progress_callback("正在准备图像编辑请求...")

            edit_url = self.api_url.replace("/v1/images/generations", "/v1/images/edits")
            if edit_url == self.api_url:
                edit_url = self.api_url.rsplit("/", 1)[0] + "/edits"

            data = {
                "model": self.model or "dall-e-2",
                "prompt": prompt,
                "n": 1,
                "size": size,
                "response_format": "b64_json"
            }

            if progress_callback:
                progress_callback("正在上传参考图...")

            with open(image_path, "rb") as image_file:
                files = {
                    "image": (Path(image_path).name, image_file, f"image/{Path(image_path).suffix[1:]}")
                }

                headers = {"Authorization": f"Bearer {self.api_key}"}

                response = requests.post(
                    edit_url,
                    data=data,
                    files=files,
                    headers=headers,
                    timeout=120
                )

            if response.status_code != 200:
                error_msg = f"HTTP错误 {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"]
                        if isinstance(error_detail, dict):
                            error_msg += f": {error_detail.get('message', str(error_detail))}"
                        else:
                            error_msg += f": {str(error_detail)}"
                    elif "message" in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {response.text[:200]}"

                if response.status_code == 404:
                    error_msg += "\n\n该API可能不支持图像编辑功能。请：\n"
                    error_msg += "1. 检查是否使用了支持图像编辑的模型（如 dall-e-2）\n"
                    error_msg += "2. 移除参考图，直接使用文字生成\n"
                    error_msg += "3. 联系API提供商确认支持的端点"

                return GenerationResult(success=False, error_message=error_msg)

            response.raise_for_status()

            data = response.json()

            if progress_callback:
                progress_callback("正在处理响应...")

            if "data" in data and len(data["data"]) > 0:
                image_b64 = data["data"][0].get("b64_json")
                if image_b64:
                    image_data = base64.b64decode(image_b64)
                    return GenerationResult(success=True, image_data=image_data)

                image_url = data["data"][0].get("url")
                if image_url:
                    return GenerationResult(success=True, image_url=image_url)

            return GenerationResult(success=False, error_message="API返回格式异常")

        except requests.exceptions.RequestException as e:
            return GenerationResult(success=False, error_message=f"网络请求错误: {str(e)}")
        except Exception as e:
            return GenerationResult(success=False, error_message=f"图像编辑失败: {str(e)}")

    def generate_gemini_format(
        self,
        prompt: str,
        aspect_ratio: str = "1:1",
        quality: str = "2k",
        reference_images: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """Gemini原生格式API调用 - 适配烈鸟API的Google API兼容端点

        使用端点: https://lnapi.com/v1beta/models/{model}:generateContent
        """
        try:
            if progress_callback:
                progress_callback("正在准备请求...")

            # 构建Google API格式的请求体
            # 参考: https://ai.google.dev/api/generate-content

            # 将提示词与参考图合并到一个user消息中
            # Gemini多模态API要求所有图片和文本在同一个content中
            parts = []

            # 如果有参考图，先添加参考图说明和所有参考图
            if reference_images and len(reference_images) > 0:
                parts.append({"text": "请参考以下图片:"})
                for img_path in reference_images[:3]:
                    image_b64 = self._prepare_image_base64(img_path)
                    # 检测实际MIME类型
                    mime_type = self._get_image_mime_type(img_path)
                    parts.append({
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": image_b64
                        }
                    })

            # 添加主要提示词（包含宽高比要求）
            size = get_size_from_ratio(aspect_ratio, quality, self.model)
            enhanced_prompt = f"{prompt}\n\n请生成一张图片，尺寸要求: {size} ({aspect_ratio})"
            parts.append({"text": enhanced_prompt})

            contents = [{
                "role": "user",
                "parts": parts
            }]

            # 构建请求体
            # Gemini API 通过 aspectRatio 参数控制画幅比例
            # 支持的比例: 1:1, 3:4, 4:3, 9:16, 16:9
            payload = {
                "contents": contents,
                "generation_config": {
                    "response_modalities": ["TEXT", "IMAGE"],
                    "aspectRatio": aspect_ratio  # Gemini原生比例参数
                }
            }

            # 构建正确的端点URL
            # 格式: https://lnapi.com/v1beta/models/{model}:generateContent
            model_name = self.model or "gemini-3-pro-image-preview"
            # 移除可能的前缀
            if model_name.startswith("models/"):
                model_name = model_name[7:]

            base_url = self.api_url.rsplit("/v1", 1)[0] if "/v1" in self.api_url else "https://lnapi.com"
            gemini_url = f"{base_url}/v1beta/models/{model_name}:generateContent"

            if progress_callback:
                progress_callback("正在发送请求...")

            # 保留 Authorization 请求头（烈鸟 API 使用 Bearer Token 鉴权）
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            }

            response = self.session.post(gemini_url, json=payload, headers=headers, timeout=120)

            # 处理错误响应
            if response.status_code != 200:
                error_msg = f"HTTP错误 {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_detail = error_data["error"]
                        if isinstance(error_detail, dict):
                            error_msg += f": {error_detail.get('message', str(error_detail))}"
                        else:
                            error_msg += f": {str(error_detail)}"
                    elif "message" in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {response.text[:200]}"

                if response.status_code == 401:
                    error_msg += "\n\n授权失败，请检查API Key是否正确或已过期"
                elif response.status_code == 503:
                    error_msg += "\n\n服务不可用，可能原因：\n"
                    error_msg += "1. 当前分组不支持该模型\n"
                    error_msg += "2. 模型调用量激增，请稍后重试\n"
                    error_msg += "3. 请联系API提供商确认分组设置"

                return GenerationResult(success=False, error_message=error_msg)

            data = response.json()

            if progress_callback:
                progress_callback("正在处理响应...")

            # 解析Google API响应格式
            # 图片通常在 candidates[0].content.parts 中，作为 inlineData
            candidates = data.get("candidates", [])
            if not candidates:
                return GenerationResult(success=False, error_message="API返回无候选结果")

            content = candidates[0].get("content", {})
            parts = content.get("parts", [])

            for part in parts:
                # 检查是否有内联图片数据
                if "inlineData" in part:
                    inline_data = part["inlineData"]
                    mime_type = inline_data.get("mimeType", "image/png")
                    image_b64 = inline_data.get("data", "")
                    if image_b64:
                        image_data = base64.b64decode(image_b64)
                        return GenerationResult(success=True, image_data=image_data)

                # 或者图片URL
                if "fileData" in part:
                    file_data = part["fileData"]
                    image_url = file_data.get("fileUri", "")
                    if image_url:
                        return GenerationResult(success=True, image_url=image_url)

            # 如果没有找到图片，尝试通用提取
            image_data, image_url, error = self._extract_image_from_json(data)

            if image_data:
                return GenerationResult(success=True, image_data=image_data)
            elif image_url:
                return GenerationResult(success=True, image_url=image_url)
            elif error:
                return GenerationResult(success=False, error_message=error)

            # 检查是否有文本响应（可能是错误信息）
            text_parts = []
            for part in parts:
                if "text" in part:
                    text_parts.append(part["text"])

            if text_parts:
                return GenerationResult(success=False, error_message=f"API返回文本而非图片: {' '.join(text_parts)[:200]}")

            return GenerationResult(success=False, error_message="API返回格式异常，无法提取图片数据")

        except requests.exceptions.RequestException as e:
            return GenerationResult(success=False, error_message=f"网络请求错误: {str(e)}")
        except Exception as e:
            return GenerationResult(success=False, error_message=f"生成失败: {str(e)}")

    def generate_with_polling(
        self,
        prompt: str,
        size: str = "1024x1024",
        reference_images: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """任务提交+轮询格式API调用"""
        try:
            if progress_callback:
                progress_callback("正在提交任务...")

            payload = {
                "model": self.model,
                "prompt": prompt,
                "size": size,
            }

            if reference_images and len(reference_images) > 0:
                images_b64 = [self._prepare_image_base64(img) for img in reference_images]
                payload["reference_images"] = images_b64

            response = self.session.post(self.api_url, json=payload, timeout=30)
            response.raise_for_status()

            data = response.json()
            task_id = data.get("task_id") or data.get("id")

            if not task_id:
                return GenerationResult(success=False, error_message="未获取到任务ID")

            if progress_callback:
                progress_callback(f"任务已提交，ID: {task_id}")

            base_url = self.api_url.rsplit('/', 1)[0]
            query_url = f"{base_url}/tasks/{task_id}"

            max_retries = 60
            for i in range(max_retries):
                if progress_callback:
                    progress_callback(f"正在生成... ({i+1}/{max_retries})")

                time.sleep(2)

                query_response = self.session.get(query_url, timeout=10)
                query_data = query_response.json()

                status = query_data.get("status", "unknown")

                if status == "completed":
                    image_url = query_data.get("image_url") or query_data.get("output", {}).get("image_url")
                    image_b64 = query_data.get("image_b64") or query_data.get("output", {}).get("image_b64")

                    if image_b64:
                        image_data = base64.b64decode(image_b64)
                        return GenerationResult(success=True, image_data=image_data, task_id=task_id)
                    elif image_url:
                        return GenerationResult(success=True, image_url=image_url, task_id=task_id)
                    else:
                        return GenerationResult(success=False, error_message="未获取到图片数据")

                elif status in ["failed", "error"]:
                    error_msg = query_data.get("error", "任务执行失败")
                    return GenerationResult(success=False, error_message=error_msg)

            return GenerationResult(success=False, error_message="轮询超时")

        except requests.exceptions.RequestException as e:
            return GenerationResult(success=False, error_message=f"网络请求错误: {str(e)}")
        except Exception as e:
            return GenerationResult(success=False, error_message=f"生成失败: {str(e)}")

    def generate_direct(
        self,
        prompt: str,
        size: str = "1024x1024",
        reference_images: Optional[List[str]] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """直接返回图片格式API调用"""
        try:
            if progress_callback:
                progress_callback("正在发送请求...")

            data = {
                "prompt": prompt,
                "model": self.model,
                "size": size,
            }

            files = []
            temp_files = []
            if reference_images and len(reference_images) > 0:
                for img_path in reference_images[:3]:
                    f = open(img_path, "rb")
                    files.append(("reference_images", f))
                    temp_files.append(f)

            if progress_callback:
                progress_callback("正在上传数据...")

            try:
                if files:
                    headers = {"Authorization": f"Bearer {self.api_key}"}
                    response = requests.post(
                        self.api_url,
                        data=data,
                        files=files,
                        headers=headers,
                        timeout=120
                    )
                else:
                    headers = self.session.headers.copy()
                    response = requests.post(
                        self.api_url,
                        json=data,
                        headers=headers,
                        timeout=120
                    )
            finally:
                for f in temp_files:
                    f.close()

            if response.status_code != 200:
                error_msg = f"HTTP错误 {response.status_code}"
                try:
                    error_data = response.json()
                    if "error" in error_data:
                        error_msg += f": {error_data['error']}"
                    elif "message" in error_data:
                        error_msg += f": {error_data['message']}"
                except:
                    error_msg += f": {response.text[:200]}"
                return GenerationResult(success=False, error_message=error_msg)

            response.raise_for_status()

            if progress_callback:
                progress_callback("正在处理响应...")

            content_type = response.headers.get("Content-Type", "").lower()

            if "image" in content_type and "json" not in content_type:
                return GenerationResult(success=True, image_data=response.content)

            if "json" in content_type or response.text.strip().startswith(("{", "[")):
                try:
                    data = response.json()
                except json.JSONDecodeError:
                    try:
                        image_data = base64.b64decode(response.text.strip())
                        return GenerationResult(success=True, image_data=image_data)
                    except:
                        pass
                    return GenerationResult(success=False, error_message="无法解析JSON响应")

                image_data, image_url, error = self._extract_image_from_json(data)

                if image_data:
                    return GenerationResult(success=True, image_data=image_data)
                elif image_url:
                    return GenerationResult(success=True, image_url=image_url)
                elif error:
                    return GenerationResult(success=False, error_message=error)

            text = response.text.strip()
            if len(text) > 100 and not text.startswith("http"):
                try:
                    image_data = base64.b64decode(text)
                    return GenerationResult(success=True, image_data=image_data)
                except:
                    pass

            if text.startswith("http"):
                return GenerationResult(success=True, image_url=text)

            if "html" in content_type:
                html_content = response.text

                if "接口聚合" in html_content or "openai" in html_content.lower() or "聚合管理" in html_content:
                    return GenerationResult(
                        success=False,
                        error_message="""检测到API聚合管理平台首页，请检查API网址配置。

可能的问题：
1. API网址缺少具体的端点路径，例如：
   - https://api.bianxie.ai/v1/images/generations
   - https://api.bianxie.ai/v1/chat/completions

2. 需要查阅该平台的API文档获取正确的图像生成端点

请确认正确的API端点地址后再试。"""
                    )

                try:
                    debug_dir = Path.home() / ".imagegenpro" / "debug"
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    debug_file = debug_dir / f"response_{int(time.time())}.html"
                    with open(debug_file, "w", encoding="utf-8") as f:
                        f.write(html_content)
                except:
                    pass

                import re
                title_match = re.search(r"<title>(.*?)</title>", html_content, re.IGNORECASE | re.DOTALL)
                h1_match = re.search(r"<h1[^>]*>(.*?)</h1>", html_content, re.IGNORECASE | re.DOTALL)

                error_detail = ""
                if title_match:
                    error_detail = f" 页面标题: {title_match.group(1).strip()[:100]}"
                elif h1_match:
                    error_detail = f" 页面提示: {h1_match.group(1).strip()[:100]}"

                if "unauthorized" in html_content.lower() or "auth" in html_content.lower() or "login" in html_content.lower():
                    return GenerationResult(success=False, error_message=f"API认证失败，请检查授权码是否正确。{error_detail}")

                if response.status_code == 404 or "not found" in html_content.lower():
                    return GenerationResult(success=False, error_message=f"API端点不存在(404)，请检查API网址是否正确。{error_detail}")

                return GenerationResult(success=False, error_message=f"API返回HTML页面而非图片数据，可能是端点错误或服务器问题。{error_detail}\n原始响应前500字符: {html_content[:500]}")

            return GenerationResult(success=False, error_message=f"无法解析响应数据，Content-Type: {content_type}\n原始响应前500字符: {response.text[:500]}")

        except requests.exceptions.RequestException as e:
            return GenerationResult(success=False, error_message=f"网络请求错误: {str(e)}")
        except Exception as e:
            return GenerationResult(success=False, error_message=f"生成失败: {str(e)}")

    def _extract_image_from_json(self, data: dict) -> tuple:
        """从JSON数据中递归提取图片信息"""
        b64_fields = ["b64_json", "image_b64", "image_base64", "base64", "imageData", "data"]
        for field in b64_fields:
            if field in data and data[field]:
                try:
                    return (base64.b64decode(data[field]), None, None)
                except:
                    pass

        url_fields = ["url", "image_url", "imageUrl", "image", "link", "download_url"]
        for field in url_fields:
            if field in data and data[field]:
                if isinstance(data[field], str) and (data[field].startswith("http") or data[field].startswith("data:image")):
                    if data[field].startswith("data:image"):
                        try:
                            base64_data = data[field].split(",")[1]
                            return (base64.b64decode(base64_data), None, None)
                        except:
                            pass
                    else:
                        return (None, data[field], None)

        nested_paths = [
            ["data", "image"],
            ["data", "url"],
            ["data", "image_url"],
            ["output", "image"],
            ["output", "url"],
            ["output", "image_url"],
            ["result", "image"],
            ["result", "url"],
            ["data", 0, "url"],
            ["data", 0, "b64_json"],
        ]

        for path in nested_paths:
            current = data
            try:
                for key in path:
                    current = current[key]
                if isinstance(current, str):
                    if current.startswith("http"):
                        return (None, current, None)
                    elif len(current) > 100:
                        try:
                            return (base64.b64decode(current), None, None)
                        except:
                            pass
            except (KeyError, TypeError, IndexError):
                continue

        def recursive_search(obj, depth=0):
            if depth > 5:
                return None, None
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if isinstance(v, str):
                        if v.startswith("http") and ("image" in k.lower() or "url" in k.lower()):
                            return None, v
                        elif len(v) > 200 and not v.startswith("http"):
                            try:
                                return base64.b64decode(v), None
                            except:
                                pass
                    elif isinstance(v, (dict, list)):
                        img_data, img_url = recursive_search(v, depth + 1)
                        if img_data or img_url:
                            return img_data, img_url
            elif isinstance(obj, list) and len(obj) > 0:
                for item in obj:
                    img_data, img_url = recursive_search(item, depth + 1)
                    if img_data or img_url:
                        return img_data, img_url
            return None, None

        img_data, img_url = recursive_search(data)
        if img_data or img_url:
            return (img_data, img_url, None)

        return (None, None, f"无法解析响应数据: {json.dumps(data, ensure_ascii=False, indent=2)[:200]}")

    def download_image(self, url: str) -> Optional[bytes]:
        """下载图片"""
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.content
        except Exception:
            return None

    def generate(
        self,
        prompt: str,
        size: str = "1024x1024",
        aspect_ratio: str = "1:1",
        quality: str = "2k",
        reference_images: Optional[List[str]] = None,
        api_type: Optional[str] = None,
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> GenerationResult:
        """主生成方法"""
        if not api_type or api_type == "auto":
            api_type = self._detect_api_type()

        if api_type == "gemini":
            result = self.generate_gemini_format(prompt, aspect_ratio, quality, reference_images, progress_callback)
        elif api_type == "openai":
            result = self.generate_openai_format(prompt, size, reference_images, progress_callback)
        elif api_type == "polling":
            result = self.generate_with_polling(prompt, size, reference_images, progress_callback)
        else:
            result = self.generate_direct(prompt, size, reference_images, progress_callback)

        if result.success and result.image_url and not result.image_data:
            if progress_callback:
                progress_callback("正在下载图片...")
            image_data = self.download_image(result.image_url)
            if image_data:
                result.image_data = image_data
            else:
                result.error_message = "图片下载失败"
                result.success = False

        return result


def get_size_from_ratio(aspect_ratio: str, quality: str, model: str = "") -> str:
    """根据画框比例和画质返回尺寸

    DALL-E 3 只支持固定尺寸: 1024x1024, 1792x1024, 1024x1792
    Gemini 模型在烈鸟API上使用 OpenAI 兼容格式，也使用这些尺寸
    """
    # DALL-E 3 和 Gemini 都使用标准 OpenAI 尺寸
    if "dall-e-3" in model.lower() or "gemini" in model.lower():
        ratio_map = {
            "16:9": "1792x1024",
            "21:9": "1792x1024",
            "3:2": "1792x1024",
            "1:1": "1024x1024",
            "9:16": "1024x1792",
            "4:3": "1024x1024",  # 4:3 接近 1:1
            "3:4": "1024x1792",  # 接近 9:16
            "2:3": "1024x1792"
        }
        return ratio_map.get(aspect_ratio, "1024x1024")

    # DALL-E 2 只支持 256x256, 512x512, 1024x1024
    if "dall-e-2" in model.lower():
        return "1024x1024"

    # 其他模型使用动态尺寸
    size_map = {
        "1k": 1024,
        "2k": 1536,
        "4k": 2048
    }

    base_size = size_map.get(quality.lower(), 1024)

    ratio_map = {
        "16:9": (16, 9),
        "1:1": (1, 1),
        "9:16": (9, 16),
        "4:3": (4, 3),
        "3:4": (3, 4),
        "21:9": (21, 9),
        "2:3": (2, 3),
        "3:2": (3, 2)
    }

    w_ratio, h_ratio = ratio_map.get(aspect_ratio, (1, 1))

    if w_ratio >= h_ratio:
        width = base_size
        height = int(base_size * h_ratio / w_ratio)
    else:
        height = base_size
        width = int(base_size * w_ratio / h_ratio)

    width = (width // 8) * 8
    height = (height // 8) * 8

    return f"{width}x{height}"
