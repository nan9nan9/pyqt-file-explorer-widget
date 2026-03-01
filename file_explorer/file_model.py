"""파일 탐색기 테이블 모델"""
import os
from datetime import datetime
from pathlib import Path
from PyQt6.QtCore import Qt, QAbstractTableModel, QModelIndex, QFileInfo
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import QFileIconProvider
from .loader import DirectoryLoader


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

    def load(self, path: str, glob_pattern: str = None):
        """경로의 항목을 로드한다."""
        self._current_path = path

        # 이전 로더가 실행 중이면 취소
        if self._loader is not None:
            self._loader.cancel()

        # 모델 초기화
        self.beginResetModel()
        self._items = []
        self.endResetModel()

        # .. 항목을 미리 추가 (루트가 아닐 경우, glob 필터가 없을 때만)
        parent_dir = os.path.dirname(path)
        if not glob_pattern and parent_dir and parent_dir != path:
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
        self._loader = DirectoryLoader(path, glob_pattern)
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
