"""파일 탐색기 애플리케이션 메인 엔트리포인트"""
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from .explorer_widget import FileExplorerWidget


def main():
    """애플리케이션을 실행한다."""
    app = QApplication(sys.argv)

    # 메인 윈도우 생성
    window = QMainWindow()
    window.setWindowTitle("파일 탐색기")
    window.setGeometry(100, 100, 900, 600)

    # 파일 탐색기 위젯 추가
    initial_path = os.getcwd()
    explorer = FileExplorerWidget(initial_path)
    window.setCentralWidget(explorer)

    # 윈도우 표시
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
