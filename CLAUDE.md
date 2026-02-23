# PyQt6 File Explorer Widget

## 프로젝트 개요
현재 디렉토리의 파일과 폴더를 표시하는 PyQt6 기반 파일 탐색기 위젯을 개발한다. Windows Explorer / macOS Finder와 유사한 UX를 제공한다.

## 기술 스택
- Python 3.10+
- PyQt6 (pip install PyQt6)
- 표준 라이브러리: `os`, `pathlib`, `datetime`, `shutil`

## 핵심 요구사항

### 파일/디렉토리 목록 표시
- **`QTableView` + 커스텀 `QAbstractTableModel`**을 사용한다 (`QTreeView`를 사용하지 않는다).
- `os.scandir()`로 현재 디렉토리의 항목을 읽어서 모델 데이터를 구성한다.
- 표시 컬럼: 아이콘+이름, 크기, 타입, 수정일시
- **첫 번째 행에 `..` (상위 디렉토리) 항목을 항상 표시한다.** 루트 디렉토리가 아닌 한 항상 존재해야 한다.
- `..` 더블클릭 시 상위 디렉토리로 이동한다.
- 디렉토리는 항상 파일보다 위에 정렬한다 (정렬 순서: `..` → 디렉토리들 → 파일들).
- 숨김 파일은 기본적으로 숨기고 토글 옵션을 제공한다.

### 성능 최적화 (필수 — 수만 개 이상의 항목 대응)
디렉토리에 파일/폴더가 수만~수십만 개일 때도 UI가 멈추지 않아야 한다.

#### 백그라운드 로딩 (QThread)
- 파일 목록 스캔은 **반드시 `QThread` 워커**에서 수행한다. 메인(GUI) 스레드에서 `os.scandir()`을 직접 호출하지 않는다.
- 워커 클래스: `DirectoryLoader(QThread)` — `file_model.py` 또는 별도 `loader.py`에 둔다.
- 워커가 스캔 완료 후 결과 리스트를 시그널(`finished(list)`)로 메인 스레드에 전달한다.
- 메인 스레드에서 `beginResetModel()` / `endResetModel()`로 모델을 갱신한다.
- 디렉토리 이동 시 이전 로딩이 진행 중이면 **취소**하고 새 로딩을 시작한다.

#### 점진적 로딩 (Chunked Insert)
- 항목이 매우 많을 경우(예: 10,000개 초과), 한 번에 전체를 모델에 넣지 않고 **청크 단위(예: 500~1000개씩)**로 `beginInsertRows()` / `endInsertRows()`를 호출하여 점진적으로 삽입한다.
- 이렇게 하면 첫 화면이 빠르게 표시되고 나머지가 백그라운드에서 추가된다.

#### stat() 호출 최소화
- `os.scandir()`의 `DirEntry` 객체는 `.is_dir()`, `.is_file()`, `.stat()`를 캐시한다. **`DirEntry`를 직접 활용**하고 별도로 `os.stat()`을 다시 호출하지 않는다.
- `DirEntry.stat(follow_symlinks=False)`로 심볼릭 링크 추적을 피한다.
- stat 실패 시(권한 없음 등) 예외를 잡아서 크기/수정일시를 "—"으로 표시한다.

#### 아이콘 캐싱
- `QFileIconProvider`를 매 행마다 호출하면 느리다. **확장자별 아이콘 캐시(`dict[str, QIcon]`)**를 유지한다.
- 디렉토리 아이콘과 기본 파일 아이콘은 한 번만 로드하여 재사용한다.
- 캐시 키: 디렉토리 → `"__dir__"`, 파일 → 소문자 확장자(예: `".py"`, `".txt"`), 확장자 없음 → `"__file__"`.

#### QTableView 렌더링 최적화
- `QTableView.setUniformRowHeights(True)` — 모든 행 높이가 같으면 뷰가 각 행의 높이를 개별 계산하지 않아 대폭 빨라진다. **반드시 설정한다.**
- `QHeaderView.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)` 또는 `Interactive`를 사용하고, `ResizeToContents`는 사용하지 않는다 (전체 데이터를 순회하므로 느림). 초기 컬럼 너비는 코드에서 수동 설정한다.
- 정렬 시 `QSortFilterProxyModel.setDynamicSortFilter(False)`로 설정하여 삽입마다 자동 재정렬되지 않도록 한다. 전체 로딩 완료 후 한 번만 정렬한다.

### 아이콘 표시
- `QFileIconProvider`를 사용하여 파일/디렉토리의 시스템 기본 아이콘을 가져온다.
- 모델의 `data()` 메서드에서 `Qt.ItemDataRole.DecorationRole`로 아이콘을 반환한다.
- **이름 컬럼(첫 번째 컬럼)에만** 아이콘을 표시한다.
- `..` 항목은 디렉토리 아이콘을 사용한다.

### 네비게이션
- 디렉토리 더블클릭 시 해당 디렉토리로 진입한다.
- 파일 더블클릭 시 OS 기본 프로그램으로 연다 (`QDesktopServices.openUrl()`).
- 상단에 현재 경로를 표시하는 주소 바(QLineEdit)를 둔다.
- 뒤로가기/앞으로가기 버튼을 제공한다 (히스토리 스택 관리).
- 주소 바에 직접 경로를 입력하면 해당 경로로 이동한다.

### QTableView 설정
- `setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)` — 행 단위 선택.
- `setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)` — 단일 선택.
- **`setUniformRowHeights(True)`** — 필수. 대량 항목 시 렌더링 성능에 결정적.
- 헤더 클릭으로 컬럼별 정렬을 지원한다 (`QSortFilterProxyModel` 사용, `dynamicSortFilter=False`).
- 이름 컬럼은 `Stretch`, 나머지 컬럼은 `Fixed` 또는 `Interactive`로 설정한다. **`ResizeToContents`는 사용 금지** (전체 데이터 순회로 느림).
- 행 높이는 아이콘이 잘 보이도록 적절히 설정한다 (24~28px).

## 프로젝트 구조

```
file_explorer/
├── main.py              # 앱 엔트리포인트, QApplication 생성 및 실행
├── explorer_widget.py   # FileExplorerWidget 클래스 (메인 위젯)
├── file_model.py        # FileTableModel(QAbstractTableModel) 커스텀 모델
├── loader.py            # DirectoryLoader(QThread) 백그라운드 스캔 워커
├── navigation_bar.py    # NavigationBar 클래스 (주소 바 + 네비게이션 버튼)
└── README.md
```

## 클래스 설계

### `DirectoryLoader(QThread)` — loader.py
- `__init__(path: str)` — 스캔할 디렉토리 경로를 받는다.
- `run()` — `os.scandir()`으로 항목을 읽어 `list[dict]`를 구성한다. `DirEntry.stat(follow_symlinks=False)`를 사용하여 stat 정보를 한 번에 가져온다. stat 실패 시 예외를 잡아 기본값("—")을 넣는다.
- 시그널: `chunk_ready(list)` — 청크(500~1000개) 단위로 중간 결과 전달, `finished(list)` — 전체 완료.
- `cancel()` 메서드 — 내부 플래그(`_cancelled`)를 설정하여 루프를 조기 종료한다. `run()` 내에서 매 항목마다 이 플래그를 체크한다.

### `FileTableModel(QAbstractTableModel)` — file_model.py
- `load(path: str)` — `DirectoryLoader`를 시작한다. 이전 로더가 실행 중이면 `cancel()` 후 새로 시작한다.
- 내부 데이터 구조: `list[dict]` — 각 dict는 `{"name", "path", "is_dir", "size", "modified"}`.
- **아이콘은 `data()` 호출 시 확장자별 캐시에서 조회**한다. 모델 데이터에 아이콘을 저장하지 않는다.
- `..` 항목을 리스트 맨 앞에 수동으로 삽입한다 (루트가 아닐 때).
- 정렬: `..` 고정 맨 위 → 디렉토리(이름순) → 파일(이름순).
- `data()` 구현:
  - `DisplayRole`: 이름, 크기(사람이 읽기 쉬운 형태), 타입("디렉토리"/"파일"), 수정일시
  - `DecorationRole`: 이름 컬럼(col 0)에서만 캐시된 `QIcon` 반환
- `rowCount()`, `columnCount()`, `headerData()` 구현.
- 청크 삽입: `chunk_ready` 시그널에 연결하여 `beginInsertRows()`/`endInsertRows()`로 점진적으로 추가한다.

### `FileExplorerWidget(QWidget)` — explorer_widget.py
- 메인 위젯. NavigationBar와 QTableView를 수직 배치(QVBoxLayout).
- `FileTableModel`을 생성하고 `QSortFilterProxyModel`을 거쳐 `QTableView`에 연결한다.
- `navigate_to(path: str)` 메서드로 경로 이동을 처리한다.
- 더블클릭 시그널(`doubleClicked`)을 연결:
  - `..` → 상위 디렉토리로 이동
  - 디렉토리 → 해당 디렉토리로 진입
  - 파일 → OS 기본 프로그램으로 열기
- 히스토리 스택(back_stack, forward_stack)을 관리한다.

### `NavigationBar(QWidget)` — navigation_bar.py
- 뒤로/앞으로 버튼 + 경로 입력 QLineEdit로 구성한다.
- 시그널: `path_changed(str)`, `back_requested()`, `forward_requested()`

### `main.py`
- `QApplication` 생성, `FileExplorerWidget` 인스턴스를 `QMainWindow`에 배치, 실행한다.
- 초기 경로: 현재 작업 디렉토리 (`os.getcwd()`)
- 창 크기: 900x600

## 코딩 규칙
- 타입 힌트를 사용한다.
- 시그널/슬롯 연결은 `connect()` 메서드를 사용한다.
- PyQt6에서는 `exec_()` 대신 `exec()`를 사용한다.
- Enum 접근 시 `Qt.ItemDataRole.DisplayRole` 같은 full qualified 형태를 사용한다 (PyQt6 방식).
- 파일 크기는 사람이 읽기 쉬운 형태(KB, MB, GB)로 표시한다.
- `..` 항목의 크기/타입/수정일시 컬럼은 빈 문자열로 표시한다.

## 실행 방법
```bash
cd file_explorer
python main.py
```