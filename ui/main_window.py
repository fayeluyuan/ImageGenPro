import sys
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QApplication,
    QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from ui.left_panel import LeftPanel
from ui.right_panel import RightPanel
from config.settings import config_manager, AppConfig
from core.api_client import ImageGenerationClient, get_size_from_ratio


class GenerationWorker(QThread):
    """图像生成工作线程"""

    progress = pyqtSignal(str)
    finished = pyqtSignal(bool, bytes, str)

    def __init__(self, client, prompt, size, aspect_ratio, quality, reference_images):
        super().__init__()
        self.client = client
        self.prompt = prompt
        self.size = size
        self.aspect_ratio = aspect_ratio
        self.quality = quality
        self.reference_images = reference_images
        self._is_running = True

    def stop(self):
        """停止生成"""
        self._is_running = False

    def run(self):
        """运行生成任务"""
        try:
            self.progress.emit("正在生成...")
            result = self.client.generate(
                prompt=self.prompt,
                size=self.size,
                aspect_ratio=self.aspect_ratio,
                quality=self.quality,
                reference_images=self.reference_images,
                progress_callback=lambda msg: self.progress.emit(msg)
            )

            if result.success:
                self.finished.emit(True, result.image_data or b'', "")
            else:
                self.finished.emit(False, b'', result.error_message or "未知错误")

        except Exception as e:
            self.finished.emit(False, b'', str(e))


class MainWindow(QMainWindow):
    """主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("ImageGenPro - AI图像生成")
        self.setMinimumSize(1200, 800)

        # 加载配置
        self.config = config_manager.load_config()
        self.templates = config_manager.load_templates()

        # 当前生成的图片路径
        self.current_image_filename = ""

        # 生成线程
        self.worker = None

        self.setup_ui()
        self.apply_styles()
        self.load_config_to_ui()

    def setup_ui(self):
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧面板
        self.left_panel = LeftPanel()
        self.left_panel.setFixedWidth(400)
        self.left_panel.template_saved.connect(self.on_template_saved)
        self.left_panel.template_deleted.connect(self.on_template_deleted)
        self.left_panel.template_selected.connect(self.on_template_selected)
        self.left_panel.reference_images_changed.connect(self.on_reference_images_changed)
        main_layout.addWidget(self.left_panel)

        # 右侧面板
        self.right_panel = RightPanel()
        self.right_panel.generate_requested.connect(self.on_generate)
        self.right_panel.set_as_reference_requested.connect(self.on_set_as_reference)
        main_layout.addWidget(self.right_panel)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
        """)

    def load_config_to_ui(self):
        """加载配置到UI"""
        self.left_panel.set_api_key(self.config.api_key)
        self.left_panel.set_model(self.config.model)
        self.left_panel.set_save_conversation(self.config.save_conversation)
        self.left_panel.set_conversation_path(self.config.conversation_path)
        self.left_panel.set_aspect_ratio(self.config.aspect_ratio)
        self.left_panel.set_quality(self.config.quality)
        self.left_panel.set_filename(self.config.filename)
        self.left_panel.set_save_path(self.config.save_path)
        self.left_panel.set_api_url(self.config.api_url)
        self.left_panel.set_prompt(self.config.prompt)
        self.left_panel.load_templates(self.templates)

        # 恢复窗口大小
        if self.config.window_width > 0 and self.config.window_height > 0:
            self.resize(self.config.window_width, self.config.window_height)

    def save_ui_to_config(self):
        """保存UI状态到配置"""
        self.config.api_key = self.left_panel.get_api_key()
        self.config.model = self.left_panel.get_model()
        self.config.save_conversation = self.left_panel.get_save_conversation()
        self.config.conversation_path = self.left_panel.get_conversation_path()
        self.config.aspect_ratio = self.left_panel.get_aspect_ratio()
        self.config.quality = self.left_panel.get_quality()
        self.config.filename = self.left_panel.get_filename()
        self.config.save_path = self.left_panel.get_save_path()
        self.config.api_url = self.left_panel.get_api_url()
        self.config.prompt = self.left_panel.get_prompt()

        # 保存窗口大小
        self.config.window_width = self.width()
        self.config.window_height = self.height()

    def closeEvent(self, event):
        """关闭事件"""
        self.save_ui_to_config()
        config_manager.save_config(self.config)
        config_manager.save_templates(self.templates)
        event.accept()

    # ===== 槽函数 =====

    def on_template_saved(self, name: str, content: str):
        """模板保存"""
        self.templates[name] = content
        config_manager.save_templates(self.templates)

    def on_template_deleted(self, name: str):
        """模板删除"""
        if name in self.templates:
            del self.templates[name]
            config_manager.save_templates(self.templates)

    def on_template_selected(self, name: str):
        """模板选择"""
        if name in self.templates:
            self.left_panel.set_prompt(self.templates[name])

    def on_reference_images_changed(self, images: list):
        """参考图变化"""
        pass

    def on_set_as_reference(self):
        """将预览图设为参考图"""
        image_data = self.right_panel.get_current_image_data()
        if image_data:
            # 保存到临时文件
            temp_dir = Path.home() / ".imagegenpro" / "temp"
            temp_dir.mkdir(parents=True, exist_ok=True)
            temp_file = temp_dir / f"reference_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"

            try:
                with open(temp_file, 'wb') as f:
                    f.write(image_data)

                current_refs = self.left_panel.get_reference_images()
                current_refs.append(str(temp_file))
                self.left_panel.set_reference_images(current_refs)

                QMessageBox.information(self, "成功", "已将预览图添加到参考图列表")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"添加参考图失败: {str(e)}")

    def on_generate(self):
        """生成图片"""
        # 获取参数
        api_key = self.left_panel.get_api_key()
        api_url = self.left_panel.get_api_url()
        model = self.left_panel.get_model()
        prompt = self.left_panel.get_prompt()
        aspect_ratio = self.left_panel.get_aspect_ratio()
        quality = self.left_panel.get_quality()
        reference_images = self.left_panel.get_reference_images()

        # 验证
        if not api_key:
            QMessageBox.warning(self, "警告", "请输入授权码")
            return

        if not api_url:
            QMessageBox.warning(self, "警告", "请输入API网址")
            return

        if not prompt:
            QMessageBox.warning(self, "警告", "请输入提示词")
            return

        # 计算尺寸
        size = get_size_from_ratio(aspect_ratio, quality, model)

        # 创建API客户端
        client = ImageGenerationClient(api_url, api_key, model)

        # 清空预览
        self.right_panel.clear_preview()

        # 创建并启动工作线程
        self.worker = GenerationWorker(client, prompt, size, aspect_ratio, quality, reference_images)
        self.worker.progress.connect(self.on_generation_progress)
        self.worker.finished.connect(self.on_generation_finished)
        self.worker.start()

        self.right_panel.set_generating(True)
        self.right_panel.set_status("正在生成图片...")

    def on_generation_progress(self, message: str):
        """生成进度"""
        self.right_panel.set_status(message)

    def on_generation_finished(self, success: bool, image_data: bytes, error_message: str):
        """生成完成"""
        self.right_panel.set_generating(False)

        if success:
            self.right_panel.set_image(image_data)
            self.right_panel.set_status("生成完成")

            # 自动保存
            save_path = self.left_panel.get_save_path()
            filename = self.left_panel.get_filename()

            if save_path and os.path.isdir(save_path):
                if not filename:
                    filename = f"generated_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                if not filename.endswith(('.png', '.jpg', '.jpeg')):
                    filename += '.png'

                file_path = os.path.join(save_path, filename)
                try:
                    with open(file_path, 'wb') as f:
                        f.write(image_data)
                    self.right_panel.set_status(f"生成完成，已保存到: {file_path}")
                except Exception as e:
                    self.right_panel.set_status(f"生成完成，但保存失败: {str(e)}")
            else:
                self.right_panel.set_status("生成完成（未自动保存，请手动保存）")
        else:
            QMessageBox.critical(self, "生成失败", error_message)
            self.right_panel.set_status(f"生成失败: {error_message}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置应用样式
    app.setStyleSheet("""
        QToolTip {
            border: 1px solid #cccccc;
            background-color: #ffffe0;
            padding: 5px;
            border-radius: 3px;
        }
    """)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
