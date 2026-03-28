"""Smoke tests for critical imports used by the frozen Windows build."""

import importlib


def test_drm_module_imports_without_runtime_secrets():
    drm = importlib.import_module("src.core.drm")

    assert callable(drm.get_widevine_keys)
    assert drm._EMBEDDED_WVD == ""


def test_downloader_imports_drm_dependency():
    downloader = importlib.import_module("src.core.downloader")

    assert callable(downloader.get_widevine_keys)
    assert downloader.get_widevine_keys.__module__ == "src.core.drm"
