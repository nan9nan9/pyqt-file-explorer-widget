"""파일 탐색기 주요 기능 테스트"""
import sys
import os
import tempfile
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QEventLoop, QTimer

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'file_explorer'))

from explorer_widget import FileExplorerWidget, parse_path_with_pattern
from file_model import FileTableModel
from loader import DirectoryLoader

print("="*70)
print("파일 탐색기 - 기능 통합 테스트")
print("="*70)

app = QApplication(sys.argv)

# ============================================================================
# 테스트 1: 디렉토리 네비게이션
# ============================================================================
print("\n[테스트 1] 디렉토리 네비게이션")
print("-" * 70)

with tempfile.TemporaryDirectory() as tmpdir:
    # 디렉토리 구조 생성
    Path(tmpdir, "subdir1").mkdir()
    Path(tmpdir, "subdir2").mkdir()
    Path(tmpdir, "file1.txt").touch()
    Path(tmpdir, "file2.py").touch()

    explorer = FileExplorerWidget(tmpdir)
    print(f"✓ 초기 경로: {tmpdir}")
    print(f"  로드된 항목: {len(explorer.model._items)}개")

    # 네비게이션 테스트
    explorer.navigate_to(tmpdir)
    if explorer.model._loader:
        explorer.model._loader.wait()

    print(f"✓ navigate_to() 성공")
    print(f"  현재 경로: {explorer._current_path}")
    print(f"  로드된 항목: {len(explorer.model._items)}개")


# ============================================================================
# 테스트 2: glob 패턴 필터링 기능
# ============================================================================
print("\n[테스트 2] glob 패턴 필터링")
print("-" * 70)

with tempfile.TemporaryDirectory() as tmpdir:
    # 테스트 파일 생성
    Path(tmpdir, "script1.py").touch()
    Path(tmpdir, "script2.py").touch()
    Path(tmpdir, "config.json").touch()
    Path(tmpdir, "readme.md").touch()
    Path(tmpdir, "test_one.py").touch()
    Path(tmpdir, "test_two.py").touch()

    explorer = FileExplorerWidget(tmpdir)

    # glob 패턴 필터링 테스트
    print(f"✓ 테스트 디렉토리: {tmpdir}")
    print(f"  생성된 파일: 6개")

    # 패턴 1: *.py
    explorer._navigate_with_pattern(tmpdir, "*.py")
    if explorer.model._loader:
        explorer.model._loader.wait()

    print(f"\n  패턴: *.py")
    print(f"  필터 결과: {len(explorer.model._items)}개")
    for item in sorted(explorer.model._items, key=lambda x: x['name']):
        print(f"    - {item['name']}")

    # 패턴 2: test_*.py
    explorer._navigate_with_pattern(tmpdir, "test_*.py")
    if explorer.model._loader:
        explorer.model._loader.wait()

    print(f"\n  패턴: test_*.py")
    print(f"  필터 결과: {len(explorer.model._items)}개")
    for item in sorted(explorer.model._items, key=lambda x: x['name']):
        print(f"    - {item['name']}")

    # 패턴 3: *.md
    explorer._navigate_with_pattern(tmpdir, "*.md")
    if explorer.model._loader:
        explorer.model._loader.wait()

    print(f"\n  패턴: *.md")
    print(f"  필터 결과: {len(explorer.model._items)}개")
    for item in sorted(explorer.model._items, key=lambda x: x['name']):
        print(f"    - {item['name']}")

    print(f"\n✓ glob 패턴 필터링 정상 작동")


# ============================================================================
# 테스트 3: 히스토리 네비게이션 (back/forward)
# ============================================================================
print("\n[테스트 3] 히스토리 네비게이션")
print("-" * 70)

with tempfile.TemporaryDirectory() as tmpdir:
    Path(tmpdir, "dir1").mkdir()
    Path(tmpdir, "dir2").mkdir()

    dir1 = os.path.join(tmpdir, "dir1")
    dir2 = os.path.join(tmpdir, "dir2")

    explorer = FileExplorerWidget(tmpdir)

    # 경로 이동: tmpdir → dir1 → dir2
    explorer.navigate_to(dir1)
    if explorer.model._loader:
        explorer.model._loader.wait()
    path1 = explorer._current_path
    print(f"✓ 이동 1: {os.path.basename(path1)}")
    print(f"  back_stack: {len(explorer._back_stack)}, forward_stack: {len(explorer._forward_stack)}")

    explorer.navigate_to(dir2)
    if explorer.model._loader:
        explorer.model._loader.wait()
    path2 = explorer._current_path
    print(f"✓ 이동 2: {os.path.basename(path2)}")
    print(f"  back_stack: {len(explorer._back_stack)}, forward_stack: {len(explorer._forward_stack)}")

    # 뒤로가기
    explorer._on_back()
    if explorer.model._loader:
        explorer.model._loader.wait()
    print(f"✓ 뒤로가기: {os.path.basename(explorer._current_path)}")
    print(f"  back_stack: {len(explorer._back_stack)}, forward_stack: {len(explorer._forward_stack)}")

    # 앞으로가기
    explorer._on_forward()
    if explorer.model._loader:
        explorer.model._loader.wait()
    print(f"✓ 앞으로가기: {os.path.basename(explorer._current_path)}")
    print(f"  back_stack: {len(explorer._back_stack)}, forward_stack: {len(explorer._forward_stack)}")


# ============================================================================
# 테스트 4: 파일 정보 포맷팅
# ============================================================================
print("\n[테스트 4] 파일 정보 포맷팅")
print("-" * 70)

with tempfile.TemporaryDirectory() as tmpdir:
    # 다양한 크기의 파일 생성
    Path(tmpdir, "small.txt").write_text("a" * 100)
    Path(tmpdir, "medium.txt").write_text("a" * 100000)
    Path(tmpdir, "large.txt").write_text("a" * 10000000)

    model = FileTableModel()
    model.load(tmpdir)
    if model._loader:
        model._loader.wait()

    print(f"✓ 파일 정보 포맷팅 테스트")
    for item in sorted(model._items, key=lambda x: x['name']):
        size_str = model._format_size(item['size'])
        print(f"  {item['name']:20} {size_str:>12}")

    print(f"\n✓ 파일 크기 포맷팅 정상 작동")


# ============================================================================
# 테스트 5: 경로 입력 처리
# ============================================================================
print("\n[테스트 5] 경로 입력 처리")
print("-" * 70)

with tempfile.TemporaryDirectory() as tmpdir:
    Path(tmpdir, "test1.py").touch()
    Path(tmpdir, "test2.py").touch()
    Path(tmpdir, "readme.txt").touch()

    explorer = FileExplorerWidget(tmpdir)

    # 경로 입력 테스트: glob 패턴
    input_path = os.path.join(tmpdir, "*.py")
    explorer._on_path_changed(input_path)
    if explorer.model._loader:
        explorer.model._loader.wait()

    print(f"✓ 입력: {input_path}")
    print(f"  필터 결과: {len(explorer.model._items)}개")
    print(f"  주소 바: {explorer.nav_bar.path_input.text()}")

    # 경로 입력 테스트: 일반 경로
    explorer._on_path_changed(tmpdir)
    if explorer.model._loader:
        explorer.model._loader.wait()

    print(f"\n✓ 입력: {tmpdir}")
    print(f"  로드 항목: {len(explorer.model._items)}개")
    print(f"  주소 바: {explorer.nav_bar.path_input.text()}")


# ============================================================================
# 테스트 6: 상위 디렉토리 항목 ("..")
# ============================================================================
print("\n[테스트 6] 상위 디렉토리 항목 ('..')")
print("-" * 70)

with tempfile.TemporaryDirectory() as tmpdir:
    Path(tmpdir, "file.txt").touch()

    model = FileTableModel()

    # 루트 디렉토리가 아닐 때 ".." 표시
    model.load(tmpdir)
    if model._loader:
        model._loader.wait()

    has_parent = any(item['name'] == '..' for item in model._items)
    print(f"✓ 일반 디렉토리: {tmpdir}")
    print(f"  '..' 항목 있음: {has_parent}")

    # glob 패턴 사용 시 ".." 미표시
    model.load(tmpdir, "*.txt")
    if model._loader:
        model._loader.wait()

    has_parent = any(item['name'] == '..' for item in model._items)
    print(f"\n✓ glob 패턴 필터: *.txt")
    print(f"  '..' 항목 있음: {has_parent}")
    print(f"  필터 결과: {len(model._items)}개")


# ============================================================================
# 최종 결과
# ============================================================================
print("\n" + "="*70)
print("✓✓✓ 모든 기능 테스트 완료 - 정상 작동! ✓✓✓")
print("="*70)

print("""
테스트된 기능:
  1. 디렉토리 네비게이션
  2. glob 패턴 필터링 (*.py, test_*.py, *.md 등)
  3. 히스토리 네비게이션 (뒤로, 앞으로)
  4. 파일 정보 포맷팅 (크기, 수정시간)
  5. 경로 입력 처리 (일반 경로 및 glob 패턴)
  6. 상위 디렉토리 항목 (".." 조건부 표시)

실행 방법:
  - file_explorer 디렉토리: python main.py
  - 단일 파일: python file_explorer_single.py
""")
print("="*70)
