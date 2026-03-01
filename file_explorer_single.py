"""
PyQt6 파일 탐색기 위젯 - 단일 파일 버전
스탠드얼론으로 사용 가능한 파일 탐색기 위젯
glob 패턴 필터링 기능 지원
"""

import os
import sys
import fnmatch
import re
from datetime import datetime
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo, QThread, pyqtSignal, QSortFilterProxyModel
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableView, QHeaderView, QApplication, QMainWindow, QFileIconProvider, QAbstractItemView
)


class DirectoryLoader(QThread):
    """백그라운드에서 디렉토리 항목을 스캔하는 QThread 워커"""

    chunk_ready = pyqtSignal(list)  # 청크 단위 결과 전달
    finished = pyqtSignal()  # 전체 완료

    def __init__(self, path: str, glob_pattern: str = None, parent=None):
        super().__init__(parent)
        self.path = path
        self.glob_pattern = glob_pattern  # glob 필터 패턴
        self._cancelled = False
        self._chunk_size = 500  # 청크 크기
        self._glob_matcher = None
        if glob_pattern:
            self._glob_matcher = re.compile(fnmatch.translate(glob_pattern)).match

    def run(self):
        """디렉토리를 스캔하고 항목 정보를 수집한다."""
        try:
            chunk = []

            with os.scandir(self.path) as entries:
                for entry in entries:
                    # 취소 플래그 확인
                    if self._cancelled or self.isInterruptionRequested():
                        return

                    # glob 패턴이 지정된 경우 필터링
                    if self._glob_matcher and not self._glob_matcher(entry.name):
                        continue

                    is_dir = entry.is_dir(follow_symlinks=False)
                    if is_dir:
                        # 디렉토리는 stat 비용을 줄이기 위해 메타데이터를 지연/생략
                        size = None
                        modified = None
                    else:
                        try:
                            # 파일에 대해서만 stat 수행
                            stat_info = entry.stat(follow_symlinks=False)
                            size = stat_info.st_size
                            modified = stat_info.st_mtime
                        except (OSError, PermissionError):
                            # 권한 없음 등의 오류 처리
                            size = None
                            modified = None

                    item_dict = {
                        "name": entry.name,
                        "path": entry.path,
                        "is_dir": is_dir,
                        "size": size,
                        "modified": modified,
                        "display_size": self._format_size(size),
                        "display_modified": self._format_modified(modified),
                    }

                    chunk.append(item_dict)

                    # 청크 크기에 도달하면 신호 발송
                    if len(chunk) >= self._chunk_size:
                        self.chunk_ready.emit(chunk)
                        chunk = []

            # 남은 청크 전송
            if chunk and not self._cancelled:
                self.chunk_ready.emit(chunk)

            # 전체 완료 신호
            if not self._cancelled:
                self.finished.emit()

        except Exception as e:
            print(f"디렉토리 스캔 오류: {e}")
            self.finished.emit()

    def cancel(self):
        """로딩을 취소한다."""
        self._cancelled = True
        self.requestInterruption()

    @staticmethod
    def _format_size(size: int | None) -> str:
        """파일 크기를 사람이 읽기 쉬운 형태로 변환한다."""
        if size is None:
            return "—"

        size_float = float(size)
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size_float < 1024:
                return f"{size_float:.1f} {unit}"
            size_float /= 1024

        return "—"

    @staticmethod
    def _format_modified(timestamp: float | None) -> str:
        """수정 시간을 포맷팅한다."""
        if timestamp is None:
            return "—"

        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "—"


class FileTableModel(QAbstractTableModel):
    """파일/디렉토리 목록을 표시하는 커스텀 테이블 모델"""
    loading_finished = pyqtSignal()

    # 컬럼 정의
    COLUMN_NAME = 0
    COLUMN_SIZE = 1
    COLUMN_TYPE = 2
    COLUMN_MODIFIED = 3
    COLUMN_COUNT = 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []  # 항목 데이터
        self._current_path = ""  # 현재 경로
        self._loader = None  # 현재 실행 중인 로더
        self._icon_cache = {}  # 확장자별 아이콘 캐시
        self._file_icon_provider = QFileIconProvider()

        # 기본 아이콘 미리 로드
        self._init_default_icons()

    def _init_default_icons(self):
        """기본 아이콘을 초기화한다."""
        try:
            dir_info = QFileInfo("/")
            self._icon_cache["__dir__"] = self._file_icon_provider.icon(dir_info)

            # 파일 아이콘은 시스템 기본 파일 아이콘 사용
            file_info = QFileInfo(__file__)
            self._icon_cache["__file__"] = self._file_icon_provider.icon(file_info)
        except Exception:
            # 아이콘 로드 실패 시 빈 아이콘 사용
            self._icon_cache["__dir__"] = QIcon()
            self._icon_cache["__file__"] = QIcon()

    def load(self, path: str, glob_pattern: str = None):
        """경로의 항목을 로드한다."""
        self._current_path = path

        # 이전 로더가 실행 중이면 취소
        self.stop_loading()

        # 모델 초기화
        self.beginResetModel()
        self._items = []
        self.endResetModel()

        # .. 항목을 미리 추가 (루트가 아닐 경우, glob 필터가 없을 때만)
        parent_dir = os.path.dirname(path)
        if not glob_pattern and parent_dir and parent_dir != path:
            parent_item = self._create_parent_item(parent_dir)
            self.beginInsertRows(QModelIndex(), 0, 0)
            self._items.append(parent_item)
            self.endInsertRows()

        # 새로운 로더 생성
        self._loader = DirectoryLoader(path, glob_pattern, self)
        self._loader.chunk_ready.connect(self._on_chunk_ready)
        self._loader.finished.connect(self._on_finished)
        self._loader.finished.connect(self._loader.deleteLater)
        self._loader.start()

    def _on_chunk_ready(self, chunk: list):
        """청크 단위 결과를 받아 모델에 추가한다."""
        if self.sender() is not self._loader:
            return
        if not chunk:
            return

        # 이미 항목이 있는 경우 시작 위치 계산
        start_row = len(self._items)
        end_row = start_row + len(chunk) - 1

        self.beginInsertRows(QModelIndex(), start_row, end_row)
        self._items.extend(chunk)
        self.endInsertRows()

    def _on_finished(self):
        """전체 로딩이 완료되었다."""
        if self.sender() is not self._loader:
            return

        self._loader = None
        self.loading_finished.emit()

    def stop_loading(self):
        """실행 중인 로더가 있으면 정지 요청한다."""
        if self._loader is not None:
            self._loader.cancel()

    @staticmethod
    def _create_parent_item(parent_dir: str) -> dict:
        """상위 디렉토리(..) 항목을 생성한다."""
        return {
            "name": "..",
            "path": parent_dir,
            "is_dir": True,
            "size": None,
            "modified": None,
            "display_size": "",
            "display_modified": "",
        }

    def _get_icon(self, item: dict) -> QIcon:
        """항목의 아이콘을 반환한다 (캐시 활용)."""
        if item["is_dir"]:
            return self._icon_cache.get("__dir__", QIcon())

        # 확장자 기반 캐시 조회
        ext = os.path.splitext(item["name"])[1].lower() if item["name"] != ".." else ""

        if not ext:
            ext = "__file__"

        if ext not in self._icon_cache:
            # 캐시에 없으면 QFileInfo로 로드
            try:
                file_info = QFileInfo(item["path"])
                self._icon_cache[ext] = self._file_icon_provider.icon(file_info)
            except Exception:
                self._icon_cache[ext] = self._icon_cache.get("__file__", QIcon())

        return self._icon_cache.get(ext, QIcon())

    def rowCount(self, parent=QModelIndex()) -> int:
        """행 개수."""
        return len(self._items)

    def columnCount(self, parent=QModelIndex()) -> int:
        """컬럼 개수."""
        return self.COLUMN_COUNT

    def data(self, index: QModelIndex, role: int):
        """셀 데이터를 반환한다."""
        if not index.isValid() or index.row() >= len(self._items):
            return None

        item = self._items[index.row()]

        if role == Qt.ItemDataRole.DisplayRole:
            col = index.column()
            if col == self.COLUMN_NAME:
                return item["name"]
            elif col == self.COLUMN_SIZE:
                # .. 항목은 크기 표시 안 함
                if item["name"] == "..":
                    return ""
                return item.get("display_size", DirectoryLoader._format_size(item["size"]))
            elif col == self.COLUMN_TYPE:
                # .. 항목은 타입 표시 안 함
                if item["name"] == "..":
                    return ""
                return "디렉토리" if item["is_dir"] else "파일"
            elif col == self.COLUMN_MODIFIED:
                # .. 항목은 수정일시 표시 안 함
                if item["name"] == "..":
                    return ""
                return item.get("display_modified", DirectoryLoader._format_modified(item["modified"]))

        elif role == Qt.ItemDataRole.DecorationRole:
            # 첫 번째 컬럼에만 아이콘 표시
            if index.column() == self.COLUMN_NAME:
                return self._get_icon(item)
        elif role == Qt.ItemDataRole.UserRole:
            return item

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        """헤더 데이터."""
        if role == Qt.ItemDataRole.DisplayRole:
            if orientation == Qt.Orientation.Horizontal:
                if section == self.COLUMN_NAME:
                    return "이름"
                elif section == self.COLUMN_SIZE:
                    return "크기"
                elif section == self.COLUMN_TYPE:
                    return "타입"
                elif section == self.COLUMN_MODIFIED:
                    return "수정일시"

        return None


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


class ExplorerSortProxyModel(QSortFilterProxyModel):
    """파일 탐색기 정렬 규칙(.. 우선, 디렉토리 우선)을 적용하는 프록시 모델"""

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        left_item = left.data(Qt.ItemDataRole.UserRole)
        right_item = right.data(Qt.ItemDataRole.UserRole)

        if not isinstance(left_item, dict) or not isinstance(right_item, dict):
            return super().lessThan(left, right)

        left_name = left_item.get("name", "")
        right_name = right_item.get("name", "")

        # 상위 디렉토리(..)는 항상 최상단
        if left_name == ".." and right_name != "..":
            return True
        if right_name == ".." and left_name != "..":
            return False

        # 디렉토리를 파일보다 우선 배치
        left_is_dir = bool(left_item.get("is_dir"))
        right_is_dir = bool(right_item.get("is_dir"))
        if left_is_dir != right_is_dir:
            return left_is_dir

        col = left.column()
        if col == FileTableModel.COLUMN_SIZE:
            left_size = left_item.get("size")
            right_size = right_item.get("size")
            left_size = -1 if left_size is None else left_size
            right_size = -1 if right_size is None else right_size
            return left_size < right_size

        if col == FileTableModel.COLUMN_MODIFIED:
            left_modified = left_item.get("modified")
            right_modified = right_item.get("modified")
            left_modified = -1 if left_modified is None else left_modified
            right_modified = -1 if right_modified is None else right_modified
            return left_modified < right_modified

        left_text = str(left.data(Qt.ItemDataRole.DisplayRole) or "").lower()
        right_text = str(right.data(Qt.ItemDataRole.DisplayRole) or "").lower()
        return left_text < right_text


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
        self.proxy_model = ExplorerSortProxyModel()
        self.proxy_model.setSourceModel(self.model)
        self.proxy_model.setDynamicSortFilter(False)  # 삽입 시 자동 재정렬 비활성화
        self.model.loading_finished.connect(self._resort_proxy)

        # 테이블 뷰
        self.table_view = QTableView()
        self.table_view.setModel(self.proxy_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table_view.verticalHeader().setDefaultSectionSize(24)  # 행 높이 설정
        self.table_view.setSortingEnabled(True)  # 헤더 클릭으로 정렬 활성화
        self.table_view.sortByColumn(FileTableModel.COLUMN_NAME, Qt.SortOrder.AscendingOrder)
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
        self._apply_navigation_state(path)

        # 모델 로드
        self.model.load(path)

    def _apply_navigation_state(self, path: str):
        """현재 경로와 네비게이션 버튼 상태를 반영한다."""
        self._current_path = path
        self.nav_bar.update_path(path)
        self.nav_bar.set_back_enabled(len(self._back_stack) > 0)
        self.nav_bar.set_forward_enabled(len(self._forward_stack) > 0)

    def _navigate_with_pattern(self, dir_path: str, glob_pattern: str):
        """glob 패턴과 함께 네비게이션을 처리한다."""
        # 주소 바에 전체 경로 + 패턴 표시
        display_path = os.path.join(dir_path, glob_pattern)
        self._current_path = dir_path
        self.nav_bar.update_path(display_path)
        self.nav_bar.set_back_enabled(False)
        self.nav_bar.set_forward_enabled(False)

        # 모델 로드 (glob 패턴 포함)
        self.model.load(dir_path, glob_pattern)

    def _resort_proxy(self):
        """모델 로딩 완료 시 현재 헤더 기준으로 정렬을 적용한다."""
        header = self.table_view.horizontalHeader()
        section = header.sortIndicatorSection()
        order = header.sortIndicatorOrder()
        if section < 0:
            section = FileTableModel.COLUMN_NAME
            order = Qt.SortOrder.AscendingOrder
        self.proxy_model.sort(section, order)

    def closeEvent(self, event):
        """위젯 종료 시 백그라운드 로더를 정리한다."""
        self.model.stop_loading()
        super().closeEvent(event)


# 스탠드얼론 실행용
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("파일 탐색기")
    window.setGeometry(100, 100, 900, 600)

    explorer = FileExplorerWidget()
    window.setCentralWidget(explorer)
    window.show()

    sys.exit(app.exec())
