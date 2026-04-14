#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImageGenPro - AI图像生成程序
简化版，只支持单张图片生成
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.main_window import main

# 确保所有模块可以正确导入
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

if __name__ == "__main__":
    main()
