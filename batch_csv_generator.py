#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImageGenPro CSV批量生成器 - 稳定版
支持: 断点续传、自动重试、无需GUI

用法:
    1. 在同目录创建 prompts.csv，格式如下:
       product_name,prompt,angle1,angle2,angle3,angle4
       包包1,"白色手提包，简约设计","正面","侧面","俯视","细节"
       包包2,"黑色双肩包，商务风格","正面","侧面","俯视","细节"

    2. 运行: python batch_csv_generator.py -i prompts.csv -o E:\\output

    3. 如果中断，再次运行会自动跳过已生成的图片
"""

import sys
import os
import csv
import time
import json
import argparse
from datetime import datetime
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.api_client import ImageGenerationClient, get_size_from_ratio

# ==================== 配置 ====================
DEFAULT_API_URL = "https://lnapi.com/v1beta/models/gemini-3-pro-image-preview:generateContent"
DEFAULT_MODEL = "gemini-3-pro-image-preview"
DEFAULT_RATIO = "1:1"
DEFAULT_QUALITY = "2k"
MAX_RETRIES = 3           # 单张图片最大重试次数
RETRY_DELAY = 10          # 重试间隔（秒）
API_DELAY = 2             # 每张图片请求间隔（秒），避免触发频率限制
# ==============================================


def log(message: str, level: str = "INFO"):
    """打印带时间的日志"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {message}")


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)


def read_csv_prompts(csv_path: str) -> List[Dict[str, str]]:
    """读取CSV文件中的提示词列表"""
    prompts = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # 收集所有 angle 列
            angles = []
            for key in sorted(row.keys()):
                if key.startswith("angle") and row[key].strip():
                    angles.append(row[key].strip())
            
            prompts.append({
                "product_name": row.get("product_name", "").strip(),
                "prompt": row.get("prompt", "").strip(),
                "angles": angles if angles else ["正面", "侧面", "俯视", "细节"]
            })
    return prompts


def generate_one(client: ImageGenerationClient, prompt: str, size: str,
                 aspect_ratio: str, quality: str, save_path: str,
                 reference_images: Optional[List[str]] = None) -> bool:
    """
    生成单张图片，带重试机制
    """
    reference_images = reference_images or []
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            log(f"  尝试 {attempt}/{MAX_RETRIES}: 开始请求API...")
            result = client.generate(
                prompt=prompt,
                size=size,
                aspect_ratio=aspect_ratio,
                quality=quality,
                reference_images=reference_images,
                progress_callback=None
            )
            
            if not result.success:
                log(f"  API返回失败: {result.error_message}", "WARN")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return False
            
            # 获取图片数据
            image_data = result.image_data
            if not image_data and result.image_url:
                image_data = client.download_image(result.image_url)
            
            if not image_data:
                log("  无法获取图片数据", "WARN")
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return False
            
            # 保存
            with open(save_path, "wb") as f:
                f.write(image_data)
            
            return True
            
        except Exception as e:
            log(f"  异常: {e}", "ERROR")
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
    
    return False


def sanitize_filename(name: str) -> str:
    """清理文件名"""
    invalid = '<>:"/\\|?*'
    for char in invalid:
        name = name.replace(char, '_')
    return name.strip() or "unnamed"


def main():
    parser = argparse.ArgumentParser(description="ImageGenPro CSV批量生成器")
    parser.add_argument("-i", "--input", required=True, help="CSV文件路径")
    parser.add_argument("-o", "--output", required=True, help="图片输出目录")
    parser.add_argument("--api-key", default=os.environ.get("LIENIAO_API_KEY", ""), help="烈鸟API密钥")
    parser.add_argument("--api-url", default=DEFAULT_API_URL, help="API地址")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="模型名称")
    parser.add_argument("--ratio", default=DEFAULT_RATIO, help="画框比例")
    parser.add_argument("--quality", default=DEFAULT_QUALITY, help="画质")
    parser.add_argument("--ref", action="append", help="参考图路径（可多次使用）")
    parser.add_argument("--resume", action="store_true", default=True, help="断点续传（默认开启）")
    
    args = parser.parse_args()
    
    if not args.api_key:
        log("错误: 未提供API密钥。请使用 --api-key 参数或设置环境变量 LIENIAO_API_KEY", "ERROR")
        sys.exit(1)
    
    if not os.path.exists(args.input):
        log(f"错误: CSV文件不存在: {args.input}", "ERROR")
        sys.exit(1)
    
    ensure_dir(args.output)
    size = get_size_from_ratio(args.ratio)
    
    # 读取CSV
    prompts = read_csv_prompts(args.input)
    if not prompts:
        log("CSV中没有找到任何提示词数据", "ERROR")
        sys.exit(1)
    
    log(f"共读取 {len(prompts)} 个产品，准备批量生成...")
    
    # 初始化API客户端
    client = ImageGenerationClient(
        api_key=args.api_key,
        api_url=args.api_url,
        model=args.model
    )
    
    total_images = sum(len(p["angles"]) for p in prompts)
    completed = 0
    success_count = 0
    fail_count = 0
    skipped_count = 0
    
    # 遍历每个产品
    for idx, item in enumerate(prompts, 1):
        product_name = item["product_name"] or f"product_{idx}"
        base_prompt = item["prompt"]
        angles = item["angles"]
        
        log(f"\n[{idx}/{len(prompts)}] 正在处理: {product_name}")
        log(f"  基础提示词: {base_prompt[:60]}...")
        log(f"  需要生成 {len(angles)} 张图片")
        
        # 为每个角度生成
        for i, angle in enumerate(angles, 1):
            completed += 1
            full_prompt = f"{base_prompt}\n\n拍摄角度: {angle}"
            safe_product = sanitize_filename(product_name)
            safe_angle = sanitize_filename(angle[:15])
            filename = f"{safe_product}_{i:02d}_{safe_angle}.png"
            save_path = os.path.join(args.output, filename)
            
            # 断点续传检查
            if args.resume and os.path.exists(save_path) and os.path.getsize(save_path) > 1000:
                log(f"  [{completed}/{total_images}] {filename} 已存在，跳过")
                skipped_count += 1
                continue
            
            log(f"  [{completed}/{total_images}] 生成: {filename}")
            success = generate_one(
                client=client,
                prompt=full_prompt,
                size=size,
                aspect_ratio=args.ratio,
                quality=args.quality,
                save_path=save_path,
                reference_images=args.ref
            )
            
            if success:
                log(f"  ✅ 成功保存: {save_path}")
                success_count += 1
            else:
                log(f"  ❌ 生成失败: {filename}", "ERROR")
                fail_count += 1
            
            # 请求间隔，避免API限流
            if completed < total_images:
                time.sleep(API_DELAY)
    
    # 汇总
    log(f"\n{'='*50}")
    log(f"批量生成完成!")
    log(f"总计: {total_images} 张")
    log(f"成功: {success_count} 张")
    log(f"跳过: {skipped_count} 张（已存在）")
    log(f"失败: {fail_count} 张")
    log(f"输出目录: {args.output}")
    log(f"{'='*50}")
    
    if fail_count > 0:
        log("建议: 失败的图片可以重新运行本脚本，会自动跳过已成功的图片", "WARN")


if __name__ == "__main__":
    main()
