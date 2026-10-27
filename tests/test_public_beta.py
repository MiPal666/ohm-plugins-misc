"""Run packaging guards against isolated fixtures; never touch system OHM."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKAGING = ROOT / 'packaging/public-beta'
STOCK = b'test stock library\n'
PATCH = b'test patched library\n'
STOCK_SHA = '3ca3739aadff088504357f9e5045c0a9d4eb361c74d611d8fcefb3e78c180f3a'
PATCH_SHA = '4226abfd91a0fb5df545b796d29d9c6d664cf872eba61c8415744b7d7e77b04a'


class PublicBetaGuards(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='felis-rpm-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.active = self.root / 'active.so'
        self.payload = self.root / 'payload.so'
        self.state = self.root / 'state'
        self.backup = self.state / 'libohm_accessories.so.original'
        self.release = self.root / 'os-release'
        self.active.write_bytes(STOCK)
        self.payload.write_bytes(PATCH)
        self.release.write_text('ID=sailfishos\nVERSION_ID=5.2.0.22\n')
        bindir = self.root / 'bin'
        bindir.mkdir()
        mocks = {
            'uname': '#!/bin/sh\nprintf "%s\\n" "${TEST_ARCH:-aarch64}"\n',
            'rpm': '#!/bin/sh\nprintf "%s" "${TEST_NATIVE:-1.11.0-1.11.1.jolla}"\n',
            'systemctl': '#!/bin/sh\n[ "${TEST_RESTART_FAIL:-0}" != 1 ]\n',
            'install': '#!/usr/bin/python3\nimport os,sys\na=sys.argv[1:]; out=[]\nwhile a:\n x=a.pop(0)\n if x in ("-o","-g"): a.pop(0)\n else: out.append(x)\nos.execv("/usr/bin/install",["install"]+out)\n',
        }
        for name, content in mocks.items():
            p = bindir / name
            p.write_text(content)
            p.chmod(0o755)
        self.env = dict(os.environ, PATH=f'{bindir}:/usr/bin:/bin')
        helper = (PACKAGING / 'felis-ohm-control.sh').read_text()
        spec = (PACKAGING / 'felis-ohm-a2dp-fix.spec').read_text()
        pre = spec.split('\n%pre\n', 1)[1].split('\n%post\n', 1)[0].replace('%%', '%')
        replacements = {
            '/etc/os-release': str(self.release),
            '/usr/lib64/ohm/libohm_accessories.so': str(self.active),
            '/usr/share/felis-ohm-a2dp-fix/libohm_accessories.so': str(self.payload),
            '/var/lib/felis-ohm-a2dp-fix': str(self.state),
            STOCK_SHA: hashlib.sha256(STOCK).hexdigest(),
            PATCH_SHA: hashlib.sha256(PATCH).hexdigest(),
        }
        for old, new in replacements.items():
            helper = helper.replace(old, new)
            pre = pre.replace(old, new)
        self.helper = self.root / 'helper.sh'
        self.pre = self.root / 'pre.sh'
        self.helper.write_text(helper)
        self.pre.write_text(pre)

    def run_script(self, script, arg, ok=True):
        result = subprocess.run(['sh', str(script), arg], env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode == 0, ok, result.stdout + result.stderr)
        return result

    def test_install_restore_both_releases(self):
        for version in ('5.2.0.20', '5.2.0.22'):
            with self.subTest(version=version):
                self.release.write_text(f'ID=sailfishos\nVERSION_ID={version}\n')
                self.run_script(self.pre, '1')
                self.run_script(self.helper, 'activate')
                self.assertEqual(self.active.read_bytes(), PATCH)
                self.assertEqual(self.backup.read_bytes(), STOCK)
                self.run_script(self.helper, 'restore')
                self.assertEqual(self.active.read_bytes(), STOCK)
                self.assertEqual(self.backup.read_bytes(), STOCK)

    def test_unsupported_os_rejected_for_install_and_restore(self):
        for release in ('ID=sailfishos\nVERSION_ID=5.2.0.24\n', 'ID=other\nVERSION_ID=5.2.0.22\n'):
            self.release.write_text(release)
            self.run_script(self.pre, '1', ok=False)
            self.run_script(self.helper, 'activate', ok=False)
            self.run_script(self.helper, 'restore', ok=False)
            self.assertEqual(self.active.read_bytes(), STOCK)

    def test_wrong_arch_rejected(self):
        self.env['TEST_ARCH'] = 'x86_64'
        self.run_script(self.pre, '1', ok=False)
        self.run_script(self.helper, 'activate', ok=False)

    def test_wrong_native_package_rejected(self):
        self.env['TEST_NATIVE'] = '1.12.0-1'
        self.run_script(self.pre, '1', ok=False)
        self.run_script(self.helper, 'activate', ok=False)
        self.run_script(self.helper, 'restore', ok=False)

    def test_upgrade_rejected(self):
        self.run_script(self.pre, '2', ok=False)

    def test_modified_active_rejected(self):
        self.active.write_bytes(b'unknown library')
        self.run_script(self.pre, '1', ok=False)
        self.run_script(self.helper, 'activate', ok=False)
        self.assertEqual(self.active.read_bytes(), b'unknown library')

    def test_symlink_active_rejected(self):
        self.active.unlink()
        self.active.symlink_to(self.payload)
        self.run_script(self.pre, '1', ok=False)
        self.run_script(self.helper, 'activate', ok=False)

    def test_corrupt_backup_rejected(self):
        self.state.mkdir()
        self.backup.write_bytes(b'bad backup')
        self.run_script(self.pre, '1', ok=False)
        self.run_script(self.helper, 'activate', ok=False)
        self.assertEqual(self.active.read_bytes(), STOCK)

    def test_corrupt_payload_rejected(self):
        self.payload.write_bytes(b'bad payload')
        self.run_script(self.helper, 'activate', ok=False)
        self.assertEqual(self.active.read_bytes(), STOCK)

    def test_restart_failure_restores_stock(self):
        self.env['TEST_RESTART_FAIL'] = '1'
        self.run_script(self.helper, 'activate', ok=False)
        self.assertEqual(self.active.read_bytes(), STOCK)
        self.assertEqual(self.backup.read_bytes(), STOCK)

    def test_restore_does_not_overwrite_unknown_library(self):
        self.run_script(self.helper, 'activate')
        self.active.write_bytes(b'new vendor library')
        self.run_script(self.helper, 'restore', ok=False)
        self.assertEqual(self.active.read_bytes(), b'new vendor library')

    def test_restore_refuses_corrupt_backup(self):
        self.run_script(self.helper, 'activate')
        self.backup.write_bytes(b'bad backup')
        self.run_script(self.helper, 'restore', ok=False)
        self.assertEqual(self.active.read_bytes(), PATCH)


if __name__ == '__main__':
    unittest.main()
