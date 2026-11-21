from views.dashboard import _snapshot_cards


def test_greenhouse_snapshot_uses_latest_saved_values():
    analysis = {
        "temperature": 30.0,
        "humidity": 80.0,
        "soil_moisture": 70.0,
        "light_intensity": 550.0,
        "co2": 650.0,
    }

    cards = _snapshot_cards(analysis, "English", lambda key: key)

    assert [card["value"] for card in cards] == ["30°C", "80%", "70%"]
    assert all(card["status"] for card in cards)
    assert all(card["badge_class"] in {"badge-ok", "badge-warn"} for card in cards)
