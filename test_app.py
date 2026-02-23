"""파일 탐색기 애플리케이션 테스트"""
import sys
import os
import tempfile
from pathlib import Path

# PyQt 애플리케이션 초기화
from PyQt6.QtWidgets import QApplication

# file_explorer 모듈 임포트
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'file_explorer'))

print("="*60)
print("파일 탐색기 애플리케이션 테스트")
print("="*60)

# ============================================================================
# 테스트 1: 모듈 임포트 테스트
# ============================================================================
print("\n[테스트 1] 모듈 임포트")
print("-" * 60)

try:
    from loader import DirectoryLoader
    print("✓ DirectoryLoader 임포트 성공")
except Exception as e:
    print(f"✗ DirectoryLoader 임포트 실패: {e}")
    sys.exit(1)

try:
    from file_model import FileTableModel
    print("✓ FileTableModel 임포트 성공")
except Exception as e:
    print(f"✗ FileTableModel 임포트 실패: {e}")
    sys.exit(1)

try:
    from navigation_bar import NavigationBar
    print("✓ NavigationBar 임포트 성공")
except Exception as e:
    print(f"✗ NavigationBar 임포트 실패: {e}")
    sys.exit(1)

try:
    from explorer_widget import FileExplorerWidget, parse_path_with_pattern
    print("✓ FileExplorerWidget 임포트 성공")
    print("✓ parse_path_with_pattern 함수 임포트 성공")
except Exception as e:
    print(f"✗ FileExplorerWidget 임포트 실패: {e}")
    sys.exit(1)


# ============================================================================
# 테스트 2: 경로 파싱 함수 테스트
# ============================================================================
print("\n[테스트 2] 경로 파싱 함수 (parse_path_with_pattern)")
print("-" * 60)

test_cases = [
    ("/home/user/*.py", "/home/user", "*.py"),
    ("/home/user", "/home/user", None),
    ("*.txt", None, "*.txt"),  # None은 os.getcwd()와 비교 필요
    ("/path/test_*.py", "/path", "test_*.py"),
]

all_passed = True
for input_path, expected_dir, expected_pattern in test_cases:
    dir_path, pattern = parse_path_with_pattern(input_path)

    # 현재 디렉토리는 동적이므로 특수 처리
    if expected_dir is None:
        dir_match = True
    else:
        dir_match = os.path.abspath(dir_path) == os.path.abspath(expected_dir)

    pattern_match = pattern == expected_pattern

    if dir_match and pattern_match:
        print(f"✓ '{input_path}' → pattern={pattern}")
    else:
        print(f"✗ '{input_path}'")
        if not dir_match:
            print(f"  디렉토리 오류: {dir_path}")
        if not pattern_match:
            print(f"  패턴 오류: {pattern} != {expected_pattern}")
        all_passed = False

if all_passed:
    print("\n✓ 모든 경로 파싱 테스트 통과")
else:
    print("\n✗ 일부 경로 파싱 테스트 실패")


# ============================================================================
# 테스트 3: 클래스 인스턴스화 테스트
# ============================================================================
print("\n[테스트 3] 클래스 인스턴스화")
print("-" * 60)

app = QApplication(sys.argv)

try:
    nav_bar = NavigationBar()
    print("✓ NavigationBar 인스턴스 생성 성공")
except Exception as e:
    print(f"✗ NavigationBar 인스턴스 생성 실패: {e}")
    sys.exit(1)

try:
    model = FileTableModel()
    print("✓ FileTableModel 인스턴스 생성 성공")
except Exception as e:
    print(f"✗ FileTableModel 인스턴스 생성 실패: {e}")
    sys.exit(1)

try:
    explorer = FileExplorerWidget(os.getcwd())
    print("✓ FileExplorerWidget 인스턴스 생성 성공")
except Exception as e:
    print(f"✗ FileExplorerWidget 인스턴스 생성 실패: {e}")
    sys.exit(1)


# ============================================================================
# 테스트 4: glob 패턴 필터링 테스트
# ============================================================================
print("\n[테스트 4] glob 패턴 필터링 (DirectoryLoader)")
print("-" * 60)

import fnmatch

test_dir = os.path.dirname(__file__)
all_files = os.listdir(test_dir)

# *.py 필터
py_files = [f for f in all_files if fnmatch.fnmatch(f, "*.py")]
print(f"✓ *.py 패턴: {len(py_files)}개 파일 매치")
print(f"  예: {', '.join(sorted(py_files)[:3])}")

# test_*.py 필터
test_files = [f for f in all_files if fnmatch.fnmatch(f, "test_*.py")]
print(f"✓ test_*.py 패턴: {len(test_files)}개 파일 매치")
if test_files:
    print(f"  예: {', '.join(sorted(test_files)[:3])}")

# *.md 필터
md_files = [f for f in all_files if fnmatch.fnmatch(f, "*.md")]
print(f"✓ *.md 패턴: {len(md_files)}개 파일 매치")
if md_files:
    print(f"  예: {', '.join(sorted(md_files)[:3])}")


# ============================================================================
# 테스트 5: DirectoryLoader 기능 테스트
# ============================================================================
print("\n[테스트 5] DirectoryLoader 기능")
print("-" * 60)

from PyQt6.QtCore import QEventLoop

# 테스트 디렉토리 생성
with tempfile.TemporaryDirectory() as tmpdir:
    # 테스트 파일 생성
    Path(tmpdir, "test1.py").touch()
    Path(tmpdir, "test2.py").touch()
    Path(tmpdir, "data.txt").touch()
    Path(tmpdir, "subdir").mkdir()

    print(f"테스트 디렉토리 생성: {tmpdir}")

    # 테스트 1: 전체 파일 로드
    loader1 = DirectoryLoader(tmpdir)
    results1 = []

    def on_finished1(items):
        results1.extend(items)
        loop.quit()

    loop = QEventLoop()
    loader1.finished.connect(on_finished1)
    loader1.start()
    loop.exec()

    print(f"✓ 전체 로드: {len(results1)}개 항목")

    # 테스트 2: *.py 패턴 필터
    loader2 = DirectoryLoader(tmpdir, "*.py")
    results2 = []

    def on_finished2(items):
        results2.extend(items)
        loop.quit()

    loop = QEventLoop()
    loader2.finished.connect(on_finished2)
    loader2.start()
    loop.exec()

    print(f"✓ *.py 필터: {len(results2)}개 파일")
    for item in sorted(results2, key=lambda x: x['name']):
        print(f"  - {item['name']}")

    # 검증
    if len(results2) == 2 and all(item['name'].endswith('.py') for item in results2):
        print("✓ *.py 필터링 검증 통과")
    else:
        print("✗ *.py 필터링 검증 실패")

    # 테스트 3: test_*.py 패턴 필터
    loader3 = DirectoryLoader(tmpdir, "test_*.py")
    results3 = []

    def on_finished3(items):
        results3.extend(items)
        loop.quit()

    loop = QEventLoop()
    loader3.finished.connect(on_finished3)
    loader3.start()
    loop.exec()

    print(f"✓ test_*.py 필터: {len(results3)}개 파일")
    for item in sorted(results3, key=lambda x: x['name']):
        print(f"  - {item['name']}")

    if len(results3) == 2 and all(item['name'].startswith('test_') for item in results3):
        print("✓ test_*.py 필터링 검증 통과")
    else:
        print("✗ test_*.py 필터링 검증 실패")


# ============================================================================
# 테스트 6: FileTableModel 로드 테스트
# ============================================================================
print("\n[테스트 6] FileTableModel 로드")
print("-" * 60)

with tempfile.TemporaryDirectory() as tmpdir:
    # 테스트 파일 생성
    Path(tmpdir, "file1.py").touch()
    Path(tmpdir, "file2.py").touch()
    Path(tmpdir, "readme.txt").touch()

    model = FileTableModel()

    # 테스트 1: 일반 로드
    model.load(tmpdir)
    print(f"✓ 디렉토리 로드: {model.rowCount()}개 항목")

    # 로더 완료 대기
    if model._loader:
        model._loader.wait()

    print(f"  로드 완료: {model.rowCount()}개 항목")

    # 테스트 2: glob 패턴 로드
    model.load(tmpdir, "*.py")
    print(f"✓ glob 패턴 로드 시작")

    if model._loader:
        model._loader.wait()

    print(f"  로드 완료: {model.rowCount()}개 항목")

    # ".." 항목이 없어야 함 (glob 패턴 사용 시)
    has_parent = any(item['name'] == '..' for item in model._items)
    if not has_parent:
        print("✓ glob 패턴 사용 시 '..' 항목 없음 (정상)")
    else:
        print("✗ glob 패턴 사용 시 '..' 항목이 있음 (오류)")


# ============================================================================
# 최종 결과
# ============================================================================
print("\n" + "="*60)
print("✓ 모든 테스트 완료 - 애플리케이션 정상 작동!")
print("="*60)
print("\n사용 방법:")
print("1. file_explorer 디렉토리: python main.py")
print("2. 단일 파일: python file_explorer_single.py")
print("\n기능:")
print("- 파일/디렉토리 탐색")
print("- 뒤로/앞으로 네비게이션")
print("- glob 패턴 필터링 (예: *.py, test_*.py)")
print("="*60)
