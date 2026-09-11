"""Direct-mode tests for the Summit contract."""

import json

CONTRACT = "contracts/summit.py"

T0 = "2026-01-01T00:00:00Z"
T_JUST_AFTER = "2026-01-01T00:02:00Z"  # 2 min later - inside the cooldown
T_AFTER_COOLDOWN = "2026-01-01T00:06:00Z"  # 6 min later - past the 300s cooldown
T_MUCH_LATER = "2026-01-01T01:00:00Z"


def _mock_leaderboard(vm, name: str, points: int):
    # mock_web/mock_llm are additive, not replacing - clear any prior
    # registration first so each call to this helper fully controls what
    # the next refresh() call sees, even across multiple refreshes in one
    # test.
    vm.clear_mocks()
    vm.mock_web(
        r"portal\.genlayer\.foundation",
        {"status": 200, "body": f"Leaderboard\n1. {name} - {points} GLP\n"},
    )
    vm.mock_llm(
        r".*live leaderboard page.*",
        json.dumps({"name": name, "points": points}),
    )


def test_get_current_champion_before_any_refresh(direct_deploy):
    contract = direct_deploy(CONTRACT)
    champion = contract.get_current_champion()
    assert champion["name"] == ""
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

    _mock_leaderboard(direct_vm, "Alexei Denisov", 28900)
    contract.refresh()

    champion = contract.get_current_champion()
    assert champion["name"] == "Alexei Denisov"
    assert champion["points"] == 28900
    assert champion["since"] > 0
    assert contract.get_history() == []


def test_refresh_same_leader_updates_points_no_history_entry(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_leaderboard(direct_vm, "Alexei Denisov", 28900)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_leaderboard(direct_vm, "Alexei Denisov", 29500)
    contract.refresh()

    champion = contract.get_current_champion()
    assert champion["name"] == "Alexei Denisov"
    assert champion["points"] == 29500
    # Still the same reign - no handoff, so no history entry yet.
    assert contract.get_history() == []


def test_refresh_handoff_archives_previous_champion(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_leaderboard(direct_vm, "Alexei Denisov", 28900)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_leaderboard(direct_vm, "action", 30000)
    contract.refresh()

    champion = contract.get_current_champion()
    assert champion["name"] == "action"
    assert champion["points"] == 30000

    history = contract.get_history()
    assert len(history) == 1
    assert history[0].name == "Alexei Denisov"
    assert history[0].points == 28900
    assert history[0].since > 0
    assert history[0].until > history[0].since


def test_multiple_handoffs_build_history_in_order(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)

    direct_vm.warp(T0)
    _mock_leaderboard(direct_vm, "Alexei Denisov", 28900)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_leaderboard(direct_vm, "action", 30000)
    contract.refresh()

    direct_vm.warp(T_MUCH_LATER)
    _mock_leaderboard(direct_vm, "johnycalkony", 31000)
    contract.refresh()

    history = contract.get_history()
    assert [h.name for h in history] == ["Alexei Denisov", "action"]
    assert contract.get_current_champion()["name"] == "johnycalkony"


def test_refresh_too_soon_fails(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_leaderboard(direct_vm, "Alexei Denisov", 28900)
    contract.refresh()

    direct_vm.warp(T_JUST_AFTER)
    _mock_leaderboard(direct_vm, "action", 30000)
    with direct_vm.expect_revert("Refreshed too recently"):
        contract.refresh()

    # The premature call must not have changed anything.
    assert contract.get_current_champion()["name"] == "Alexei Denisov"
    assert contract.get_history() == []


def test_refresh_after_cooldown_succeeds(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_leaderboard(direct_vm, "Alexei Denisov", 28900)
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_leaderboard(direct_vm, "action", 30000)
    contract.refresh()

    assert contract.get_current_champion()["name"] == "action"


def test_refresh_with_no_identifiable_leader_fails(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    direct_vm.mock_web(r"portal\.genlayer\.foundation", {"status": 200, "body": "empty page"})
    direct_vm.mock_llm(
        r".*live leaderboard page.*",
        json.dumps({"name": "", "points": 0}),
    )

    with direct_vm.expect_revert("Could not identify a current"):
        contract.refresh()

    assert contract.get_current_champion()["name"] == ""
