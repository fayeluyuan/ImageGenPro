import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict


@dataclass
class AppConfig:
    """应用程序配置"""
    # 程序配置
    api_key: str = ""
    model: str = "gemini-3-pro-image-preview"
    save_conversation: bool = False
    conversation_path: str = ""

    # 生成参数
    aspect_ratio: str = "16:9"
    quality: str = "4k"
    filename: str = ""
    save_path: str = ""
    api_url: str = "https://lnapi.com/v1beta/models/gemini-3-pro-image-preview:generateContent"

    # 提示词
    prompt: str = ""

    # 强制使用 Gemini（你的令牌不支持 dall-e）
    force_gemini: bool = True

    # 窗口状态
    window_width: int = 1200
    window_height: int = 800


class ConfigManager:
    """配置管理器"""

    def __init__(self):
        self.config_dir = Path.home() / ".imagegenpro"
        self.config_file = self.config_dir / "config.json"
        self.template_file = self.config_dir / "templates.json"
        self.ensure_config_dir()

    def ensure_config_dir(self):
        """确保配置目录存在"""
        self.config_dir.mkdir(exist_ok=True)

    def save_config(self, config: AppConfig):
        """保存配置到文件"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(config), f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存配置失败: {e}")

    def load_config(self) -> AppConfig:
        """从文件加载配置"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return AppConfig(**data)
        except Exception as e:
            print(f"加载配置失败: {e}")
        return AppConfig()

    def save_templates(self, templates: Dict[str, str]):
        """保存模板到文件"""
        try:
            with open(self.template_file, 'w', encoding='utf-8') as f:
                json.dump(templates, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存模板失败: {e}")

    def load_templates(self) -> Dict[str, str]:
        """从文件加载模板"""
        try:
            if self.template_file.exists():
                with open(self.template_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"加载模板失败: {e}")
        return {}


# 全局配置管理器实例
config_manager = ConfigManager()
