"""
PyQt6 파일 탐색기 위젯 - 단일 파일 버전
스탠드얼론으로 사용 가능한 파일 탐색기 위젯
"""

import os
from datetime import datetime
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo, QThread, pyqtSignal, QUrl, QSortFilterProxyModel
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTableView, QHeaderView, QApplication, QMainWindow, QFileIconProvider
)


class DirectoryLoader(QThread):
    """백그라운드에서 디렉토리 항목을 스캔하는 QThread 워커"""

    chunk_ready = pyqtSignal(list)  # 청크 단위 결과 전달
    finished = pyqtSignal(list)  # 전체 완료

    def __init__(self, path: str):
        super().__init__()
        self.path = path
        self._cancelled = False
        self._chunk_size = 500  # 청크 크기

    def run(self):
        """디렉토리를 스캔하고 항목 정보를 수집한다."""
        try:
            items = []
            chunk = []

            with os.scandir(self.path) as entries:
                for entry in entries:
                    # 취소 플래그 확인
                    if self._cancelled:
                        return

                    try:
                        # stat 정보 한 번에 가져오기
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
                        "is_dir": entry.is_dir(follow_symlinks=False),
                        "is_file": entry.is_file(follow_symlinks=False),
                        "size": size,
                        "modified": modified,
                    }

                    chunk.append(item_dict)
                    items.append(item_dict)

                    # 청크 크기에 도달하면 신호 발송
                    if len(chunk) >= self._chunk_size:
                        self.chunk_ready.emit(chunk)
                        chunk = []

            # 남은 청크 전송
            if chunk and not self._cancelled:
                self.chunk_ready.emit(chunk)

            # 전체 완료 신호
            if not self._cancelled:
                self.finished.emit(items)

        except Exception as e:
            print(f"디렉토리 스캔 오류: {e}")
            self.finished.emit([])

    def cancel(self):
        """로딩을 취소한다."""
        self._cancelled = True
        self.wait()


class FileTableModel(QAbstractTableModel):
    """파일/디렉토리 목록을 표시하는 커스텀 테이블 모델"""

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

    def load(self, path: str):
        """경로의 항목을 로드한다."""
        self._current_path = path

        # 이전 로더가 실행 중이면 취소
        if self._loader is not None:
            self._loader.cancel()

        # 모델 초기화
        self.beginResetModel()
        self._items = []
        self.endResetModel()

        # .. 항목을 미리 추가 (루트가 아닐 경우)
        parent_dir = os.path.dirname(path)
        if parent_dir and parent_dir != path:
            parent_item = {
                "name": "..",
                "path": parent_dir,
                "is_dir": True,
                "is_file": False,
                "size": None,
                "modified": None,
            }
            self.beginInsertRows(QModelIndex(), 0, 0)
            self._items.append(parent_item)
            self.endInsertRows()

        # 새로운 로더 생성
        self._loader = DirectoryLoader(path)
        self._loader.chunk_ready.connect(self._on_chunk_ready)
        self._loader.finished.connect(self._on_finished)
        self._loader.start()

    def _on_chunk_ready(self, chunk: list):
        """청크 단위 결과를 받아 모델에 추가한다."""
        # 이미 항목이 있는 경우 시작 위치 계산
        start_row = len(self._items)
        end_row = start_row + len(chunk) - 1

        self.beginInsertRows(QModelIndex(), start_row, end_row)
        self._items.extend(chunk)
        self.endInsertRows()

    def _on_finished(self, all_items: list):
        """전체 로딩이 완료되었다."""
        # 청크로 이미 추가된 항목이 없으면 전체를 한 번에 추가
        if not self._items:
            self.beginResetModel()
            self._items = all_items
            self.endResetModel()

        # 정렬: .. → 디렉토리 → 파일
        self._sort_items()

    def _sort_items(self):
        """항목을 정렬한다: .. → 디렉토리(이름순) → 파일(이름순)"""
        parent_item = None
        directories = []
        files = []

        for item in self._items:
            if item["name"] == "..":
                parent_item = item
            elif item["is_dir"]:
                directories.append(item)
            else:
                files.append(item)

        # 각각 이름순으로 정렬
        directories.sort(key=lambda x: x["name"].lower())
        files.sort(key=lambda x: x["name"].lower())

        # 재조립
        self.beginResetModel()
        self._items = []
        if parent_item:
            self._items.append(parent_item)
        self._items.extend(directories)
        self._items.extend(files)
        self.endResetModel()

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

    def _format_size(self, size: int | None) -> str:
        """파일 크기를 사람이 읽기 쉬운 형태로 변환한다."""
        if size is None:
            return "—"

        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024

        return "—"

    def _format_modified(self, timestamp: float | None) -> str:
        """수정 시간을 포맷팅한다."""
        if timestamp is None:
            return "—"

        try:
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return "—"

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
                return self._format_size(item["size"])
            elif col == self.COLUMN_TYPE:
                # .. 항목은 타입 표시 안 함
                if item["name"] == "..":
                    return ""
                return "디렉토리" if item["is_dir"] else "파일"
            elif col == self.COLUMN_MODIFIED:
                # .. 항목은 수정일시 표시 안 함
                if item["name"] == "..":
                    return ""
                return self._format_modified(item["modified"])

        elif role == Qt.ItemDataRole.DecorationRole:
            # 첫 번째 컬럼에만 아이콘 표시
            if index.column() == self.COLUMN_NAME:
                return self._get_icon(item)

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
        self.back_btn.setMaximumWidth(50)
        self.back_btn.clicked.connect(self.back_requested.emit)
        layout.addWidget(self.back_btn)

        # 앞으로가기 버튼
        self.forward_btn = QPushButton("►")
        self.forward_btn.setMaximumWidth(50)
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


# 스탠드얼론 실행용
if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = QMainWindow()
    window.setWindowTitle("파일 탐색기")
    window.setGeometry(100, 100, 900, 600)

    explorer = FileExplorerWidget()
    window.setCentralWidget(explorer)
    window.show()

    sys.exit(app.exec())
