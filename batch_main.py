#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImageGenPro Batch - AI图像批量生成程序
支持生成1-8张不同角度的产品照片
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ui.batch_main_window import main

# 确保所有模块可以正确导入
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

if __name__ == "__main__":
    main()
