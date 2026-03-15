"""
Unit tests for clear-sky detection utilities.
晴空检测工具单元测试。
"""

import os
import sys
import unittest

import numpy as np
import pandas as pd

# Ensure 'src' is in path / 确保 'src' 在路径中
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from bsrn.utils.cs_detection import (
    reno_csd,
    ineichen_csd,
    lefevre_csd,
    brightsun_csd,
    detect_clearsky,
)


class TestCSDMethods(unittest.TestCase):
    """Basic tests for CSD method outputs."""

    def setUp(self):
        self.times = pd.date_range("2024-07-01 00:00", periods=360, freq="1min", tz="UTC")
        x = np.linspace(0.0, np.pi, len(self.times))
        self.ghi_clear = 900.0 * np.maximum(np.sin(x), 0.0)
        self.ghi = self.ghi_clear * (0.88 + 0.06 * np.sin(3.0 * x))
        self.dhi_clear = self.ghi_clear * 0.2
        self.dhi = self.ghi * (0.28 + 0.03 * np.cos(2.0 * x))
        self.zenith = 80.0 - 55.0 * np.maximum(np.sin(x), 0.0)
        self.ghi_extra = np.maximum(self.ghi_clear / np.maximum(np.cos(np.radians(self.zenith)), 0.1), 1.0)

    def _check_standard_output(self, out):
        self.assertIsInstance(out, pd.DataFrame)
        self.assertIn("is_clearsky", out.columns)
        self.assertIn("cloud_flag", out.columns)
        self.assertEqual(len(out), len(self.times))
        self.assertTrue(out.index.equals(self.times))

    def test_reno_output(self):
        out = reno_csd(self.ghi, self.ghi_clear, times=self.times, return_diagnostics=True)
        self._check_standard_output(out)
        self.assertIn("c1", out.columns)

    def test_ineichen_output(self):
        out = ineichen_csd(
            self.ghi,
            self.ghi_extra,
            self.zenith,
            times=self.times,
            return_diagnostics=True,
        )
        self._check_standard_output(out)
        self.assertIn("kt_prime", out.columns)

    def test_lefevre_output(self):
        out = lefevre_csd(
            self.ghi,
            self.dhi,
            self.ghi_extra,
            self.zenith,
            times=self.times,
            return_diagnostics=True,
        )
        self._check_standard_output(out)
        self.assertIn("KTp", out.columns)

    def test_brightsun_output(self):
        out = brightsun_csd(
            self.zenith,
            self.ghi,
            self.ghi_clear,
            self.dhi,
            self.dhi_clear,
            self.times,
            return_diagnostics=True,
        )
        self._check_standard_output(out)
        self.assertIn("cloud_bni", out.columns)

    def test_wrapper_dispatch(self):
        out_reno = detect_clearsky(method="reno", ghi=self.ghi, ghi_clear=self.ghi_clear, times=self.times)
        self._check_standard_output(out_reno)

        out_ineichen = detect_clearsky(
            method="ineichen",
            ghi=self.ghi,
            ghi_extra=self.ghi_extra,
            zenith=self.zenith,
            times=self.times,
        )
        self._check_standard_output(out_ineichen)

        out_lefevre = detect_clearsky(
            method="lefevre",
            ghi=self.ghi,
            dhi=self.dhi,
            ghi_extra=self.ghi_extra,
            zenith=self.zenith,
            times=self.times,
        )
        self._check_standard_output(out_lefevre)

        out_brightsun = detect_clearsky(
            method="brightsun",
            zenith=self.zenith,
            ghi=self.ghi,
            ghi_clear=self.ghi_clear,
            dhi=self.dhi,
            dhi_clear=self.dhi_clear,
            times=self.times,
        )
        self._check_standard_output(out_brightsun)

    def test_invalid_method(self):
        with self.assertRaises(ValueError):
            detect_clearsky(method="unknown_method", ghi=self.ghi, ghi_clear=self.ghi_clear, times=self.times)


if __name__ == "__main__":
    unittest.main()
