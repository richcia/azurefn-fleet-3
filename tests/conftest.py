from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def disable_managed_identity_lookup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_IDENTITY_DISABLE_MANAGED_IDENTITY", "true")
