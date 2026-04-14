from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFileDialog, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPixmap, QImage
from PIL import Image
import io


class ImagePreviewWidget(QWidget):
    """单张图片预览组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_pixmap = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        # 图片显示标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 2px dashed #cccccc;
                border-radius: 8px;
            }
        """)
        self.image_label.setMinimumSize(400, 400)
        self.image_label.setText("等待生成...")
        layout.addWidget(self.image_label)

    def set_image(self, image_data: bytes):
        """设置图片"""
        try:
            image = Image.open(io.BytesIO(image_data))
            qimage = self._pil_to_qimage(image)
            pixmap = QPixmap.fromImage(qimage)
            self.current_pixmap = pixmap
            self._update_display()
        except Exception as e:
            self.image_label.setText(f"图片加载失败: {str(e)}")

    def _pil_to_qimage(self, pil_image):
        """PIL Image 转换为 QImage"""
        if pil_image.mode == 'RGBA':
            format = QImage.Format.Format_RGBA8888
        elif pil_image.mode == 'RGB':
            format = QImage.Format.Format_RGB888
        else:
            pil_image = pil_image.convert('RGB')
            format = QImage.Format.Format_RGB888

        data = pil_image.tobytes('raw', pil_image.mode)
        qimage = QImage(data, pil_image.width, pil_image.height, format)
        return qimage

    def _update_display(self):
        """更新显示"""
        if self.current_pixmap:
            scaled_pixmap = self.current_pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
            self.image_label.setStyleSheet("""
                QLabel {
                    background-color: transparent;
                    border: none;
                }
            """)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_display()

    def get_image_data(self) -> bytes:
        """获取当前图片数据"""
        if self.current_pixmap:
            buffer = io.BytesIO()
            image = Image.open(io.BytesIO(self.current_pixmap.toImage().bits().asstring()))
            image.save(buffer, format='PNG')
            return buffer.getvalue()
        return b''

    def clear(self):
        """清空预览"""
        self.current_pixmap = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("等待生成...")
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                border: 2px dashed #cccccc;
                border-radius: 8px;
            }
        """)


class RightPanel(QWidget):
    """右侧面板 - 预览区"""

    # 信号
    generate_requested = pyqtSignal()
    set_as_reference_requested = pyqtSignal()
    save_image_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_image_data = None
        self.setup_ui()
        self.apply_styles()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # 标题
        title = QLabel("生成图片预览")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        layout.addWidget(title)

        # 图片预览区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self.preview_widget = ImagePreviewWidget()
        scroll.setWidget(self.preview_widget)
        layout.addWidget(scroll)

        # 操作按钮行
        action_layout = QHBoxLayout()

        self.set_ref_btn = QPushButton("将预览图设为参考图")
        self.set_ref_btn.setEnabled(False)
        self.set_ref_btn.clicked.connect(self.set_as_reference_requested.emit)
        self.set_ref_btn.setStyleSheet("""
            QPushButton {
                background-color: #9e9e9e;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:enabled {
                background-color: #2196F3;
            }
            QPushButton:enabled:hover {
                background-color: #0b7dda;
            }
        """)
        action_layout.addWidget(self.set_ref_btn)

        self.save_btn = QPushButton("保存图片")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.on_save_image)
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #9e9e9e;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:enabled {
                background-color: #4CAF50;
            }
            QPushButton:enabled:hover {
                background-color: #45a049;
            }
        """)
        action_layout.addWidget(self.save_btn)

        layout.addLayout(action_layout)

        # 生成按钮
        self.generate_btn = QPushButton("生成图片")
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.clicked.connect(self.generate_requested.emit)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #095a9e;
            }
        """)
        layout.addWidget(self.generate_btn)

        # 状态栏
        self.status_label = QLabel("就绪")
        self.status_label.setStyleSheet("color: #666; font-size: 12px; padding: 5px;")
        layout.addWidget(self.status_label)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #fafafa;
            }
        """)

    def set_image(self, image_data: bytes):
        """设置预览图片"""
        self.current_image_data = image_data
        self.preview_widget.set_image(image_data)
        self.set_ref_btn.setEnabled(True)
        self.save_btn.setEnabled(True)

    def clear_preview(self):
        """清空预览"""
        self.current_image_data = None
        self.preview_widget.clear()
        self.set_ref_btn.setEnabled(False)
        self.save_btn.setEnabled(False)

    def set_status(self, message: str):
        """设置状态信息"""
        self.status_label.setText(message)

    def set_generating(self, generating: bool):
        """设置生成状态"""
        if generating:
            self.generate_btn.setEnabled(False)
            self.generate_btn.setText("生成中...")
        else:
            self.generate_btn.setEnabled(True)
            self.generate_btn.setText("生成图片")

    def on_save_image(self):
        """保存图片"""
        if not self.current_image_data:
            QMessageBox.warning(self, "警告", "没有可保存的图片")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存图片", "generated_image.png",
            "图片文件 (*.png *.jpg *.jpeg)"
        )

        if file_path:
            try:
                with open(file_path, 'wb') as f:
                    f.write(self.current_image_data)
                QMessageBox.information(self, "成功", f"图片已保存到:\n{file_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {str(e)}")

    def get_current_image_data(self) -> bytes:
        """获取当前图片数据"""
        return self.current_image_data
