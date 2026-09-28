"""Sample agents test — runs offline (no LLM, no DB).

Real graph tests (Phase 8+) use a fake chat model; this placeholder just proves the
``agents`` test folder and marker are wired up.
"""

from __future__ import annotations

import pytest


@pytest.mark.agents
def test_agents_marker_runs_offline() -> None:
    assert True
