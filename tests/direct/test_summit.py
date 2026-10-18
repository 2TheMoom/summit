"""Direct-mode tests for the Summit contract (top-3 podium)."""

import json

CONTRACT = "contracts/summit.py"

T0 = "2026-01-01T00:00:00Z"
T_JUST_AFTER = "2026-01-01T00:02:00Z"  # 2 min later - inside the cooldown
T_AFTER_COOLDOWN = "2026-01-01T00:06:00Z"  # 6 min later - past the 300s cooldown
T_MUCH_LATER = "2026-01-01T01:00:00Z"

STORY_A = ("Show HN: I built a thing", 289)
STORY_B = ("A misalignment of AI in mathematics", 512)
STORY_C = ("GrapheneOS Messages app is released", 601)
STORY_D = ("Ask HN: How do you structure a monorepo?", 140)
STORY_E = ("The unreasonable effectiveness of static typing", 233)


def _mock_top3(vm, top3):
    """top3 is a list of exactly 3 (headline, points) tuples, ranked #1 first.
    mock_web/mock_llm are additive, not replacing - clear any prior
    registration first so each call to this helper fully controls what the
    next refresh() call sees, even across multiple refreshes in one test.
    """
    vm.clear_mocks()
    body_lines = "\n".join(f"{i + 1}. {h} - {p} points" for i, (h, p) in enumerate(top3))
    vm.mock_web(
        r"news\.ycombinator\.com",
        {"status": 200, "body": f"Hacker News\n{body_lines}\n"},
    )
    vm.mock_llm(
        r".*Hacker News's live front page.*",
        json.dumps({"top3": [{"headline": h, "points": p} for h, p in top3]}),
    )


def test_get_podium_before_any_refresh(direct_deploy):
    contract = direct_deploy(CONTRACT)
    podium = contract.get_podium()
    assert len(podium) == 3
    for i, seat in enumerate(podium):
        assert seat["rank"] == i + 1
        assert seat["headline"] == ""
        assert seat["points"] == 0
        assert seat["since"] == 0


def test_get_history_empty_initially(direct_deploy):
    contract = direct_deploy(CONTRACT)
    assert contract.get_history() == []


def test_get_min_refresh_interval_seconds(direct_deploy):
    contract = direct_deploy(CONTRACT)
    assert contract.get_min_refresh_interval_seconds() == 300


def test_refresh_first_ever_fills_all_three_seats(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)

    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_C])
    contract.refresh()

    podium = contract.get_podium()
    assert podium[0]["headline"] == STORY_A[0]
    assert podium[0]["points"] == STORY_A[1]
    assert podium[0]["since"] > 0
    assert podium[1]["headline"] == STORY_B[0]
    assert podium[2]["headline"] == STORY_C[0]
    assert contract.get_history() == []


def test_refresh_same_podium_updates_points_no_history(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_C])
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_top3(direct_vm, [(STORY_A[0], 340), (STORY_B[0], 550), (STORY_C[0], 620)])
    contract.refresh()

    podium = contract.get_podium()
    assert podium[0]["points"] == 340
    assert podium[1]["points"] == 550
    assert podium[2]["points"] == 620
    # Same three stories still hold their seats - no handoff, no history.
    assert contract.get_history() == []


def test_refresh_handoff_on_one_seat_only(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_C])
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    # Only #3 changes; #1 and #2 hold.
    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_D])
    contract.refresh()

    podium = contract.get_podium()
    assert podium[0]["headline"] == STORY_A[0]
    assert podium[1]["headline"] == STORY_B[0]
    assert podium[2]["headline"] == STORY_D[0]

    history = contract.get_history()
    assert len(history) == 1
    assert history[0].rank == 3
    assert history[0].headline == STORY_C[0]
    assert history[0].since > 0
    assert history[0].until > history[0].since


def test_refresh_promotion_is_a_handoff_on_both_seats(direct_vm, direct_deploy):
    """A story promoted from #3 to #2 archives an event on seat 2 (its
    outgoing holder) and on seat 3 (the promoted story's own prior tenure
    there) - seats are tracked independently, not story trajectories."""
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_C])
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    # STORY_C climbs from #3 to #2; STORY_B drops out; a new story takes #3.
    _mock_top3(direct_vm, [STORY_A, STORY_C, STORY_D])
    contract.refresh()

    podium = contract.get_podium()
    assert podium[0]["headline"] == STORY_A[0]
    assert podium[1]["headline"] == STORY_C[0]
    assert podium[2]["headline"] == STORY_D[0]

    history = contract.get_history()
    ranks_and_headlines = {(h.rank, h.headline) for h in history}
    assert (2, STORY_B[0]) in ranks_and_headlines
    assert (3, STORY_C[0]) in ranks_and_headlines
    assert len(history) == 2


def test_multiple_refreshes_build_history_in_order(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)

    direct_vm.warp(T0)
    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_C])
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_top3(direct_vm, [STORY_D, STORY_A, STORY_B])
    contract.refresh()

    direct_vm.warp(T_MUCH_LATER)
    _mock_top3(direct_vm, [STORY_D, STORY_E, STORY_A])
    contract.refresh()

    history = contract.get_history()
    assert len(history) >= 3
    assert contract.get_podium()[0]["headline"] == STORY_D[0]
    assert contract.get_podium()[1]["headline"] == STORY_E[0]
    assert contract.get_podium()[2]["headline"] == STORY_A[0]


def test_refresh_too_soon_fails(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_C])
    contract.refresh()

    direct_vm.warp(T_JUST_AFTER)
    _mock_top3(direct_vm, [STORY_D, STORY_B, STORY_C])
    with direct_vm.expect_revert("Refreshed too recently"):
        contract.refresh()

    # The premature call must not have changed anything.
    assert contract.get_podium()[0]["headline"] == STORY_A[0]
    assert contract.get_history() == []


def test_refresh_after_cooldown_succeeds(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    _mock_top3(direct_vm, [STORY_A, STORY_B, STORY_C])
    contract.refresh()

    direct_vm.warp(T_AFTER_COOLDOWN)
    _mock_top3(direct_vm, [STORY_D, STORY_B, STORY_C])
    contract.refresh()

    assert contract.get_podium()[0]["headline"] == STORY_D[0]


def test_refresh_with_fewer_than_three_entries_fails(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    direct_vm.mock_web(r"news\.ycombinator\.com", {"status": 200, "body": "Hacker News\n1. only one\n"})
    direct_vm.mock_llm(
        r".*Hacker News's live front page.*",
        json.dumps({"top3": [{"headline": STORY_A[0], "points": STORY_A[1]}]}),
    )

    with direct_vm.expect_revert("Could not identify the current top 3 stories"):
        contract.refresh()

    assert contract.get_podium()[0]["headline"] == ""


def test_refresh_with_blank_headline_fails(direct_vm, direct_deploy):
    contract = direct_deploy(CONTRACT)
    direct_vm.warp(T0)
    direct_vm.mock_web(r"news\.ycombinator\.com", {"status": 200, "body": "empty page"})
    direct_vm.mock_llm(
        r".*Hacker News's live front page.*",
        json.dumps({"top3": [{"headline": "", "points": 0}, {"headline": STORY_B[0], "points": STORY_B[1]}, {"headline": STORY_C[0], "points": STORY_C[1]}]}),
    )

    with direct_vm.expect_revert("Could not identify the current top 3 stories"):
        contract.refresh()
