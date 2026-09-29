from contextlib import ExitStack, contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from flask import Response

import subscription_api as api


@pytest.mark.parametrize("agent", ["", "Mozilla/5.0", "curl/8.0", "TelegramBot (like TwitterBot)"])
@pytest.mark.parametrize("state", [None, "revoked", "allowed"])
def test_unbound_probe_never_creates_or_restores_slot(agent, state):
    with route_mocks(state=state) as mocks:
        response = api.app.test_client().get(
            "/sub/probe_subscription_123", headers={"User-Agent": agent}
        )
        assert response.status_code == 200
        assert response.data == b"legacy"
        mocks["register_import_device"].assert_not_called()
        mocks["adopt_import_device_identity"].assert_not_called()
        mocks["get_import_device_access_state"].assert_not_called()


@pytest.mark.parametrize("agent", ["Happ/2.9", "INCY/1.0", "Hiddify/2.0"])
def test_recognized_client_still_registers_recovery_slot(agent):
    with route_mocks() as mocks:
        mocks["get_import_device_access_state"].side_effect = [None, "allowed"]
        response = api.app.test_client().get(
            "/sub/probe_subscription_123", headers={"User-Agent": agent}
        )
        assert response.data == b"live"
        mocks["register_import_device"].assert_called_once()


def test_generic_bound_alias_preserves_access():
    with route_mocks() as mocks:
        mocks["resolve_device_subscription"].return_value = {
            "sub_id": "probe_subscription_123", "state": "allowed",
            "platform": "ios", "display_name": "iPhone",
        }
        response = api.app.test_client().get("/sub/bound_subscription_123")
        assert response.data == b"live"
        mocks["register_import_device"].assert_not_called()


def test_generic_head_is_read_only():
    with route_mocks() as mocks:
        response = api.app.test_client().head("/sub/probe_subscription_123")
        assert response.status_code == 200
        mocks["_prepare_headers_only_subscription"].assert_called_once()
        mocks["register_import_device"].assert_not_called()


def test_generic_with_stable_hwid_preserves_client_recovery():
    with route_mocks() as mocks:
        mocks["get_import_device_access_state"].side_effect = [None, "allowed"]
        response = api.app.test_client().get(
            "/sub/probe_subscription_123", headers={"X-Hwid": "stable-client-123"}
        )
        assert response.data == b"live"
        mocks["register_import_device"].assert_called_once()


@contextmanager
def route_mocks(state=None):
    stack = ExitStack()
    values = {
        "resolve_device_subscription": None,
        "get_active_key_by_subscription_id": SimpleNamespace(has_available_traffic=True),
        "subscription_requires_device_token": True,
        "get_subscription_device_limit": 3,
        "get_import_device_access_state": state,
        "subscription_device_slots_full": False,
        "register_import_device": "test-device-alias",
        "adopt_import_device_identity": False,
        "_prepare_device_limit_subscription": "legacy",
        "_prepare_headers_only_subscription": "headers",
        "_resolve_subscription_source": SimpleNamespace(
            prepared="live", source="remnawave", fallback_reason=None
        ),
    }
    mocks = {name: stack.enter_context(patch.object(api, name, return_value=value))
             for name, value in values.items()}
    stack.enter_context(patch.object(api.TOKEN_RATE_LIMITER, "allow", return_value=(True, 0)))
    stack.enter_context(patch.object(api.IP_RATE_LIMITER, "allow", return_value=(True, 0)))
    stack.enter_context(patch.object(api, "_response_from_prepared",
                                     side_effect=lambda prepared, *args: Response(prepared)))
    with stack:
        yield mocks
