"""Build automation: PyInstaller -> sign -> Inno Setup.

Signing is opt-in via environment variables:
  SIGN_THUMBPRINT   — cert thumbprint in Windows certificate store (preferred)
  SIGN_PFX_PATH     — path to a .pfx file
  SIGN_PFX_PASSWORD — password for the .pfx file (used with SIGN_PFX_PATH)

Example (cert store):
  set SIGN_THUMBPRINT=ABCDEF1234...
  python build.py

Example (pfx file):
  set SIGN_PFX_PATH=C:\\certs\\my.pfx
  set SIGN_PFX_PASSWORD=secret
  python build.py
"""
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / 'dist'
BUILD = ROOT / 'build'
SPEC = ROOT / 'ExcelDiff.spec'
ISS = ROOT / 'installer' / 'excel_diff_setup.iss'
VERSION_FILE = ROOT / 'src' / 'excel_diff' / '__init__.py'

ISCC = Path(r'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')

_SIGNTOOL_SEARCH = [
    Path(r'C:\Program Files (x86)\Windows Kits\10\bin'),
    Path(r'C:\Program Files\Windows Kits\10\bin'),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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

    vf = ROOT / 'version_file.txt'
    text = vf.read_text(encoding='utf-8')
    text = re.sub(r'filevers=\(.*?\)', f'filevers=({tuple_str})', text)
    text = re.sub(r'prodvers=\(.*?\)', f'prodvers=({tuple_str})', text)
    text = re.sub(r"(u'FileVersion',\s*u').*?'", f"u'FileVersion', u'{version}.0'", text)
    text = re.sub(r"(u'ProductVersion',\s*u').*?'", f"u'ProductVersion', u'{version}'", text)
    vf.write_text(text, encoding='utf-8')


def _force_remove(_func, path, _exc):
    import stat
    os.chmod(path, stat.S_IWRITE)
    if os.path.isfile(path):
        os.remove(path)
    else:
        os.rmdir(path)


def _find_signtool() -> Path | None:
    # Prefer PATH (works in CI and when SDK is on PATH)
    found = shutil.which('signtool')
    if found:
        return Path(found)
    # Search Windows SDK directories (newest version first)
    for base in _SIGNTOOL_SEARCH:
        if not base.exists():
            continue
        candidates = sorted(base.glob('*/x64/signtool.exe'), reverse=True)
        if candidates:
            return candidates[0]
    return None


# ---------------------------------------------------------------------------
# Build steps
# ---------------------------------------------------------------------------

def clean():
    for d in (DIST, BUILD):
        if d.exists():
            shutil.rmtree(d, onexc=_force_remove)
    print('Cleaned dist/ and build/')


def run_pyinstaller():
    print('Running PyInstaller...')
    subprocess.check_call([sys.executable, '-m', 'PyInstaller', str(SPEC)])
    print(f'Binary created at: {DIST / "ExcelDiff" / "ExcelDiff.exe"}')


def sign(targets: list[Path]):
    """Sign one or more executables. Skips silently if no signing config."""
    thumbprint = os.environ.get('SIGN_THUMBPRINT')
    pfx_path = os.environ.get('SIGN_PFX_PATH')

    if not thumbprint and not pfx_path:
        print('No signing credentials set — skipping code signing.')
        print('  Set SIGN_THUMBPRINT or SIGN_PFX_PATH to enable signing.')
        return

    signtool = _find_signtool()
    if not signtool:
        print('signtool.exe not found — skipping code signing.')
        print('  Install the Windows SDK to enable signing.')
        return

    for target in targets:
        if not target.exists():
            print(f'  WARNING: {target} not found, skipping.')
            continue

        cmd = [
            str(signtool), 'sign',
            '/fd', 'SHA256',
            '/tr', 'http://timestamp.digicert.com',
            '/td', 'SHA256',
        ]

        if thumbprint:
            cmd += ['/sha1', thumbprint]
        elif pfx_path:
            cmd += ['/f', pfx_path]
            pfx_pass = os.environ.get('SIGN_PFX_PASSWORD', '')
            if pfx_pass:
                cmd += ['/p', pfx_pass]

        cmd.append(str(target))
        print(f'Signing {target.name}...')
        subprocess.check_call(cmd)

    print('Code signing complete.')


def run_inno():
    if not ISCC.exists():
        # Try PATH (works in CI after choco install innosetup)
        iscc_on_path = shutil.which('iscc') or shutil.which('ISCC')
        if not iscc_on_path:
            print(f'Inno Setup not found. Skipping installer build.')
            return
        iscc_cmd = iscc_on_path
    else:
        iscc_cmd = str(ISCC)

    if not ISS.exists():
        print(f'ISS script not found at {ISS}. Skipping installer build.')
        return

    print('Running Inno Setup...')
    subprocess.check_call([iscc_cmd, str(ISS)])
    output = ROOT / 'installer' / 'Output'
    installers = list(output.glob('*.exe')) if output.exists() else []
    if installers:
        print(f'Installer created at: {installers[0]}')
        return installers[0]
    return None


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    version = get_version()
    print(f'Building version {version}')

    patch_version_file(version)
    patch_iss_version(version)
    clean()
    run_pyinstaller()

    exe = DIST / 'ExcelDiff' / 'ExcelDiff.exe'
    sign([exe])

    installer = run_inno()
    if installer:
        sign([installer])
