from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QLineEdit, QComboBox, QCheckBox, QPushButton,
    QTextEdit, QListWidget, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from pathlib import Path


class PathSelector(QWidget):
    """路径选择器组件"""
    path_changed = pyqtSignal(str)

    def __init__(self, is_directory=True, parent=None):
        super().__init__(parent)
        self.is_directory = is_directory
        self.setup_ui()

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("选择路径...")
        self.path_edit.textChanged.connect(self.path_changed.emit)
        layout.addWidget(self.path_edit)

        self.browse_btn = QPushButton("浏览")
        self.browse_btn.setFixedWidth(50)
        self.browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #bbb;
                padding: 4px 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
        """)
        self.browse_btn.clicked.connect(self.on_browse)
        layout.addWidget(self.browse_btn)

    def on_browse(self):
        if self.is_directory:
            path = QFileDialog.getExistingDirectory(self, "选择目录")
        else:
            path, _ = QFileDialog.getSaveFileName(self, "保存文件")
        if path:
            self.path_edit.setText(path)

    def get_path(self) -> str:
        return self.path_edit.text()

    def set_path(self, path: str):
        self.path_edit.setText(path)


class LeftPanel(QWidget):
    """左侧面板 - 配置区"""

    # 信号
    generate_requested = pyqtSignal()
    template_saved = pyqtSignal(str, str)
    template_deleted = pyqtSignal(str)
    template_selected = pyqtSignal(str)
    reference_images_changed = pyqtSignal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.reference_images = []
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # ===== 程序配置区块 =====
        config_group = QGroupBox("程序配置")
        config_layout = QVBoxLayout(config_group)
        config_layout.setSpacing(8)

        # 授权码
        auth_layout = QHBoxLayout()
        auth_layout.addWidget(QLabel("授权码:"))
        self.auth_input = QLineEdit()
        self.auth_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.auth_input.setPlaceholderText("输入API密钥")
        auth_layout.addWidget(self.auth_input)
        config_layout.addLayout(auth_layout)

        # Model
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Model:"))
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        self.model_combo.addItems([
            "gemini-2.0-flash-exp-image-generation",
            "gemini-3-pro-image-preview",
            "gemini-3.1-flash-image-preview",
            "dall-e-3",
            "dall-e-2"
        ])
        model_layout.addWidget(self.model_combo)
        config_layout.addLayout(model_layout)

        # 保存对话记录
        save_conv_layout = QHBoxLayout()
        self.save_conv_checkbox = QCheckBox("保存对话记录")
        save_conv_layout.addWidget(self.save_conv_checkbox)
        config_layout.addLayout(save_conv_layout)

        # 保存路径
        conv_path_layout = QHBoxLayout()
        conv_path_layout.addWidget(QLabel("保存路径:"))
        self.conv_path_selector = PathSelector(is_directory=True)
        conv_path_layout.addWidget(self.conv_path_selector)
        config_layout.addLayout(conv_path_layout)

        layout.addWidget(config_group)

        # ===== 生成参数区块 =====
        gen_group = QGroupBox("生成参数")
        gen_layout = QVBoxLayout(gen_group)
        gen_layout.setSpacing(8)

        # 画框比例和画质
        ratio_quality_layout = QHBoxLayout()

        ratio_layout = QHBoxLayout()
        ratio_layout.addWidget(QLabel("画框比例:"))
        self.ratio_combo = QComboBox()
        self.ratio_combo.addItems([
            "16:9", "1:1", "9:16", "4:3", "3:4", "21:9", "2:3", "3:2"
        ])
        ratio_layout.addWidget(self.ratio_combo)
        ratio_quality_layout.addLayout(ratio_layout)

        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("画质:"))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["4k", "2k", "1k"])
        quality_layout.addWidget(self.quality_combo)
        ratio_quality_layout.addLayout(quality_layout)
        gen_layout.addLayout(ratio_quality_layout)

        # 文件名
        filename_layout = QHBoxLayout()
        filename_layout.addWidget(QLabel("文件名:"))
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText("留空自动生成")
        filename_layout.addWidget(self.filename_input)
        gen_layout.addLayout(filename_layout)

        # 保存路径
        save_path_layout = QHBoxLayout()
        save_path_layout.addWidget(QLabel("保存路径:"))
        self.save_path_selector = PathSelector(is_directory=True)
        save_path_layout.addWidget(self.save_path_selector)
        gen_layout.addLayout(save_path_layout)

        # API网址
        api_layout = QHBoxLayout()
        api_layout.addWidget(QLabel("API网址:"))
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("https://lnapi.com/v1beta/models/gemini-3-pro-image-preview:generateContent")
        api_layout.addWidget(self.api_url_input)
        gen_layout.addLayout(api_layout)

        layout.addWidget(gen_group)

        # ===== 提示词配置区块 =====
        prompt_group = QGroupBox("提示词配置")
        prompt_layout = QVBoxLayout(prompt_group)
        prompt_layout.setSpacing(8)

        # 模板选择
        template_layout = QHBoxLayout()
        template_layout.addWidget(QLabel("输入提示词:"))
        self.template_combo = QComboBox()
        self.template_combo.setPlaceholderText("选择模板...")
        self.template_combo.currentTextChanged.connect(self.on_template_selected)
        template_layout.addWidget(self.template_combo)
        prompt_layout.addLayout(template_layout)

        # 提示词输入
        self.prompt_text = QTextEdit()
        self.prompt_text.setPlaceholderText("在此输入提示词，描述你想要生成的图片...")
        self.prompt_text.setMinimumHeight(120)
        prompt_layout.addWidget(self.prompt_text)

        # 模板按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(5)
        btn_layout.setContentsMargins(0, 2, 0, 2)
        self.save_template_btn = QPushButton("保存模板")
        self.save_template_btn.setFixedHeight(26)
        self.save_template_btn.clicked.connect(self.on_save_template)
        self.save_template_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        btn_layout.addWidget(self.save_template_btn)

        self.delete_template_btn = QPushButton("删除模板")
        self.delete_template_btn.setFixedHeight(26)
        self.delete_template_btn.clicked.connect(self.on_delete_template)
        self.delete_template_btn.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        btn_layout.addWidget(self.delete_template_btn)
        btn_layout.addStretch()
        prompt_layout.addLayout(btn_layout)

        # 参考图区域
        ref_label = QLabel("参考图（支持多张）")
        ref_label.setContentsMargins(0, 4, 0, 0)
        prompt_layout.addWidget(ref_label)

        ref_btn_layout = QHBoxLayout()
        ref_btn_layout.setSpacing(5)
        ref_btn_layout.setContentsMargins(0, 2, 0, 2)
        self.add_ref_btn = QPushButton("+ 添加参考图")
        self.add_ref_btn.setFixedHeight(26)
        self.add_ref_btn.clicked.connect(self.on_add_reference)
        self.add_ref_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        ref_btn_layout.addWidget(self.add_ref_btn)

        self.clear_ref_btn = QPushButton("清空所有")
        self.clear_ref_btn.setFixedHeight(26)
        self.clear_ref_btn.clicked.connect(self.on_clear_references)
        self.clear_ref_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff9800;
                color: white;
                border: none;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e68900;
            }
        """)
        ref_btn_layout.addWidget(self.clear_ref_btn)
        ref_btn_layout.addStretch()
        prompt_layout.addLayout(ref_btn_layout)

        # 参考图列表
        self.ref_list = QListWidget()
        self.ref_list.setMaximumHeight(80)
        prompt_layout.addWidget(self.ref_list)

        layout.addWidget(prompt_group)
        layout.addStretch()

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
            QLineEdit, QComboBox, QTextEdit {
                padding: 5px;
                border: 1px solid #bbb;
                border-radius: 4px;
                background-color: white;
            }
            QLineEdit:focus, QComboBox:focus, QTextEdit:focus {
                border: 1px solid #2196F3;
            }
            QListWidget {
                border: 1px solid #bbb;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
        """)

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
            self.reference_images_changed.emit(self.reference_images)

    def on_clear_references(self):
        self.reference_images.clear()
        self.ref_list.clear()
        self.reference_images_changed.emit(self.reference_images)

    def on_save_template(self):
        prompt = self.prompt_text.toPlainText().strip()
        if not prompt:
            QMessageBox.warning(self, "警告", "提示词不能为空")
            return

        name = self.template_combo.currentText().strip()
        if not name or name == "选择模板...":
            name = f"模板{self.template_combo.count()}"

        existing_index = self.template_combo.findText(name)
        if existing_index == -1:
            self.template_combo.addItem(name)
            self.template_combo.setCurrentText(name)

        self.template_saved.emit(name, prompt)
        QMessageBox.information(self, "成功", f"模板 '{name}' 已保存")

    def on_delete_template(self):
        name = self.template_combo.currentText()
        if not name or name == "选择模板...":
            return

        reply = QMessageBox.question(
            self, "确认", f"确定要删除模板 '{name}' 吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            index = self.template_combo.currentIndex()
            self.template_combo.removeItem(index)
            self.template_deleted.emit(name)
            self.prompt_text.clear()

    def on_template_selected(self, name: str):
        if name and name != "选择模板...":
            self.template_selected.emit(name)

    def load_templates(self, templates: dict):
        """加载模板列表"""
        self.template_combo.clear()
        self.template_combo.addItem("选择模板...")
        for name in templates.keys():
            self.template_combo.addItem(name)

    def set_prompt(self, text: str):
        """设置提示词文本"""
        self.prompt_text.setPlainText(text)

    # ===== 获取配置值的方法 =====
    def get_api_key(self) -> str:
        return self.auth_input.text()

    def get_model(self) -> str:
        return self.model_combo.currentText()

    def get_save_conversation(self) -> bool:
        return self.save_conv_checkbox.isChecked()

    def get_conversation_path(self) -> str:
        return self.conv_path_selector.get_path()

    def get_aspect_ratio(self) -> str:
        return self.ratio_combo.currentText()

    def get_quality(self) -> str:
        return self.quality_combo.currentText()

    def get_filename(self) -> str:
        return self.filename_input.text()

    def get_save_path(self) -> str:
        return self.save_path_selector.get_path()

    def get_api_url(self) -> str:
        return self.api_url_input.text()

    def get_prompt(self) -> str:
        return self.prompt_text.toPlainText()

    def get_reference_images(self) -> list:
        return self.reference_images.copy()

    # ===== 设置配置值的方法 =====
    def set_api_key(self, value: str):
        self.auth_input.setText(value)

    def set_model(self, value: str):
        self.model_combo.setCurrentText(value)

    def set_save_conversation(self, value: bool):
        self.save_conv_checkbox.setChecked(value)

    def set_conversation_path(self, value: str):
        self.conv_path_selector.set_path(value)

    def set_aspect_ratio(self, value: str):
        self.ratio_combo.setCurrentText(value)

    def set_quality(self, value: str):
        self.quality_combo.setCurrentText(value)

    def set_filename(self, value: str):
        self.filename_input.setText(value)

    def set_save_path(self, value: str):
        self.save_path_selector.set_path(value)

    def set_api_url(self, value: str):
        self.api_url_input.setText(value)

    def set_reference_images(self, images: list):
        """设置参考图列表"""
        self.reference_images = images.copy()
        self.ref_list.clear()
        for img in images:
            self.ref_list.addItem(Path(img).name)
        self.reference_images_changed.emit(self.reference_images)
