"""네비게이션 바 - 뒤로/앞으로 버튼 + 경로 입력 필드"""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit


class NavigationBar(QWidget):
    """네비게이션 바 위젯"""

    path_changed = pyqtSignal(str)  # 사용자가 경로를 변경했을 때
    back_requested = pyqtSignal()  # 뒤로가기 요청
    forward_requested = pyqtSignal()  # 앞으로가기 요청

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        """UI를 설정한다."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # 뒤로가기 버튼
        self.back_btn = QPushButton("◄")
        self.back_btn.setFixedWidth(24)
        self.back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(self.back_btn)

        # 앞으로가기 버튼
        self.forward_btn = QPushButton("►")
        self.forward_btn.setFixedWidth(24)
        self.forward_btn.clicked.connect(self.forward_requested.emit)
        layout.addWidget(self.forward_btn)

        # 경로 입력 필드
        self.path_input = QLineEdit()
        self.path_input.setPlaceholderText("경로를 입력하세요...")
        self.path_input.returnPressed.connect(self._on_path_input)
        layout.addWidget(self.path_input)

        self.setLayout(layout)

    def _on_path_input(self):
        """사용자가 경로를 입력했을 때."""
        path = self.path_input.text().strip()
        if path:
            self.path_changed.emit(path)

    def update_path(self, path: str):
        """현재 경로를 표시한다."""
        self.path_input.setText(path)

    def set_back_enabled(self, enabled: bool):
        """뒤로가기 버튼 활성화 상태를 설정한다."""
        self.back_btn.setEnabled(enabled)

    def set_forward_enabled(self, enabled: bool):
        """앞으로가기 버튼 활성화 상태를 설정한다."""
        self.forward_btn.setEnabled(enabled)
