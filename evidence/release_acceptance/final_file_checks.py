"""Documented first run plus exact installed package payload identity."""
import hashlib
import json
import os
import subprocess
from pathlib import Path

from evidence.release_acceptance import selected_file_checks as original
from test_cycle import ROOT, redact


class FinalFileChecks(original.SelectedFileChecks):
    def test_installed_console_first_run_and_file_mutations(self):
        super().test_installed_console_first_run_and_file_mutations()
        manifest = json.loads((ROOT / os.environ['WTL_SELECTED_MANIFEST']).read_text(encoding='utf-8'))
        expected = {name: digest for name, digest in manifest['package_source_sha256'].items()
                    if name.startswith('watchmode_truth_lab/')}
        executable = Path(os.environ['WTL_INSTALLED_PYTHON']).absolute()
        project = Path(os.environ['WTL_FILE_PROJECT']).resolve()
        code = ('import hashlib,json,sys,watchmode_truth_lab\nfrom pathlib import Path\n'
                'root=Path(watchmode_truth_lab.__file__).parent.parent\n'
                'assert root.is_relative_to(Path(sys.prefix))\n'
                'expected=json.loads(sys.argv[1])\n'
                'actual={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in expected}\n'
                'assert actual==expected\nprint(json.dumps(actual))\n')
        environment = os.environ.copy()
        environment.pop('PYTHONPATH', None)
        environment.update(PYTHONUTF8='1', PYTHONDONTWRITEBYTECODE='1')
        result = subprocess.run([str(executable), '-c', code, json.dumps(expected)], cwd=project,
                                env=environment, capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads(result.stdout)
        self.assertEqual(actual, expected)
        output = ROOT / os.environ['WTL_FILE_EVIDENCE'] / 'installed-payload-identity.json'
        self.assertFalse(output.exists())
        output.write_text(redact(json.dumps({'controller_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'import_within_fresh_venv_verified':True,'installed_package_sources_sha256':actual},indent=2))+'\n',encoding='utf-8')
