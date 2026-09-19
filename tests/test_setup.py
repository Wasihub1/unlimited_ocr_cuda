"""Setup decisions, failure propagation, and isolated Windows bootstrap checks."""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import run


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        self.enterContext(patch.object(run, 'ROOT', self.folder))
        (self.folder / 'env').mkdir()
        (self.folder / 'requirements-common.txt').write_text('common')
        for profile in ['cpu', 'cuda']:
            (self.folder / f'requirements-{profile}.txt').write_text(profile)
        (self.folder / 'vendor/unlimited-ocr/.git').mkdir(parents=True)

    def test_hash_skips_repeat_and_invalidates_on_change_and_profile(self):
        with patch.object(run, 'command') as install:
            run.install_dependencies('python', 'cpu')
            run.install_dependencies('python', 'cpu')
            self.assertEqual(install.call_count, 1)
            (self.folder / 'requirements-common.txt').write_text('changed')
            run.install_dependencies('python', 'cpu')
            run.install_dependencies('python', 'cuda')
            self.assertEqual(install.call_count, 3)

    def test_install_failure_does_not_write_stamp(self):
        with patch.object(run, 'command', side_effect=RuntimeError('pip failed')):
            with self.assertRaises(RuntimeError):
                run.install_dependencies('python', 'cpu')
        self.assertFalse((self.folder / 'env/.requirements.stamp').exists())

    def test_cache_failure_prevents_server(self):
        with patch.object(sys, 'argv', ['run.py', '--device', 'cuda']), \
             patch.object(run, 'ensure_environment', return_value=Path(sys.executable)), \
             patch.object(run, 'install_dependencies'), \
             patch.object(run, 'command', side_effect=RuntimeError('simulated cache failure')), \
             patch('uvicorn.run') as serve:
            self.assertEqual(run.main(), 1)
            serve.assert_not_called()

    def test_cpu_skips_download_and_force_download_overrides(self):
        with patch.object(run, 'ensure_environment', return_value=Path(sys.executable)), \
             patch.object(run, 'command') as download:
            for extra in [[], ['--force-download']]:
                with patch.object(sys, 'argv', ['run.py', '--device', 'cpu', '--setup-only', '--skip-install'] + extra):
                    self.assertEqual(run.main(), 0)
                self.assertEqual(download.call_count, int(bool(extra)))

    def test_auto_profile(self):
        with patch('run.shutil.which', return_value=None):
            self.assertEqual(run.dependency_profile('auto'), 'cpu')
        with patch('run.shutil.which', return_value='nvidia-smi'), patch('run.subprocess.run') as detect:
            detect.return_value.returncode = 0
            self.assertEqual(run.dependency_profile('auto'), 'cuda')
            detect.return_value.returncode = 1
            self.assertEqual(run.dependency_profile('auto'), 'cpu')


@unittest.skipUnless(os.name == 'nt', 'Windows bootstrap scripts')
class WindowsBootstrapTests(unittest.TestCase):
    def test_real_venv_repeat_and_batch_failure(self):
        root = Path(__file__).resolve().parents[1]
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        shutil.copy(root / 'setup.ps1', folder / 'setup.ps1')
        shutil.copy(root / 'run.bat', folder / 'run.bat')
        # Dot source the actual functions in an isolated workspace, then use a real 3.12 runtime.
        bootstrap = folder / 'check.ps1'
        bootstrap.write_text(". (Join-Path $PSScriptRoot 'setup.ps1')\n"
                             "$first = Initialize-Environment $args[0]\n"
                             "$before = (Get-Item -LiteralPath $first).LastWriteTimeUtc\n"
                             "$second = Initialize-Environment $args[0]\n"
                             "if ($first -ne $second -or $before -ne (Get-Item -LiteralPath $second).LastWriteTimeUtc) { exit 9 }\n", encoding='utf-8')
        result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(bootstrap), sys.executable], capture_output=True, text=True, timeout=90)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((folder / 'env/Scripts/python.exe').exists())
        # Keep the real batch/PowerShell chain; only the setup workload is a failing fixture.
        (folder / 'run.py').write_text("import sys\nfrom pathlib import Path\nif '--setup-only' in sys.argv:\n print('Setup failed at step model cache: simulated failure', flush=True)\n sys.exit(7)\nPath('server-started').touch()\n")
        result = subprocess.run([os.environ['COMSPEC'], '/c', 'run.bat', '--no-browser'], cwd=folder, input='\n', capture_output=True, text=True, timeout=30)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn('simulated failure', result.stdout)
        self.assertFalse((folder / 'server-started').exists())

    def test_python_detection_rejects_wrong_version_then_uses_valid_py(self):
        root = Path(__file__).resolve().parents[1]
        folder = Path(self.enterContext(tempfile.TemporaryDirectory()))
        shutil.copy(root / 'setup.ps1', folder / 'setup.ps1')
        harness = folder / 'detect.ps1'
        harness.write_text(". (Join-Path $PSScriptRoot 'setup.ps1')\n"
                           "$env:LOCALAPPDATA = $PSScriptRoot\n"
                           "function py { $global:LASTEXITCODE = 0; return '' }\n"
                           "function python { $global:LASTEXITCODE = 0; return '' }\n"
                           "if (Find-Python312) { throw 'Wrong Python accepted' }\n"
                           "$script:expected = $args[0]\n"
                           "function py { $global:LASTEXITCODE = 0; return $script:expected }\n"
                           "if ((Find-Python312) -ne $script:expected) { throw 'Valid py rejected' }\n", encoding='utf-8')
        result = subprocess.run(['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(harness), sys.executable], capture_output=True, text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
