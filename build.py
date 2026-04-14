#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImageGenPro 打包脚本
支持打包单张生成版本和批量生成版本
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path


def clean_build():
    """清理构建目录"""
    dirs_to_remove = ['build']
    for dir_name in dirs_to_remove:
        if os.path.exists(dir_name):
            print(f"清理 {dir_name} 目录...")
            shutil.rmtree(dir_name)


def build_single():
    """构建单张生成版本"""
    print("\n" + "=" * 60)
    print("打包: ImageGenPro (单张生成版本)")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "ImageGenPro.spec",
        "--clean",
        "--noconfirm",
    ]

    print(f"命令: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = Path("dist") / "ImageGenPro.exe"
        if exe_path.exists():
            print(f"✓ 打包成功: {exe_path.absolute()}")
            print(f"  文件大小: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            return True
    return False


def build_batch():
    """构建批量生成版本"""
    print("\n" + "=" * 60)
    print("打包: ImageGenPro-Batch (批量生成版本)")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "ImageGenPro-Batch.spec",
        "--clean",
        "--noconfirm",
    ]

    print(f"命令: {' '.join(cmd)}\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = Path("dist") / "ImageGenPro-Batch.exe"
        if exe_path.exists():
            print(f"✓ 打包成功: {exe_path.absolute()}")
            print(f"  文件大小: {exe_path.stat().st_size / 1024 / 1024:.2f} MB")
            return True
    return False


def build_exe():
    """构建EXE文件"""
    print("=" * 60)
    print("ImageGenPro 打包程序")
    print("=" * 60)

    # 检查 PyInstaller
    try:
        import PyInstaller
        print("PyInstaller 已安装\n")
    except ImportError:
        print("正在安装 PyInstaller...")
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    # 清理旧构建
    clean_build()

    # 构建两个版本
    single_ok = build_single()
    batch_ok = build_batch()

    # 输出结果
    print("\n" + "=" * 60)
    print("打包结果汇总")
    print("=" * 60)

    if single_ok:
        print("✓ ImageGenPro.exe (单张生成版本) - 成功")
    else:
        print("✗ ImageGenPro.exe (单张生成版本) - 失败")

    if batch_ok:
        print("✓ ImageGenPro-Batch.exe (批量生成版本) - 成功")
    else:
        print("✗ ImageGenPro-Batch.exe (批量生成版本) - 失败")

    dist_path = Path("dist").absolute()
    print(f"\n所有文件已保存到: {dist_path}")

    if not (single_ok and batch_ok):
        sys.exit(1)


def build_single_only():
    """仅构建单张版本"""
    print("=" * 60)
    print("打包: ImageGenPro (单张生成版本)")
    print("=" * 60)

    try:
        import PyInstaller
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "ImageGenPro.spec",
        "--clean",
        "--noconfirm",
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = Path("dist") / "ImageGenPro.exe"
        print(f"\n✓ 打包成功: {exe_path.absolute()}")
    else:
        print("\n✗ 打包失败")
        sys.exit(1)


def build_batch_only():
    """仅构建批量版本"""
    print("=" * 60)
    print("打包: ImageGenPro-Batch (批量生成版本)")
    print("=" * 60)

    try:
        import PyInstaller
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "pyinstaller"], check=True)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "ImageGenPro-Batch.spec",
        "--clean",
        "--noconfirm",
    ]

    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe_path = Path("dist") / "ImageGenPro-Batch.exe"
        print(f"\n✓ 打包成功: {exe_path.absolute()}")
    else:
        print("\n✗ 打包失败")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="ImageGenPro 打包脚本")
    parser.add_argument(
        "--version",
        choices=["single", "batch", "all"],
        default="all",
        help="选择打包版本: single=单张, batch=批量, all=全部(默认)"
    )
    args = parser.parse_args()

    if args.version == "single":
        build_single_only()
    elif args.version == "batch":
        build_batch_only()
    else:
        build_exe()
