import pathlib
import sys

import pytest

# Ensure "src" is on the path so we can import project modules without installation
PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.append(str(PROJECT_ROOT / "src"))

from tui.utils.json_detector import json_detector


def test_split_content_no_json():
    content = "Hello there!"
    split = json_detector.split_content(content)
    assert not split.has_json
    assert split.prefix_text == content


def test_split_content_stray_brace():
    content = "Look at {"
    split = json_detector.split_content(content)
    assert not split.has_json


def test_split_content_partial_json():
    content = "Intro {\"a\": 1"
    split = json_detector.split_content(content)
    assert split.has_json
    assert not split.is_complete_json
    assert split.prefix_text == "Intro"
