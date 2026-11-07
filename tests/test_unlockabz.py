import contextlib
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine
import unlockabz


class RecoveryTests(unittest.TestCase):
    def test_mask_range_has_no_leading_zero(self):
        args = engine.attack_arguments('numbers8')
        self.assertEqual(args, ['-a', '3', '-1', '123456789', '?1?d?d?d?d?d?d?d'])
        self.assertEqual(9 * 10 ** 7, engine.LISTS['numbers8'][1])

    def test_actual_small_dictionary(self):
        self.assertEqual(engine.NUMBERS_SMALL.read_text().splitlines(), [str(n) for n in range(1, 10000)])

    def test_shell_escaped_and_quoted_paths(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'some file.docx'
            path.touch()
            self.assertEqual(unlockabz.normalize_path(str(path)), path)
            self.assertEqual(unlockabz.normalize_path("'" + str(path) + "'"), path)
            self.assertEqual(unlockabz.normalize_path(str(path).replace(' ', '\\ ')), path)

    def test_cleanup_preserves_reports_and_does_not_follow_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            outside = root / 'outside'
            outside.mkdir()
            (outside / 'important').write_text('keep')
            job = root / 'job'
            job.mkdir()
            for name in ('upload.docx', 'input.hash', 'recovered.raw', 'passwords.txt', 'passwords.pot', 'result.json', 'unlocked.docx'):
                (job / name).write_text('data')
            (job / 'data').symlink_to(outside, target_is_directory=True)
            unlockabz.cleanup_job(job)
            self.assertTrue((outside / 'important').is_file())
            self.assertEqual({p.name for p in job.iterdir()}, {'passwords.txt', 'passwords.pot', 'result.json', 'unlocked.docx'})

    def test_lock_prevents_cleanup_during_attack(self):
        with tempfile.TemporaryDirectory() as d, patch.object(unlockabz, 'BASE', Path(d)):
            with unlockabz.exclusive():
                with self.assertRaisesRegex(ValueError, 'Boshqa UnlockAbz'):
                    unlockabz.cleanup_all()

    def test_invalid_hc22000(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / 'bad.hc22000'
            path.write_text('WPA*02*broken')
            with self.assertRaises(ValueError):
                engine.extract_hash(path, root)

    def test_valid_pmkid_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = root / 'valid.hc22000'
            value = 'WPA*01*' + 'a'*32 + '*001122334455*66778899aabb*54657374***\n'
            path.write_text(value)
            target, mode = engine.extract_hash(path, root)
            self.assertEqual(mode, '22000')
            self.assertEqual(target.read_text(), value)

    def test_invalid_list_rejected(self):
        with self.assertRaises(ValueError):
            engine.attack_arguments('rockyou')

    def test_wpa_short_list_rejected_before_job_creation(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'test.hc22000'
            path.touch()
            with self.assertRaisesRegex(ValueError, 'kamida 8'):
                unlockabz.recover(path, 'numbers1to9999')

    def test_cancelled_worker_persists_report_without_launching(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            event = threading.Event()
            event.set()
            job = dict(directory=root, source=root/'test.docx', state='preparing', cancel=event, passwords=[], log=[])
            with patch.object(engine.shutil, 'which', return_value='/bin/tool'), patch.object(engine.subprocess, 'Popen') as launch:
                engine.worker(job)
                launch.assert_not_called()
            report = json.loads((root/'result.json').read_text())
            self.assertEqual(report['state'], 'cancelled')
            self.assertNotIn('cancel', report)
            self.assertNotIn('directory', report)

    def test_incomplete_office_output_is_removed_and_warning_saved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            source = root / 'broken.docx'
            source.write_text('not Office')
            fake_process = unittest.mock.Mock()
            fake_process.stdout = iter([])
            fake_process.wait.return_value = 0
            job = dict(id='test', directory=root, source=source, list='numbers8', state='preparing',
                       cancel=threading.Event(), passwords=[], log=[])
            with patch.object(engine.shutil, 'which', return_value='/bin/tool'), \
                 patch.object(engine, 'extract_hash', return_value=(root/'input.hash','9600')), \
                 patch.object(engine, 'environment', return_value={}), \
                 patch.object(engine.subprocess, 'Popen', return_value=fake_process), \
                 patch.object(engine.subprocess, 'check_output', return_value=b'2023\n'):
                engine.worker(job)
            self.assertEqual(job['state'], 'found')
            self.assertIn('warning', job)
            self.assertFalse((root/'unlocked.tmp').exists())
            self.assertFalse((root/'unlocked.docx').exists())
            self.assertEqual((root/'passwords.txt').read_text(), '2023\n')

    def test_partial_wpa_recovery_is_distinct_from_complete(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            proc = unittest.mock.Mock()
            proc.stdout = iter([])
            proc.wait.return_value = 1
            job = dict(id='test',directory=root,source=root/'test.hc22000',list='numbers8',
                       state='preparing',cancel=threading.Event(),passwords=[],log=[])
            with patch.object(engine.shutil, 'which', return_value='/bin/tool'), \
                 patch.object(engine, 'extract_hash', return_value=(root/'input.hash','22000')), \
                 patch.object(engine, 'environment', return_value={}), \
                 patch.object(engine.subprocess, 'Popen', return_value=proc), \
                 patch.object(engine.subprocess, 'check_output', return_value=b'12345678\n'):
                engine.worker(job)
            self.assertEqual(job['state'], 'partial')
            self.assertEqual(job['passwords'], ['12345678'])


if __name__ == '__main__':
    unittest.main()
