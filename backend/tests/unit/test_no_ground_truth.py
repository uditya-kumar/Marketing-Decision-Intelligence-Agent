"""Guard (task 2.6): only evaluation/ may read the generator's ground truth.

If the backend could see which scenarios were injected, detection and diagnosis
results would be meaningless, so no backend source file may even mention it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

import mdia

pytestmark = pytest.mark.unit

SOURCE_ROOT = Path(mdia.__file__).resolve().parent


def test_no_backend_module_references_ground_truth() -> None:
    offenders = [
        path.relative_to(SOURCE_ROOT).as_posix()
        for path in SOURCE_ROOT.rglob("*.py")
        if "ground_truth" in path.read_text(encoding="utf-8").casefold()
    ]

    assert offenders == []
