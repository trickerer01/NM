# coding=UTF-8
"""
Author: trickerer (https://github.com/trickerer, https://github.com/trickerer01)
"""
#########################################
#
#

from asyncio import run as run_async
from io import StringIO
from os import path, remove as remove_file, stat
from tempfile import gettempdir
from unittest import TestCase
from unittest.mock import patch

from cmdargs import prepare_arglist
# noinspection PyProtectedMember
from config import BaseConfig
from defs import DOWNLOAD_MODE_TOUCH, QUALITIES, QUALITY_480P
from downloader import VideoDownloadWorker
from dscanner import VideoScanWorker
# noinspection PyProtectedMember
from ids import main as ids_main, main_sync as ids_main_sync
from logger import Log
# noinspection PyProtectedMember
from pages import main as pages_main, main_sync as pages_main_sync
# noinspection PyProtectedMember
from path_util import found_filenames_dict
from rex import prepare_regex_fullmatch
# noinspection PyProtectedMember
from tagger import normalize_wtag, match_text
from util import normalize_path
from version import APP_NAME, APP_VERSION

RUN_CONN_TESTS = 0


def set_up_test(log=False) -> None:
    VideoDownloadWorker._instance = None
    VideoScanWorker._instance = None
    found_filenames_dict.clear()
    Log._disabled = not log


class CmdTests(TestCase):
    def test_output_version_pages(self):
        set_up_test()
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run_async(pages_main(['--version']))
            self.assertEqual(f'{APP_NAME} {APP_VERSION}', stdout.getvalue().strip('\n'))
        print(f'{self._testMethodName} passed')

    def test_output_version_ids(self):
        set_up_test()
        with patch('sys.stdout', new_callable=StringIO) as stdout:
            run_async(ids_main(['--version']))
            self.assertEqual(f'{APP_NAME} {APP_VERSION}', stdout.getvalue().strip('\n'))
        print(f'{self._testMethodName} passed')

    # @mock_stderr
    # def test_cmd_base(self, stderr: StringIO):
    #     set_up_test()
    #     self.assertRaises(HelpPrintExitException, prepare_arglist, ['cmd', '--help'], True)
    #     self.assertRaises(HelpPrintExitException, prepare_arglist, ['cmd', '-start', '1'], True)
    #     self.assertRaises(HelpPrintExitException, prepare_arglist, ['cmd', '-start', '1', '-pages'], True)
    #     self.assertNotEqual('', stderr.getvalue().strip('\n'))

    def test_cmd_pages(self):
        set_up_test()
        parsed1 = prepare_arglist(['cmd', '-get_maxid'], True)
        c1 = BaseConfig()
        c1.read(parsed1, True)
        self.assertTrue(c1.get_maxid)
        parsed2 = prepare_arglist(['-start', '2', '-pages', '1', '-uploader', '1234', '(2d~vr)', '--skip-empty-lists', '-script',
                                   'a: 2d; b: 3d; c: a2 -2d; d: * -utp always', '-naming', 'prefix|quality', '-log', 'warn'], True)
        c2 = BaseConfig()
        c2.read(parsed2, True)
        self.assertEqual(17, c2.naming_flags)
        self.assertEqual(8, c2.logging_flags)
        self.assertEqual(1, len(c2.extra_tags))
        self.assertEqual(4, len(c2.scenario))
        self.assertEqual('1234', c2.uploader)
        self.assertEqual('', c2.search)
        self.assertIsNone(c2.search_rule_art)
        self.assertIsNone(c2.use_id_sequence)
        self.assertTrue(c2.skip_empty_lists)
        parsed3 = prepare_arglist(['-playlist_name', 'commodified', '-start', '3', '-pages', '2', '-quality', '480p', '-dnoempty',
                                   '-minscore', '12', '-continue', '-unfinish', '-tdump', '-ddump', '-cdump', '-sdump'], True)
        c3 = BaseConfig()
        c3.read(parsed3, True)
        self.assertEqual('commodified', c3.playlist_name)
        self.assertEqual(3, c3.start)
        self.assertEqual(4, c3.end)
        self.assertEqual(QUALITIES[3], c3.quality)
        self.assertEqual(QUALITY_480P, c3.quality)
        self.assertEqual('480p', c3.quality)
        self.assertEqual(12, c3.min_score)
        self.assertTrue(c3.continue_mode)
        self.assertTrue(c3.keep_unfinished)
        self.assertTrue(c3.save_tags)
        self.assertTrue(c3.save_descriptions)
        self.assertTrue(c3.save_comments)
        self.assertTrue(c3.save_screenshots)
        self.assertTrue(c3.skip_empty_lists)
        print(f'{self._testMethodName} passed')

    def test_cmd_ids(self):
        set_up_test()
        parsed1 = prepare_arglist(['cmd', '-seq'], False)
        c1 = BaseConfig()
        c1.read(parsed1, False)
        self.assertTrue(c1.use_id_sequence)
        parsed2 = prepare_arglist(['-start', '1000', '-end', '999', '(a2~4k)', '(2d~vr)', '-dmode', 'touch', '--store-continue-cmdfile',
                                   '-lookahead', '100',
                                   '-script', 'a: 2d; b: 3d; c: a2 -2d; d: * -utp always', '-naming', '0x8', '-log', 'trace'], False)
        c2 = BaseConfig()
        c2.read(parsed2, False)
        self.assertEqual(8, c2.naming_flags)
        self.assertEqual(1, c2.logging_flags)
        self.assertEqual(2, len(c2.extra_tags))
        self.assertEqual(4, len(c2.scenario))
        self.assertEqual(100, c2.lookahead)
        self.assertEqual(DOWNLOAD_MODE_TOUCH, c2.download_mode)
        self.assertTrue(c2.store_continue_cmdfile)
        print(f'{self._testMethodName} passed')

    def test_cmd_wtags(self):
        set_up_test()
        parsed1 = prepare_arglist(['-start', '1', '-pages', '5',
                                   '-*[1`-5]`+`(finger{1`,3}|girl`)s`?`.`*',
                                   '-*`[1`-5`]`+`(finger`{1`,3`}`|`girl`)s`?`.`*``'], True)
        c1 = BaseConfig()
        c1.read(parsed1, True)
        self.assertEqual(r'^\-.*[1-5]+(?:finger{1,3}|girl)s?.*$', prepare_regex_fullmatch(normalize_wtag(c1.extra_tags[0])).pattern)
        self.assertEqual(r'^\-.*[1-5]+(?:finger{1,3}|girl)s?.*$', prepare_regex_fullmatch(normalize_wtag(c1.extra_tags[1])).pattern)
        parsed2 = prepare_arglist(['-start', '1', '-pages', '5', 'trigger`(s|ed|ing`)*'], True)
        c2 = BaseConfig()
        c2.read(parsed2, True)
        self.assertIsNotNone(match_text(c2.extra_tags[0], 'a triggered bluff'))
        print(f'{self._testMethodName} passed')


class DownloadTests(TestCase):
    def test_ids_touch(self):
        if not RUN_CONN_TESTS:
            return
        set_up_test()
        tempdir = normalize_path(gettempdir())
        tempfile_id = '85606'
        tempfile_ext = 'mp4'
        tempfile_fullpath = f'{tempdir}{tempfile_id}.{tempfile_ext}'
        arglist1 = ['-path', tempdir, '-start', tempfile_id, '-dmode', 'touch', '-naming', 'none', '-quality', '360p', '-log', 'trace']
        ids_main_sync(arglist1)
        self.assertTrue(path.isfile(tempfile_fullpath))
        st = stat(tempfile_fullpath)
        self.assertEqual(0, st.st_size)
        remove_file(tempfile_fullpath)
        print(f'{self._testMethodName} passed')

    def test_pages_touch(self):
        if not RUN_CONN_TESTS:
            return
        set_up_test()
        tempdir = normalize_path(gettempdir())
        tempfile_id = '85716'
        tempfile_ext = 'mp4'
        tempfile_fullpath = f'{tempdir}{tempfile_id}.{tempfile_ext}'
        arglist1 = ['-path', tempdir, '-pages', '999', '-dmode', 'touch', '-naming', 'none', '-quality', '360p', '-log', 'trace',
                    '-begin_id', tempfile_id, '-stop_id', tempfile_id, '-search', 'queen+nualia+played']
        pages_main_sync(arglist1)
        self.assertTrue(path.isfile(tempfile_fullpath))
        st = stat(tempfile_fullpath)
        self.assertEqual(0, st.st_size)
        remove_file(tempfile_fullpath)
        print(f'{self._testMethodName} passed')

    def test_ids_full(self):
        if not RUN_CONN_TESTS:
            return
        set_up_test()
        tempdir = normalize_path(gettempdir())
        tempfile_id = '86033'
        tempfile_ext = 'mp4'
        tempfile_fullpath = f'{tempdir}{tempfile_id}.{tempfile_ext}'
        arglist1 = ['-path', tempdir, '-start', tempfile_id, '-dmode', 'full', '-naming', 'none', '-quality', '360p', '-log', 'trace']
        ids_main_sync(arglist1)
        self.assertTrue(path.isfile(tempfile_fullpath))
        st = stat(tempfile_fullpath)
        self.assertGreater(st.st_size, 0)
        remove_file(tempfile_fullpath)
        print(f'{self._testMethodName} passed')

    def test_pages_full(self):
        if not RUN_CONN_TESTS:
            return
        set_up_test()
        tempdir = normalize_path(gettempdir())
        tempfile_id = '86045'
        tempfile_ext = 'mp4'
        tempfile_fullpath = f'{tempdir}{tempfile_id}.{tempfile_ext}'
        arglist1 = ['-path', tempdir, '-pages', '999', '-dmode', 'full', '-naming', 'none', '-quality', '360p', '-log', 'trace',
                    '-begin_id', tempfile_id, '-stop_id', tempfile_id, '-search', 'isobel']
        pages_main_sync(arglist1)
        self.assertTrue(path.isfile(tempfile_fullpath))
        st = stat(tempfile_fullpath)
        self.assertGreater(st.st_size, 0)
        remove_file(tempfile_fullpath)
        print(f'{self._testMethodName} passed')

#
#
#########################################
