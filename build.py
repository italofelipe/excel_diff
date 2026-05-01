"""Build automation: PyInstaller -> Inno Setup."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / 'dist'
BUILD = ROOT / 'build'
SPEC = ROOT / 'ExcelDiff.spec'
ISCC = Path(r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
ISS = ROOT / 'installer' / 'excel_diff_setup.iss'
VERSION_FILE = ROOT / 'src' / 'excel_diff' / '__init__.py'


def get_version() -> str:
    text = VERSION_FILE.read_text(encoding='utf-8')
    match = re.search(r'__version__\s*=\s*["\'](.+?)["\']', text)
    if not match:
        raise RuntimeError('__version__ not found in src/excel_diff/__init__.py')
    return match.group(1)


def patch_iss_version(version: str):
    text = ISS.read_text(encoding='utf-8')
    text = re.sub(r'AppVersion=.*', f'AppVersion={version}', text)
    text = re.sub(r'OutputBaseFilename=.*', f'OutputBaseFilename=ExcelDiff_Instalador_v{version}', text)
    ISS.write_text(text, encoding='utf-8')


def patch_version_file(version: str):
    parts = version.split('.')
    while len(parts) < 4:
        parts.append('0')
    tuple_str = ', '.join(parts[:4])

    text = (ROOT / 'version_file.txt').read_text(encoding='utf-8')
    text = re.sub(r'filevers=\(.*?\)', f'filevers=({tuple_str})', text)
    text = re.sub(r'prodvers=\(.*?\)', f'prodvers=({tuple_str})', text)
    text = re.sub(r"(u'FileVersion',\s*u').*?'", f"u'FileVersion', u'{version}.0'", text)
    text = re.sub(r"(u'ProductVersion',\s*u').*?'", f"u'ProductVersion', u'{version}'", text)
    (ROOT / 'version_file.txt').write_text(text, encoding='utf-8')


def clean():
    for d in (DIST, BUILD):
        if d.exists():
            shutil.rmtree(d)
    print('Cleaned dist/ and build/')


def run_pyinstaller():
    print('Running PyInstaller...')
    subprocess.check_call([sys.executable, '-m', 'PyInstaller', str(SPEC)])
    exe = DIST / 'ExcelDiff' / 'ExcelDiff.exe'
    print(f'Binary created at: {exe}')


def run_inno(version: str):
    if not ISCC.exists():
        print(f'Inno Setup not found at {ISCC}. Skipping installer build.')
        return
    if not ISS.exists():
        print(f'ISS script not found at {ISS}. Skipping installer build.')
        return
    print('Running Inno Setup...')
    subprocess.check_call([str(ISCC), str(ISS)])
    output = ROOT / 'installer' / 'Output'
    installers = list(output.glob('*.exe')) if output.exists() else []
    if installers:
        print(f'Installer created at: {installers[0]}')


if __name__ == '__main__':
    version = get_version()
    print(f'Building version {version}')
    patch_version_file(version)
    patch_iss_version(version)
    clean()
    run_pyinstaller()
    run_inno(version)
