from collections import namedtuple
from contextlib import contextmanager
import logging
from mock import patch
from pathlib import Path
from unittest import TestCase

import fixfonts


class TestFixFonts(TestCase):
    @contextmanager
    def subTestMocked(self, subtest: str, *mocks):
        with self.subTest(subtest):
            yield
            for mock in mocks:
                mock.reset_mock()

    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.rename')
    def test_archive_dry_run(self, rename_mock, mkdir_mock) -> None:
        with self.subTestMocked("With archive directory", rename_mock, mkdir_mock):
            with patch('pathlib.Path.exists', return_value=True) as exists_mock:
                fixfonts.archive(Path("test.file"), dry_run=True)
                exists_mock.assert_called_once()
                mkdir_mock.assert_not_called()
                rename_mock.assert_not_called()

        with self.subTestMocked("No archive directory", rename_mock, mkdir_mock):
            with patch('pathlib.Path.exists', return_value=False) as exists_mock:
                fixfonts.archive(Path("test.file"), dry_run=True)
                exists_mock.assert_called_once()
                mkdir_mock.assert_called_once()
                rename_mock.assert_not_called()

    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.rename')
    def test_archive_live(self, rename_mock, mkdir_mock) -> None:
        with self.subTestMocked("With archive directory", rename_mock, mkdir_mock):
            with patch('pathlib.Path.exists', return_value=True) as exists_mock:
                fixfonts.archive(Path("test.file"), dry_run=False)
                exists_mock.assert_called_once()
                mkdir_mock.assert_not_called()
                rename_mock.assert_called_once_with(fixfonts.ARCHIVE_DIR / "test.file")

        with self.subTestMocked("No archive directory", rename_mock, mkdir_mock):
            with patch('pathlib.Path.exists', return_value=False) as exists_mock:
                fixfonts.archive(Path("test.file"), dry_run=False)
                exists_mock.assert_called_once()
                mkdir_mock.assert_called_once()
                rename_mock.assert_called_once_with(fixfonts.ARCHIVE_DIR / "test.file")

    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.mkdir')
    @patch('pathlib.Path.rename')
    def test_archive_dry_run_default(self, rename_mock, *mocks) -> None:
        fixfonts.archive(Path("test.file"))
        rename_mock.assert_called_once()

    def test_font_files_empty(self) -> None:
        self.assertEqual([], fixfonts.font_files([]))

    def test_font_files_filtered(self) -> None:
        with self.subTest("Eliminate all"):
            inputs = [Path(f) for f in ("aaa", "a.b", "a.otf.efg", "a.otf2")]
            self.assertEqual([], fixfonts.font_files(inputs))

        with self.subTest("Eliminate some"):
            inputs = [Path(f) for f in ("aaa", "a.otfX", "b.oTf", "c.ttf", "d.ttf.x")]
            self.assertEqual([Path("b.oTf"), Path("c.ttf")], fixfonts.font_files(inputs))

        with self.subTest("Return all"):
            inputs = [Path(f) for f in ("a.otf", "a.ttf", "b.OTf")]
            self.assertEqual(inputs, fixfonts.font_files(inputs))

    @patch('fixfonts.archive')
    def test_eliminate_dry_run(self, archive_mock) -> None:
        # We'll use these to add a test with len candidates > 1
        non_candidates = [Path(f) for f in ("foobar.ttf", "foo mono bar.ttf", "foo bar mono.ttf", "foo.otf")]
    
        with self.subTest("No patterns"):
            self.assertFalse(fixfonts.eliminate(Path("foo mono.ttf"), [], "mono", dry_run=True))
            archive_mock.assert_not_called()

        with self.subTest("No pattern match"):
            self.assertFalse(fixfonts.eliminate(Path("foo mono.ttf"), [Path("foo.ttf")], "monox", dry_run=True))
            archive_mock.assert_not_called()
            self.assertFalse(fixfonts.eliminate(Path("foo mono.ttf"), [Path("foo.ttf")] + non_candidates, "monox", dry_run=True))
            archive_mock.assert_not_called()

        with self.subTest("No pattern matched file"):
            self.assertFalse(fixfonts.eliminate(Path("foo mono.ttf"), [Path("foo2.txt")], "mono", dry_run=True))
            archive_mock.assert_not_called()
            self.assertFalse(fixfonts.eliminate(Path("foo mono.ttf"), non_candidates, "monox", dry_run=True))
            archive_mock.assert_not_called()

        with self.subTest("With match"):
            self.assertTrue(fixfonts.eliminate(Path("foo mono.ttf"), [Path("foo.ttf")], "mono", dry_run=True))
            archive_mock.assert_called_once_with(Path("foo mono.ttf"), dry_run=True)
            archive_mock.reset_mock()

            self.assertTrue(fixfonts.eliminate(Path("foo mono.ttf"), non_candidates + [Path("foo.ttf")], "mono", dry_run=True))
            archive_mock.assert_called_once_with(Path("foo mono.ttf"), dry_run=True)
            archive_mock.reset_mock()

            self.assertTrue(fixfonts.eliminate(Path("foo mono.ttf"), [Path("foo.ttf")] + non_candidates, "mono", dry_run=True))
            archive_mock.assert_called_once_with(Path("foo mono.ttf"), dry_run=True)
            archive_mock.reset_mock()

    @patch('fixfonts.archive')
    def test_eliminate_live(self, archive_mock) -> None:
        with self.subTest("With match"):
            self.assertTrue(fixfonts.eliminate(Path("foo mono.ttf"), [Path("foo.ttf")], "mono"))
            archive_mock.assert_called_once_with(Path("foo mono.ttf"), dry_run=False)

    @patch('os.scandir', return_value='scanned')
    @patch('fixfonts.archive')
    @patch('fixfonts.font_files', return_value=[Path(f) for f in ('foo.otf', 'foo.ttf', 'foo Complete.ttf', 'foo Complete Nerd Font Mono.otf')])
    def test_scan_fonts(self, font_files_mock, archive_mock, scandir_mock) -> None:
        # We expected that 'foo Mono.ttf' and 'foo Mono Nerd font Mono.ttf' can be removed.
        self.assertEqual(1, fixfonts.scan_fonts('.'))
        scandir_mock.assert_called_once_with('.')
        font_files_mock.assert_called_once_with('scanned')
        self.assertEqual(1, archive_mock.call_count)
        archive_mock.assert_any_call(Path('foo Complete.ttf'), dry_run=False)

    @patch('os.scandir', return_value='scanned')
    @patch('fixfonts.archive')
    @patch('fixfonts.font_files', return_value=[Path(f) for f in ('LGC.otf', 'LGC Nerd Font.otf', 'LGC Nerd Font Complete.otf')])
    def test_scan_fonts_multi_match(self, font_files_mock, archive_mock, scandir_mock) -> None:
        # We expected that 'foo Mono.ttf' and 'foo Mono Nerd font Mono.ttf' can be removed.
        self.assertEqual(2, fixfonts.scan_fonts('.'))
        scandir_mock.assert_called_once_with('.')
        font_files_mock.assert_called_once_with('scanned')
        self.assertEqual(2, archive_mock.call_count)
        archive_mock.assert_any_call(Path('LGC Nerd Font.otf'), dry_run=False)
        archive_mock.assert_any_call(Path('LGC Nerd Font Complete.otf'), dry_run=False)

    @patch('os.scandir', return_value='scanned')
    @patch('pathlib.Path.exists')
    @patch('pathlib.Path.rename')
    @patch('fixfonts.archive')
    @patch('fixfonts.font_files')
    def test_down_names(self, font_files_mock, archive_mock, rename_mock, exists_mock, *mocks) -> None:
        returns = [False, True]
        exists_mock.side_effect = lambda: returns.pop(0)

        font_files_mock.return_value = [Path(f) for f in ('foo.ttf', 'foo.otf', 'foo Complete.otf', 'foo Complete Windows Compatible.otf')]

        with self.assertLogs(fixfonts.LOG, logging.WARNING) as cm:
            self.assertEqual(2, fixfonts.down_names())
            self.assertEqual(2, exists_mock.call_count)
            # if we weren't mocking archive, there would be two calls to rename
            self.assertEqual(1, rename_mock.call_count)
            archive_mock.assert_called_once_with(Path('foo Complete Windows Compatible.otf'), dry_run=False)

        self.assertEqual(["WARNING:fixfonts:Can't down-name foo Complete Windows Compatible.otf -> foo.otf: file exists."], cm.output)

