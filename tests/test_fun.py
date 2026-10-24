import datetime
import logging
import sys
import threading
import time
import types
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

import pytz

# `tzlocal` 是项目的运行时依赖，但精简 CI 环境可能只安装直接依赖。
# 为本单元测试提供确定性的本地时区，避免测试结果依赖执行机器。
if "tzlocal" not in sys.modules:
    tzlocal_stub = types.ModuleType("tzlocal")
    tzlocal_stub.get_localzone = lambda: "UTC"
    sys.modules["tzlocal"] = tzlocal_stub

from chanlun import fun


class FunTests(unittest.TestCase):
    def test_timestamp_conversion_honors_requested_timezone(self):
        timestamp = 0
        shanghai = pytz.timezone("Asia/Shanghai")
        utc = pytz.UTC

        self.assertEqual(fun.timeint_to_str(timestamp, tz=utc), "1970-01-01 00:00:00")
        self.assertEqual(
            fun.timeint_to_str(timestamp, tz=shanghai), "1970-01-01 08:00:00"
        )
        self.assertIsNotNone(fun.timeint_to_datetime(timestamp, tz=utc).tzinfo)

    def test_string_conversion_is_timezone_aware_and_round_trips(self):
        tz = pytz.timezone("Asia/Shanghai")
        value = "2026-07-12 09:30:00"
        parsed = fun.str_to_datetime(value, tz=tz)

        self.assertEqual(parsed.utcoffset(), datetime.timedelta(hours=8))
        self.assertEqual(
            fun.timeint_to_str(fun.str_to_timeint(value, tz=tz), tz=tz), value
        )

    def test_singleton_is_safe_during_concurrent_first_access(self):
        creations = 0
        creations_lock = threading.Lock()

        @fun.singleton
        class Example:
            def __init__(self):
                nonlocal creations
                time.sleep(0.01)
                with creations_lock:
                    creations += 1

        instances = []
        threads = [
            threading.Thread(target=lambda: instances.append(Example()))
            for _ in range(20)
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual(creations, 1)
        self.assertEqual(len({id(instance) for instance in instances}), 1)

    def test_logger_has_distinct_stream_and_file_handlers(self):
        with TemporaryDirectory() as directory, mock.patch.object(
            fun, "get_data_path", return_value=Path(directory)
        ):
            logger_name = "test-fun.log"
            logger = logging.getLogger(logger_name)
            logger.handlers.clear()
            result = fun.get_logger(logger_name)

            self.assertTrue(
                any(
                    isinstance(handler, logging.StreamHandler)
                    and not isinstance(handler, logging.FileHandler)
                    for handler in result.handlers
                )
            )
            self.assertTrue(
                any(isinstance(handler, logging.FileHandler) for handler in result.handlers)
            )


if __name__ == "__main__":
    unittest.main()
