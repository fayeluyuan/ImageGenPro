#!/usr/bin/env python3
"""测试烈鸟API Gemini调用"""
import requests
import json
import time

def test_gemini_api():
    # 配置 - 请修改为你的授权码
    api_key = input("请输入授权码: ").strip()
    model = "gemini-3-pro-image-preview"
    prompt = "a cute dog"

    # 构建端点URL
    base_url = "https://lnapi.com"
    gemini_url = f"{base_url}/v1beta/models/{model}:generateContent?key={api_key}"

    print(f"\n请求URL: {gemini_url[:80]}...")
    print(f"模型: {model}")
    print(f"提示词: {prompt}")

    # 构建请求体
    payload = {
        "contents": [{
            "role": "user",
            "parts": [{"text": prompt}]
        }],
        "generation_config": {
            "response_modalities": ["TEXT", "IMAGE"]
        }
    }

    print("\n发送请求...")
    print(f"Payload: {json.dumps(payload, indent=2)}")

    headers = {"Content-Type": "application/json"}

    try:
        start_time = time.time()
        response = requests.post(gemini_url, json=payload, headers=headers, timeout=120)
        elapsed = time.time() - start_time
        print(f"\n响应时间: {elapsed:.2f}秒")
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n响应内容:\n{json.dumps(data, indent=2, ensure_ascii=False)[:1000]}...")

            # 检查是否有图片
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        print("\n✓ 成功获取图片数据！")
                        return True
                    if "text" in part:
                        print(f"\n文本响应: {part['text'][:200]}")
            print("\n✗ 未找到图片数据")
        else:
            print(f"\n错误: {response.status_code}")
            print(f"响应: {response.text[:500]}")

    except requests.exceptions.Timeout:
        print("\n✗ 请求超时（120秒）")
    except Exception as e:
        print(f"\n✗ 错误: {str(e)}")

    return False

if __name__ == "__main__":
    test_gemini_api()
    input("\n按回车键退出...")
