"""파일 탐색기 메인 위젯"""
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QModelIndex, QSortFilterProxyModel
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView
from file_model import FileTableModel
from navigation_bar import NavigationBar


class FileExplorerWidget(QWidget):
    """파일 탐색기 메인 위젯"""

    def __init__(self, initial_path: str = None, parent=None):
        super().__init__(parent)
        self._current_path = initial_path or os.getcwd()
        self._back_stack = []
        self._forward_stack = []

        self._setup_ui()
        self.navigate_to(self._current_path)

    def _setup_ui(self):
        """UI를 설정한다."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 네비게이션 바
        self.nav_bar = NavigationBar()
        self.nav_bar.path_changed.connect(self._on_path_changed)
        self.nav_bar.back_requested.connect(self._on_back)
        self.nav_bar.forward_requested.connect(self._on_forward)
        layout.addWidget(self.nav_bar)

        # 파일 모델
        self.model = FileTableModel()

        # 정렬 필터 프록시 모델
        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(False)  # 삽입 시 자동 재정렬 비활성화

        # 테이블 뷰
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QTableView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QTableView.SelectionMode.SingleSelection)
        self.table_view.verticalHeader().setDefaultSectionSize(24)  # 행 높이 설정
        self.table_view.setSortingEnabled(True)  # 헤더 클릭으로 정렬 활성화
        self.table_view.doubleClicked.connect(self._on_double_clicked)

        # 헤더 설정
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # 이름 컬럼은 Stretch
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)  # 나머지는 Fixed
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)

        header.setStretchLastSection(False)

        # 컬럼 너비 설정
        self.table_view.setColumnWidth(1, 100)  # 크기
        self.table_view.setColumnWidth(2, 80)  # 타입
        self.table_view.setColumnWidth(3, 150)  # 수정일시

        layout.addWidget(self.table_view)
        self.setLayout(layout)

    def _on_path_changed(self, path: str):
        """사용자가 경로를 변경했을 때."""
        if os.path.isdir(path):
            self.navigate_to(path)

    def _on_back(self):
        """뒤로가기."""
        if self._back_stack:
            self._forward_stack.append(self._current_path)
            path = self._back_stack.pop()
            self._navigate(path)

    def _on_forward(self):
        """앞으로가기."""
        if self._forward_stack:
            self._back_stack.append(self._current_path)
            path = self._forward_stack.pop()
            self._navigate(path)

    def _on_double_clicked(self, index: QModelIndex):
        """테이블 항목 더블클릭."""
        # 프록시 모델의 인덱스를 원본 모델 인덱스로 변환
        source_index = self.proxy_model.mapToSource(index)
        row = source_index.row()

        if row >= len(self.model._items):
            return

        item = self.model._items[row]
        path = item["path"]

        if item["is_dir"]:
            # 디렉토리: 진입
            self.navigate_to(path)

    def navigate_to(self, path: str):
        """경로로 이동한다."""
        path = os.path.abspath(path)

        if not os.path.isdir(path):
            return

        # 히스토리 처리
        if self._current_path and path != self._current_path:
            self._back_stack.append(self._current_path)
            self._forward_stack.clear()

        self._navigate(path)

    def _navigate(self, path: str):
        """실제 네비게이션 처리."""
        self._current_path = path
        self.nav_bar.update_path(path)
        self.nav_bar.set_back_enabled(len(self._back_stack) > 0)
        self.nav_bar.set_forward_enabled(len(self._forward_stack) > 0)

        # 모델 로드
        self.model.load(path)

        # 정렬 다시 설정
        self.proxy_model.sort(-1, Qt.SortOrder.AscendingOrder)
