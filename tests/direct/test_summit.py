"""Direct-mode tests for the Summit contract."""

import json

CONTRACT = "contracts/summit.py"

T0 = "2026-01-01T00:00:00Z"
T_JUST_AFTER = "2026-01-01T00:02:00Z"  # 2 min later - inside the cooldown
T_AFTER_COOLDOWN = "2026-01-01T00:06:00Z"  # 6 min later - past the 300s cooldown
T_MUCH_LATER = "2026-01-01T01:00:00Z"


def _mock_front_page(vm, headline: str, points: int):
    # mock_web/mock_llm are additive, not replacing - clear any prior
    # registration first so each call to this helper fully controls what
    # the next refresh() call sees, even across multiple refreshes in one
    # test.
    vm.clear_mocks()
    vm.mock_web(
        r"news\.ycombinator\.com",
        {"status": 200, "body": f"Hacker News\n1. {headline} - {points} points\n"},
    )
    vm.mock_llm(
        r".*Hacker News's live front page.*",
        json.dumps({"headline": headline, "points": points}),
    )


def test_get_current_champion_before_any_refresh(direct_deploy):
    contract = direct_deploy(CONTRACT)
    champion = contract.get_current_champion()
    assert champion["headline"] == ""
    assert champion["points"] == 0
    assert champion["since"] == 0


def test_get_history_empty_initially(direct_deploy):
    contract = direct_deploy(CONTRACT)
    assert contract.get_history() == []


def test_get_min_refresh_interval_seconds(direct_deploy):
    contract = direct_deploy(CONTRACT)
    assert contract.get_min_refresh_interval_seconds() == 300


def test_refresh_first_ever_crowns_current_leader(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)

    _mock_front_page(direct_vm, "Show HN: I built a thing", 289)
    contract.refresh()

    champion = contract.get_current_champion()
    assert champion["headline"] == "Show HN: I built a thing"
    assert champion["points"] == 289
    assert champion["since"] > 0
    assert contract.get_history() == []


def test_refresh_same_leader_updates_points_no_history_entry(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_front_page(direct_vm, "Show HN: I built a thing", 289)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_front_page(direct_vm, "Show HN: I built a thing", 340)
    contract.refresh()

    champion = contract.get_current_champion()
    assert champion["headline"] == "Show HN: I built a thing"
    assert champion["points"] == 340
    # Still the same reign - no handoff, so no history entry yet.
    assert contract.get_history() == []


def test_refresh_handoff_archives_previous_champion(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_front_page(direct_vm, "Show HN: I built a thing", 289)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_front_page(direct_vm, "A misalignment of AI in mathematics", 512)
    contract.refresh()

    champion = contract.get_current_champion()
    assert champion["headline"] == "A misalignment of AI in mathematics"
    assert champion["points"] == 512

    history = contract.get_history()
    assert len(history) == 1
    assert history[0].headline == "Show HN: I built a thing"
    assert history[0].points == 289
    assert history[0].since > 0
    assert history[0].until > history[0].since


def test_multiple_handoffs_build_history_in_order(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)

    direct_vm.warp(T0)
    _mock_front_page(direct_vm, "Show HN: I built a thing", 289)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_front_page(direct_vm, "A misalignment of AI in mathematics", 512)
    contract.refresh()

    direct_vm.warp(T_MUCH_LATER)
    _mock_front_page(direct_vm, "GrapheneOS Messages app is released", 601)
    contract.refresh()

    history = contract.get_history()
    assert [h.headline for h in history] == [
        "Show HN: I built a thing",
        "A misalignment of AI in mathematics",
    ]
    assert contract.get_current_champion()["headline"] == "GrapheneOS Messages app is released"


def test_refresh_too_soon_fails(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_front_page(direct_vm, "Show HN: I built a thing", 289)
    contract.refresh()

    direct_vm.warp(T_JUST_AFTER)
    _mock_front_page(direct_vm, "A misalignment of AI in mathematics", 512)
    with direct_vm.expect_revert("Refreshed too recently"):
        contract.refresh()

    # The premature call must not have changed anything.
    assert contract.get_current_champion()["headline"] == "Show HN: I built a thing"
    assert contract.get_history() == []


def test_refresh_after_cooldown_succeeds(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_front_page(direct_vm, "Show HN: I built a thing", 289)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_front_page(direct_vm, "A misalignment of AI in mathematics", 512)
    contract.refresh()

    assert contract.get_current_champion()["headline"] == "A misalignment of AI in mathematics"


def test_refresh_with_no_identifiable_leader_fails(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    direct_vm.mock_web(r"news\.ycombinator\.com", {"status": 200, "body": "empty page"})
    direct_vm.mock_llm(
        r".*Hacker News's live front page.*",
        json.dumps({"headline": "", "points": 0}),
    )

    with direct_vm.expect_revert("Could not identify a current"):
        contract.refresh()

    assert contract.get_current_champion()["headline"] == ""
