"""GUI 애플리케이션 시각적 테스트"""
import sys
import os
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import QTimer

# file_explorer 모듈 임포트
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'file_explorer'))

from explorer_widget import FileExplorerWidget

print("="*60)
print("PyQt6 파일 탐색기 - GUI 시각적 테스트")
print("="*60)
print("\n애플리케이션을 3초 동안 실행합니다...")
print("(headless 환경에서는 윈도우가 표시되지 않습니다)")
print()

app = QApplication(sys.argv)

# 메인 윈도우 생성
window = QMainWindow()
window.setWindowTitle("파일 탐색기 - 테스트")
window.setGeometry(100, 100, 900, 600)

# 파일 탐색기 위젯 추가
initial_path = os.getcwd()
try:
    explorer = FileExplorerWidget(initial_path)
    window.setCentralWidget(explorer)
    print("✓ FileExplorerWidget 생성 성공")
    print(f"✓ 초기 경로: {initial_path}")

    # 현재 경로의 파일 수 확인
    items_count = len(explorer.model._items)
    print(f"✓ 로드된 항목: {items_count}개")

except Exception as e:
    print(f"✗ 오류: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# 3초 후 자동 종료
timer = QTimer()
timer.timeout.connect(app.quit)
timer.start(3000)

# 윈도우 표시 (headless 환경에서는 표시되지 않음)
window.show()

# 이벤트 루프 실행
sys.exit(app.exec())
