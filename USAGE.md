# PyQt6 파일 탐색기 위젯 - 사용 가이드

## 📦 단일 파일 모듈

`file_explorer_single.py` 하나의 파일로 모든 기능을 제공합니다.

## 🚀 설치

### 1. 파일 복사
`file_explorer_single.py`를 프로젝트에 복사하세요.

```
your_project/
├── file_explorer_single.py   ← 여기에 복사
├── your_app.py
└── ...
```

### 2. 의존성
```bash
pip install PyQt6
```

## 💻 기본 사용법

### 간단한 예제
```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from file_explorer_single import FileExplorerWidget

app = QApplication(sys.argv)
window = QMainWindow()
window.setWindowTitle("파일 탐색기")
window.setGeometry(100, 100, 900, 600)

# 파일 탐색기 위젯 생성
explorer = FileExplorerWidget("/home/user/documents")
window.setCentralWidget(explorer)
window.show()

sys.exit(app.exec())
```

### 현재 디렉토리부터 시작
```python
explorer = FileExplorerWidget()  # os.getcwd() 사용
```

### 특정 경로부터 시작
```python
explorer = FileExplorerWidget("/path/to/directory")
```

## 🎯 주요 기능

### 1. 디렉토리 네비게이션
- **더블클릭**: 디렉토리 진입
- **".." 항목**: 상위 폴더로 이동
- **뒤로/앞으로**: 히스토리 네비게이션
- **주소 바**: 경로 직접 입력

### 2. 파일 정보 표시
- **이름**: 아이콘 포함
- **크기**: 사람이 읽기 쉬운 형식 (B, KB, MB, GB)
- **타입**: 디렉토리 또는 파일
- **수정일시**: YYYY-MM-DD HH:MM:SS 형식

### 3. 정렬
- **헤더 클릭**: 컬럼별 정렬
- **기본 정렬**: .. → 디렉토리 → 파일 (이름순)

## 📚 클래스 구조

### FileExplorerWidget
메인 위젯 클래스
```python
class FileExplorerWidget(QWidget):
    def __init__(self, initial_path: str = None, parent=None)
    def navigate_to(self, path: str)  # 경로 이동
```

### FileTableModel
테이블 데이터 모델 (내부 사용)
```python
class FileTableModel(QAbstractTableModel)
```

### NavigationBar
네비게이션 바 위젯 (내부 사용)
```python
class NavigationBar(QWidget)
```

### DirectoryLoader
백그라운드 로딩 워커 (내부 사용)
```python
class DirectoryLoader(QThread)
```

## ⚙️ 성능 특성

- ✅ 수만 개 이상의 파일 효율적 처리
- ✅ 백그라운드 로딩 (UI 응답성 보장)
- ✅ 점진적 로딩 (청크 단위)
- ✅ 아이콘 캐싱 (성능 최적화)

## 🎨 커스터마이징

### 초기 경로 설정
```python
explorer = FileExplorerWidget("/home/user")
```

### 부모 위젯 지정
```python
explorer = FileExplorerWidget(parent=your_widget)
```

### 내부 테이블 뷰 접근
```python
table_view = explorer.table_view
# 예: 컬럼 숨기기
table_view.hideColumn(2)
```

### 네비게이션 바 커스터마이징
```python
nav_bar = explorer.nav_bar
nav_bar.set_back_enabled(False)  # 뒤로가기 버튼 비활성화
```

## 📝 예제: 통합 예제

```python
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton
from file_explorer_single import FileExplorerWidget

class MyApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("파일 관리자")
        self.setGeometry(100, 100, 1000, 700)

        # 메인 위젯
        main_widget = QWidget()
        layout = QVBoxLayout()

        # 파일 탐색기
        self.explorer = FileExplorerWidget("/home")
        layout.addWidget(self.explorer)

        # 버튼
        btn = QPushButton("현재 경로 출력")
        btn.clicked.connect(self.print_path)
        layout.addWidget(btn)

        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

    def print_path(self):
        print(f"현재 경로: {self.explorer._current_path}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MyApp()
    window.show()
    sys.exit(app.exec())
```

## 🐛 문제 해결

### Qt 플러그인 경고
무시해도 됩니다. 기능에 영향 없음.

### 경로 접근 오류
- 권한이 없는 폴더는 자동으로 처리됨 (크기/수정일시 = "—")
- 존재하지 않는 경로는 무시됨

## 📄 라이센스

이 코드는 자유롭게 사용 및 수정할 수 있습니다.

## 📧 지원

문제 발생 시 코드 검토를 해주세요.
