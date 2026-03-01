"""파일 탐색기 메인 위젯"""
import os
from pathlib import Path
from PyQt6.QtCore import Qt, QModelIndex, QSortFilterProxyModel, pyqtSignal
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTableView, QHeaderView
from .file_model import FileTableModel
from .navigation_bar import NavigationBar


def parse_path_with_pattern(input_path: str):
    """경로와 glob 패턴을 분리한다.

    예: "/home/user/*.py" -> ("/home/user", "*.py")
    예: "/home/user" -> ("/home/user", None)
    """
    # * 또는 ? 가 포함되어 있으면 glob 패턴으로 간주
    if '*' in input_path or '?' in input_path:
        # 마지막 경로 구분자를 찾아서 디렉토리와 패턴 분리
        last_sep_idx = input_path.rfind(os.sep)
        if last_sep_idx != -1:
            dir_path = input_path[:last_sep_idx]
            pattern = input_path[last_sep_idx + 1:]
            return dir_path, pattern
        else:
            # 구분자가 없으면 현재 디렉토리에서 패턴 적용
            return os.getcwd(), input_path

    return input_path, None


class FileExplorerWidget(QWidget):
    """파일 탐색기 메인 위젯"""

    # 파일 더블클릭 시 파일 경로를 전달하는 시그널
    fileDoubleClicked = pyqtSignal(str)

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

    def _on_path_changed(self, input_path: str):
        """사용자가 경로를 변경했을 때."""
        # 경로와 glob 패턴을 분리
        dir_path, glob_pattern = parse_path_with_pattern(input_path)

        # 절대 경로로 변환
        dir_path = os.path.abspath(dir_path)

        if os.path.isdir(dir_path):
            if glob_pattern:
                # glob 패턴이 있으면 경로와 패턴을 함께 전달
                self._navigate_with_pattern(dir_path, glob_pattern)
            else:
                # 일반 경로 네비게이션
                self.navigate_to(dir_path)

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
        else:
            # 파일: 시그널 발생
            self.fileDoubleClicked.emit(path)

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

    def _navigate_with_pattern(self, dir_path: str, glob_pattern: str):
        """glob 패턴과 함께 네비게이션을 처리한다."""
        # 주소 바에 전체 경로 + 패턴 표시
        display_path = os.path.join(dir_path, glob_pattern)
        self.nav_bar.update_path(display_path)
        self.nav_bar.set_back_enabled(False)
        self.nav_bar.set_forward_enabled(False)

        # 모델 로드 (glob 패턴 포함)
        self.model.load(dir_path, glob_pattern)

        # 정렬 다시 설정
        self.proxy_model.sort(-1, Qt.SortOrder.AscendingOrder)
