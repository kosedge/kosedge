"""Pytest config and fixtures for pipeline tests."""
import pytest


@pytest.fixture
def fixture_dir():
    """Path to tests_pipeline/fixtures (static files)."""
    from pathlib import Path
    return Path(__file__).resolve().parent / "fixtures"
