"""백그라운드 디렉토리 스캔 워커 (QThread)"""
import os
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal


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
