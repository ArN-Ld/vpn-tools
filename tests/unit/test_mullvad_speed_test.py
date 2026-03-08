import pytest

import vpn_tools.mullvad_speed_test as mst


class DummyUI:
    def __init__(self, interactive):
        self.interactive = interactive

    def info(self, _msg):
        pass

    def success(self, _msg):
        pass

    def warning(self, _msg):
        pass

    def error(self, _msg):
        pass


def test_handle_geocode_failure_uses_default_coords():
    tester = mst.MullvadTester.__new__(mst.MullvadTester)
    tester.default_coords = (48.8566, 2.3522)
    tester.coords_cache = {}
    tester.ui = DummyUI(interactive=False)
    tester._save_coords_cache = lambda: None
    tester.log_and_warning = lambda _msg: None

    coords = tester._handle_geocode_failure("Paris, France")

    assert coords == (48.8566, 2.3522)
    assert tester.coords_cache["Paris, France"] == (48.8566, 2.3522)


def test_handle_geocode_failure_non_interactive_without_defaults_raises():
    tester = mst.MullvadTester.__new__(mst.MullvadTester)
    tester.default_coords = None
    tester.coords_cache = {}
    tester.ui = DummyUI(interactive=False)

    with pytest.raises(ValueError, match="Unable to geocode location in non-interactive mode"):
        tester._handle_geocode_failure("Unknown")


def test_main_non_interactive_skips_interactive_helpers(monkeypatch):
    called = {
        "custom": False,
        "summary": False,
        "run_tests": False,
    }

    class FakeTester:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def run_tests(self, protocol, max_servers, max_distance):
            called["run_tests"] = True
            assert protocol == "WireGuard"
            assert max_servers == 1
            assert max_distance is None

    monkeypatch.setattr(mst, "check_dependencies", lambda: [])
    monkeypatch.setattr(mst, "check_optional_dependencies", lambda: [])
    monkeypatch.setattr(mst, "print_welcome", lambda _ui: None)
    monkeypatch.setattr(mst, "MullvadTester", FakeTester)

    def fake_custom(args, _ui):
        called["custom"] = True
        return args

    def fake_summary(_args, _ui, countdown_seconds=5):
        called["summary"] = True

    monkeypatch.setattr(mst, "input_custom_parameters", fake_custom)
    monkeypatch.setattr(mst, "display_parameters_summary", fake_summary)
    monkeypatch.setattr(
        mst.sys,
        "argv",
        [
            "mullvad_speed_test.py",
            "--non-interactive",
            "--location",
            "Paris, France",
            "--default-lat",
            "48.8566",
            "--default-lon",
            "2.3522",
            "--max-servers",
            "1",
            "--no-open-results",
        ],
    )

    mst.main()

    assert called["custom"] is False
    assert called["summary"] is False
    assert called["run_tests"] is True


def test_get_location_coordinates_uses_local_city_lookup(monkeypatch):
    tester = mst.MullvadTester.__new__(mst.MullvadTester)
    tester.reference_location = "pArIs"
    tester.default_coords = None
    tester.coords_cache = {}
    tester.ui = DummyUI(interactive=False)
    tester._save_coords_cache = lambda: None
    tester.log_and_info = lambda _msg: None
    tester.log_and_warning = lambda _msg: None

    monkeypatch.setattr(
        mst,
        "resolve_location_input",
        lambda _loc: ("Paris, France", (48.8566, 2.3522), ["Paris, France"]),
    )

    def _unexpected_geopy():
        raise AssertionError("geopy should not be called when local city lookup matches")

    monkeypatch.setattr(mst, "load_geo_modules", _unexpected_geopy)

    coords = mst.MullvadTester._get_location_coordinates(tester)

    assert coords == (48.8566, 2.3522)
    assert tester.reference_location == "Paris, France"
    assert tester.coords_cache["Paris, France"] == (48.8566, 2.3522)
