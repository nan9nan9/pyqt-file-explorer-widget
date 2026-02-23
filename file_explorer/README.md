# PyQt6 파일 탐색기 위젯

Windows Explorer / macOS Finder와 유사한 UX를 제공하는 PyQt6 기반 파일 탐색기 위젯입니다.

## 기능

- **파일/디렉토리 목록 표시**: `QTableView` + 커스텀 `QAbstractTableModel`
- **아이콘 표시**: 시스템 기본 아이콘 자동 로드 (확장자별 캐싱)
- **네비게이션**: 뒤로/앞으로 버튼, 경로 주소 바
- **성능 최적화**: 수만 개 이상의 항목을 효율적으로 처리
  - 백그라운드 로딩 (QThread 워커)
  - 점진적 로딩 (청크 단위 삽입)
  - 아이콘 확장자별 캐싱
  - stat() 호출 최소화
  - QTableView 렌더링 최적화 (`setUniformRowHeights(True)`)

## 프로젝트 구조

```
file_explorer/
├── main.py              # 앱 엔트리포인트
├── explorer_widget.py   # FileExplorerWidget 메인 위젯
├── file_model.py        # FileTableModel 커스텀 모델
├── loader.py            # DirectoryLoader QThread 워커
├── navigation_bar.py    # NavigationBar 네비게이션 바
└── README.md            # 이 파일
```

## 설치

```bash
pip install PyQt6
```

## 실행

```bash
python main.py
```

## 사용

- **디렉토리 진입**: 디렉토리 더블클릭
- **파일 열기**: 파일 더블클릭 (OS 기본 프로그램)
- **상위 디렉토리 이동**: `..` 항목 더블클릭
- **네비게이션**: 뒤로/앞으로 버튼 또는 주소 바 경로 입력

## 기술 사항

- Python 3.10+
- PyQt6
- 표준 라이브러리: `os`, `pathlib`, `datetime`, `shutil`

## 성능

- 수만~수십만 개의 항목을 효율적으로 처리
- 백그라운드 로딩으로 UI 응답성 보장
- 점진적 로딩으로 초기 로딩 시간 단축
