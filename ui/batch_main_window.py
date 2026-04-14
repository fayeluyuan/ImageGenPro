#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ImageGenPro Batch - 批量生成版本主窗口
支持1-8张不同角度产品照片生成
"""

import sys
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QApplication,
    QMessageBox, QFileDialog, QVBoxLayout, QLabel,
    QSpinBox, QProgressBar, QGridLayout, QGroupBox,
    QComboBox, QPushButton, QTextEdit, QCheckBox,
    QLineEdit, QListWidget, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QImage

from config.settings import config_manager, AppConfig
from core.api_client import ImageGenerationClient, get_size_from_ratio


class BatchGenerationWorker(QThread):
    """批量图像生成工作线程"""

    progress = pyqtSignal(str, int)  # 消息, 当前进度
    image_finished = pyqtSignal(int, bool, bytes, str)  # 序号, 成功, 图片数据, 错误信息
    all_finished = pyqtSignal(bool, str)  # 全部完成, 总体结果

    def __init__(self, client, base_prompt: str, angle_prompts: List[str], size: str,
                 aspect_ratio: str, quality: str, reference_images: List[str],
                 save_dir: str, filename_prefix: str):
        super().__init__()
        self.client = client
        self.base_prompt = base_prompt
        self.angle_prompts = angle_prompts
        self.size = size
        self.aspect_ratio = aspect_ratio
        self.quality = quality
        self.reference_images = reference_images
        self.save_dir = save_dir
        self.filename_prefix = filename_prefix
        self._is_running = True
        self.generated_count = 0

    def stop(self):
        """停止生成"""
        self._is_running = False

    def run(self):
        """运行批量生成任务"""
        total = len(self.angle_prompts)

        for i, angle_desc in enumerate(self.angle_prompts):
            if not self._is_running:
                self.all_finished.emit(False, "用户取消")
                return

            current_num = i + 1
            self.progress.emit(f"正在生成第 {current_num}/{total} 张: {angle_desc}", current_num)

            # 构建带角度的提示词
            full_prompt = f"{self.base_prompt}\n\n拍摄角度: {angle_desc}"

            try:
                result = self.client.generate(
                    prompt=full_prompt,
                    size=self.size,
                    aspect_ratio=self.aspect_ratio,
                    quality=self.quality,
                    reference_images=self.reference_images,
                    progress_callback=None
                )

                if result.success:
                    image_data = result.image_data
                    if not image_data and result.image_url:
                        image_data = self.client.download_image(result.image_url)

                    if image_data:
                        # 自动保存
                        filename = f"{self.filename_prefix}_{current_num:02d}_{self._sanitize_filename(angle_desc[:20])}.png"
                        filepath = os.path.join(self.save_dir, filename)
                        try:
                            with open(filepath, 'wb') as f:
                                f.write(image_data)
                        except Exception as e:
                            print(f"保存失败: {e}")

                        self.image_finished.emit(current_num, True, image_data, "")
                        self.generated_count += 1
                    else:
                        self.image_finished.emit(current_num, False, b'', "无法获取图片数据")
                else:
                    self.image_finished.emit(current_num, False, b'', result.error_message or "生成失败")

            except Exception as e:
                self.image_finished.emit(current_num, False, b'', str(e))

        self.all_finished.emit(True, f"完成 {self.generated_count}/{total}")

    def _sanitize_filename(self, name: str) -> str:
        """清理文件名中的非法字符"""
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            name = name.replace(char, '_')
        return name.strip()


class BatchLeftPanel(QWidget):
    """左侧面板 - 批量生成配置"""

    generate_requested = pyqtSignal()
    stop_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reference_images = []
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # ===== API配置区块 =====
        api_group = QGroupBox("API配置")
        api_layout = QVBoxLayout(api_group)
        api_layout.setSpacing(8)

        # 授权码
        auth_layout = QHBoxLayout()
        auth_layout.addWidget(QLabel("授权码:"))
        self.auth_input = QLineEdit()
        self.auth_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.auth_input.setPlaceholderText("输入API密钥")
        auth_layout.addWidget(self.auth_input)
        api_layout.addLayout(auth_layout)

        # API网址
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("API网址:"))
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("https://lnapi.com/v1beta/models/gemini-3-pro-image-preview:generateContent")
        url_layout.addWidget(self.api_url_input)
        api_layout.addLayout(url_layout)

        # Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("模型:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "gemini-3-pro-image-preview",
            "gemini-2.0-flash-exp-image-generation",
            "gemini-3.1-flash-image-preview",
        ])
        model_layout.addWidget(self.model_combo)
        api_layout.addLayout(model_layout)

        layout.addWidget(api_group)

        # ===== 批量生成配置区块 =====
        batch_group = QGroupBox("批量生成配置")
        batch_layout = QVBoxLayout(batch_group)
        batch_layout.setSpacing(10)

        # 生成数量
        count_layout = QHBoxLayout()
        count_layout.addWidget(QLabel("生成数量:"))
        self.count_spin = QSpinBox()
        self.count_spin.setRange(1, 8)
        self.count_spin.setValue(4)
        self.count_spin.valueChanged.connect(self.on_count_changed)
        count_layout.addWidget(self.count_spin)
        count_layout.addStretch()
        batch_layout.addLayout(count_layout)

        # 画框比例
        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(QLabel("画框比例:"))
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems(["1:1", "4:3", "3:4", "16:9", "9:16"])
        ratio_layout.addWidget(self.ratio_combo)
        ratio_layout.addStretch()
        batch_layout.addLayout(ratio_layout)

        # 画质
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("画质:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["2k", "4k", "1k"])
        quality_layout.addWidget(self.quality_combo)
        quality_layout.addStretch()
        batch_layout.addLayout(quality_layout)

        # 保存路径
        save_layout = QHBoxLayout()
        save_layout.addWidget(QLabel("保存路径:"))
        self.save_path_input = QLineEdit()
        self.save_path_input.setPlaceholderText("选择保存目录...")
        save_layout.addWidget(self.save_path_input)
        self.browse_btn = QPushButton("浏览")
        self.browse_btn.clicked.connect(self.on_browse_save)
        save_layout.addWidget(self.browse_btn)
        batch_layout.addLayout(save_layout)

        # 文件名前缀
        prefix_layout = QHBoxLayout()
        prefix_layout.addWidget(QLabel("文件名前缀:"))
        self.prefix_input = QLineEdit()
        self.prefix_input.setPlaceholderText("product")
        prefix_layout.addWidget(self.prefix_input)
        batch_layout.addLayout(prefix_layout)

        layout.addWidget(batch_group)

        # ===== 角度配置区块 =====
        angle_group = QGroupBox("拍摄角度配置")
        angle_layout = QVBoxLayout(angle_group)
        angle_layout.setSpacing(8)

        # 角度预设
        preset_layout = QHBoxLayout()
        preset_layout.addWidget(QLabel("快速预设:"))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "电商产品4角度",
            "电商产品6角度",
            "电商产品8角度",
            "自定义"
        ])
        self.preset_combo.currentTextChanged.connect(self.on_preset_changed)
        preset_layout.addWidget(self.preset_combo)
        preset_layout.addStretch()
        angle_layout.addLayout(preset_layout)

        # 角度列表
        angle_layout.addWidget(QLabel("各角度描述:"))
        self.angle_list = QListWidget()
        self.angle_list.setMaximumHeight(150)
        angle_layout.addWidget(self.angle_list)

        # 角度编辑
        edit_layout = QHBoxLayout()
        self.angle_edit = QLineEdit()
        self.angle_edit.setPlaceholderText("添加新角度描述...")
        edit_layout.addWidget(self.angle_edit)
        self.add_angle_btn = QPushButton("添加")
        self.add_angle_btn.clicked.connect(self.on_add_angle)
        edit_layout.addWidget(self.add_angle_btn)
        self.remove_angle_btn = QPushButton("删除")
        self.remove_angle_btn.clicked.connect(self.on_remove_angle)
        edit_layout.addWidget(self.remove_angle_btn)
        angle_layout.addLayout(edit_layout)

        layout.addWidget(angle_group)

        # ===== 参考图区块 =====
        ref_group = QGroupBox("参考图（可选）")
        ref_layout = QVBoxLayout(ref_group)
        ref_layout.setSpacing(8)

        ref_btn_layout = QHBoxLayout()
        self.add_ref_btn = QPushButton("+ 添加参考图")
        self.add_ref_btn.clicked.connect(self.on_add_reference)
        ref_btn_layout.addWidget(self.add_ref_btn)
        self.clear_ref_btn = QPushButton("清空")
        self.clear_ref_btn.clicked.connect(self.on_clear_references)
        ref_btn_layout.addWidget(self.clear_ref_btn)
        ref_btn_layout.addStretch()
        ref_layout.addLayout(ref_btn_layout)

        self.ref_list = QListWidget()
        self.ref_list.setMaximumHeight(80)
        ref_layout.addWidget(self.ref_list)

        layout.addWidget(ref_group)

        # ===== 提示词区块 =====
        prompt_group = QGroupBox("产品描述提示词")
        prompt_layout = QVBoxLayout(prompt_group)

        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("描述产品特征，例如：\"一款白色无线蓝牙耳机，简约设计，哑光质感，放在木质桌面上...\"")
        self.prompt_text.setMinimumHeight(100)
        prompt_layout.addWidget(self.prompt_text)

        layout.addWidget(prompt_group)

        # ===== 操作按钮 =====
        btn_layout = QHBoxLayout()

        self.generate_btn = QPushButton("开始批量生成")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.clicked.connect(self.generate_requested.emit)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        btn_layout.addWidget(self.generate_btn)

        self.stop_btn = QPushButton("停止")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self.stop_requested.emit)
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)
        layout.addStretch()

        # 初始化角度列表
        self.on_preset_changed("电商产品4角度")

    def apply_styles(self):
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #f5f5f5;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #333333;
            }
            QLabel {
                color: #333333;
                font-size: 12px;
            }
            QLineEdit, QComboBox, QTextEdit, QSpinBox {
                padding: 5px;
                border: 1px solid #bbb;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget {
                border: 1px solid #bbb;
                border-radius: 4px;
                background-color: white;
            }
        """)

    def on_browse_save(self):
        path = QFileDialog.getExistingDirectory(self, "选择保存目录")
        if path:
            self.save_path_input.setText(path)

    def on_preset_changed(self, preset: str):
        """角度预设变更"""
        presets = {
            "电商产品4角度": [
                "正面平视角度，展示整体外观",
                "45度侧视角度，展示立体感",
                "俯视角度，展示顶部细节",
                "背面角度，展示后视图"
            ],
            "电商产品6角度": [
                "正面平视角度，展示整体外观",
                "左侧45度角度，展示左侧面",
                "右侧45度角度，展示右侧面",
                "俯视角度，展示顶部细节",
                "背面角度，展示后视图",
                "仰视角微距，展示底部细节"
            ],
            "电商产品8角度": [
                "正面平视角度，展示整体外观",
                "左侧45度角度，展示左侧面",
                "正侧面90度，展示侧面轮廓",
                "右侧45度角度，展示右侧面",
                "俯视45度角度，展示顶部和正面",
                "纯俯视角度，展示顶部细节",
                "背面角度，展示后视图",
                "特写细节角度，展示材质纹理"
            ],
            "自定义": []
        }

        angles = presets.get(preset, [])
        self.angle_list.clear()
        for angle in angles:
            self.angle_list.addItem(angle)

        # 更新数量
        self.count_spin.setValue(len(angles))

    def on_count_changed(self, count: int):
        """数量变更时更新角度列表"""
        current_count = self.angle_list.count()
        if count > current_count:
            # 添加默认角度
            for i in range(current_count, count):
                self.angle_list.addItem(f"角度{i+1}: 请描述拍摄角度")
        elif count < current_count:
            # 移除多余角度
            for i in range(current_count - 1, count - 1, -1):
                self.angle_list.takeItem(i)

    def on_add_angle(self):
        text = self.angle_edit.text().strip()
        if text:
            self.angle_list.addItem(text)
            self.angle_edit.clear()
            self.count_spin.setValue(self.angle_list.count())

    def on_remove_angle(self):
        current_row = self.angle_list.currentRow()
        if current_row >= 0:
            self.angle_list.takeItem(current_row)
            self.count_spin.setValue(self.angle_list.count())

    def on_add_reference(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择参考图", "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.bmp *.webp)"
        )
        if files:
            for f in files:
                if f not in self.reference_images:
                    self.reference_images.append(f)
                    self.ref_list.addItem(Path(f).name)

    def on_clear_references(self):
        self.reference_images.clear()
        self.ref_list.clear()

    def set_generating(self, generating: bool):
        """设置生成状态"""
        self.generate_btn.setEnabled(not generating)
        self.stop_btn.setEnabled(generating)

    # ===== 获取配置值 =====
    def get_api_key(self) -> str:
        return self.auth_input.text()

    def get_api_url(self) -> str:
        return self.api_url_input.text()

    def get_model(self) -> str:
        return self.model_combo.currentText()

    def get_count(self) -> int:
        return self.count_spin.value()

    def get_aspect_ratio(self) -> str:
        return self.ratio_combo.currentText()

    def get_quality(self) -> str:
        return self.quality_combo.currentText()

    def get_save_path(self) -> str:
        return self.save_path_input.text()

    def get_prefix(self) -> str:
        return self.prefix_input.text() or "product"

    def get_prompt(self) -> str:
        return self.prompt_text.toPlainText()

    def get_reference_images(self) -> List[str]:
        return self.reference_images.copy()

    def get_angle_prompts(self) -> List[str]:
        """获取所有角度描述"""
        prompts = []
        for i in range(self.angle_list.count()):
            prompts.append(self.angle_list.item(i).text())
        return prompts[:self.get_count()]


class BatchRightPanel(QWidget):
    """右侧面板 - 批量生成结果展示"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.image_widgets = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 标题
        title = QLabel("批量生成结果")
        title.setStyleSheet("font-size: 16px; font-weight: bold; padding: 5px;")
        layout.addWidget(title)

        # 进度条
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(QLabel("总体进度:"))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        self.progress_label = QLabel("0/0")
        progress_layout.addWidget(self.progress_label)
        layout.addLayout(progress_layout)

        # 状态标签
        self.status_label = QLabel("准备就绪")
        self.status_label.setStyleSheet("color: #666; padding: 5px;")
        layout.addWidget(self.status_label)

        # 图片展示区 - 使用滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.images_container = QWidget()
        self.images_grid = QGridLayout(self.images_container)
        self.images_grid.setSpacing(10)
        layout.addWidget(scroll)
        scroll.setWidget(self.images_container)

        self.clear_results()

    def clear_results(self, count: int = 8):
        """清空并初始化结果区域"""
        # 清除旧控件
        while self.images_grid.count():
            item = self.images_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.image_widgets = []

        # 创建图片占位框
        for i in range(count):
            frame = QFrame()
            frame.setFrameShape(QFrame.Shape.StyledPanel)
            frame.setStyleSheet("""
                QFrame {
                    border: 2px dashed #cccccc;
                    border-radius: 8px;
                    background-color: #f9f9f9;
                    min-width: 200px;
                    min-height: 200px;
                }
            """)

            frame_layout = QVBoxLayout(frame)

            # 序号标签
            num_label = QLabel(f"#{i+1}")
            num_label.setStyleSheet("font-weight: bold; font-size: 14px;")
            num_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_layout.addWidget(num_label)

            # 图片标签
            img_label = QLabel("等待生成...")
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setMinimumSize(180, 180)
            img_label.setStyleSheet("background-color: #eeeeee; border-radius: 4px;")
            frame_layout.addWidget(img_label)

            # 状态标签
            status_label = QLabel("未开始")
            status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            status_label.setStyleSheet("color: #999; font-size: 11px;")
            frame_layout.addWidget(status_label)

            # 保存按钮
            save_btn = QPushButton("保存")
            save_btn.setEnabled(False)
            save_btn.clicked.connect(lambda checked, idx=i: self.on_save_image(idx))
            frame_layout.addWidget(save_btn)

            row = i // 4
            col = i % 4
            self.images_grid.addWidget(frame, row, col)

            self.image_widgets.append({
                'frame': frame,
                'image_label': img_label,
                'status_label': status_label,
                'save_btn': save_btn,
                'image_data': None
            })

    def set_progress(self, current: int, total: int):
        """设置进度"""
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.progress_label.setText(f"{current}/{total}")

    def set_status(self, message: str):
        """设置状态文本"""
        self.status_label.setText(message)

    def set_image(self, index: int, image_data: bytes, success: bool = True):
        """设置指定位置的图片"""
        if index < 0 or index >= len(self.image_widgets):
            return

        widget = self.image_widgets[index]

        if success and image_data:
            # 显示图片
            pixmap = QPixmap()
            pixmap.loadFromData(image_data)
            if not pixmap.isNull():
                scaled = pixmap.scaled(180, 180, Qt.AspectRatioMode.KeepAspectRatio,
                                       Qt.TransformationMode.SmoothTransformation)
                widget['image_label'].setPixmap(scaled)
                widget['image_label'].setStyleSheet("background-color: transparent;")

            widget['status_label'].setText("✓ 生成成功")
            widget['status_label'].setStyleSheet("color: #4CAF50; font-size: 11px;")
            widget['save_btn'].setEnabled(True)
            widget['image_data'] = image_data
            widget['frame'].setStyleSheet("""
                QFrame {
                    border: 2px solid #4CAF50;
                    border-radius: 8px;
                    background-color: #f0f8f0;
                    min-width: 200px;
                    min-height: 200px;
                }
            """)
        else:
            widget['status_label'].setText("✗ 生成失败")
            widget['status_label'].setStyleSheet("color: #f44336; font-size: 11px;")
            widget['frame'].setStyleSheet("""
                QFrame {
                    border: 2px solid #f44336;
                    border-radius: 8px;
                    background-color: #fff0f0;
                    min-width: 200px;
                    min-height: 200px;
                }
            """)

    def on_save_image(self, index: int):
        """保存单张图片"""
        if index >= len(self.image_widgets):
            return

        widget = self.image_widgets[index]
        if not widget['image_data']:
            return

        path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", f"image_{index+1:02d}.png",
            "PNG图片 (*.png);;JPEG图片 (*.jpg)"
        )
        if path:
            try:
                with open(path, 'wb') as f:
                    f.write(widget['image_data'])
                QMessageBox.information(self, "成功", f"图片已保存到:\n{path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")


class BatchMainWindow(QMainWindow):
    """批量生成主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageGenPro Batch - AI批量图像生成")
        self.setMinimumSize(1400, 900)

        self.worker = None
        self.setup_ui()
        self.apply_styles()
        self.load_config()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        layout = QHBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 左侧面板
        self.left_panel = BatchLeftPanel()
        self.left_panel.setFixedWidth(450)
        self.left_panel.generate_requested.connect(self.on_generate)
        self.left_panel.stop_requested.connect(self.on_stop)
        layout.addWidget(self.left_panel)

        # 右侧面板
        self.right_panel = BatchRightPanel()
        layout.addWidget(self.right_panel)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QProgressBar {
                border: 1px solid #bbb;
                border-radius: 4px;
                text-align: center;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)

    def load_config(self):
        """加载配置"""
        config = config_manager.load_config()
        self.left_panel.auth_input.setText(config.api_key)
        self.left_panel.api_url_input.setText(config.api_url)
        self.left_panel.model_combo.setCurrentText(config.model)
        self.left_panel.save_path_input.setText(config.save_path)

    def save_config(self):
        """保存配置"""
        config = config_manager.load_config()
        config.api_key = self.left_panel.get_api_key()
        config.api_url = self.left_panel.get_api_url()
        config.model = self.left_panel.get_model()
        config.save_path = self.left_panel.get_save_path()
        config_manager.save_config(config)

    def closeEvent(self, event):
        """关闭事件"""
        self.save_config()
        event.accept()

    def on_generate(self):
        """开始批量生成"""
        # 验证输入
        api_key = self.left_panel.get_api_key()
        api_url = self.left_panel.get_api_url()
        prompt = self.left_panel.get_prompt()
        save_path = self.left_panel.get_save_path()

        if not api_key:
            QMessageBox.warning(self, "警告", "请输入授权码")
            return
        if not api_url:
            QMessageBox.warning(self, "警告", "请输入API网址")
            return
        if not prompt:
            QMessageBox.warning(self, "警告", "请输入产品描述")
            return
        if not save_path or not os.path.isdir(save_path):
            QMessageBox.warning(self, "警告", "请选择有效的保存路径")
            return

        # 获取参数
        count = self.left_panel.get_count()
        aspect_ratio = self.left_panel.get_aspect_ratio()
        quality = self.left_panel.get_quality()
        reference_images = self.left_panel.get_reference_images()
        angle_prompts = self.left_panel.get_angle_prompts()
        prefix = self.left_panel.get_prefix()

        if len(angle_prompts) < count:
            QMessageBox.warning(self, "警告", f"角度描述数量({len(angle_prompts)})少于生成数量({count})")
            return

        # 限制角度数量
        angle_prompts = angle_prompts[:count]

        # 计算尺寸
        size = get_size_from_ratio(aspect_ratio, quality, self.left_panel.get_model())

        # 创建API客户端
        client = ImageGenerationClient(api_url, api_key, self.left_panel.get_model())

        # 初始化UI
        self.right_panel.clear_results(count)
        self.right_panel.set_progress(0, count)
        self.right_panel.set_status("准备生成...")
        self.left_panel.set_generating(True)

        # 创建工作线程
        self.worker = BatchGenerationWorker(
            client, prompt, angle_prompts, size,
            aspect_ratio, quality, reference_images,
            save_path, prefix
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.image_finished.connect(self.on_image_finished)
        self.worker.all_finished.connect(self.on_all_finished)
        self.worker.start()

    def on_stop(self):
        """停止生成"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(2000)
            self.left_panel.set_generating(False)
            self.right_panel.set_status("已停止")

    def on_progress(self, message: str, current: int):
        """进度更新"""
        self.right_panel.set_status(message)
        self.right_panel.set_progress(current, self.left_panel.get_count())

    def on_image_finished(self, index: int, success: bool, image_data: bytes, error: str):
        """单张完成"""
        self.right_panel.set_image(index - 1, image_data, success)
        if not success:
            self.right_panel.set_status(f"第{index}张生成失败: {error[:50]}")

    def on_all_finished(self, success: bool, message: str):
        """全部完成"""
        self.left_panel.set_generating(False)
        self.right_panel.set_status(message)

        if success:
            save_path = self.left_panel.get_save_path()
            QMessageBox.information(
                self, "完成",
                f"批量生成完成！\n\n结果: {message}\n\n保存位置: {save_path}"
            )


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    app.setStyleSheet("""
        QToolTip {
            border: 1px solid #cccccc;
            background-color: #ffffe0;
            padding: 5px;
            border-radius: 3px;
        }
    """)

    window = BatchMainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
