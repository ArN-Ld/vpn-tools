import vpn_tools.mullvad_coordinates as mc


def test_resolve_location_input_city_only_case_insensitive():
    canonical, coords, matches = mc.resolve_location_input("pArIs")

    assert canonical == "Paris, France"
    assert isinstance(coords, tuple)
    assert len(coords) == 2
    assert canonical in matches


def test_resolve_location_input_full_location_case_insensitive():
    canonical, coords, matches = mc.resolve_location_input("paris, france")

    assert canonical == "Paris, France"
    assert isinstance(coords, tuple)
    assert len(coords) == 2
    assert matches == ["Paris, France"]