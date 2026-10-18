# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from genlayer import *

FRONT_PAGE_URL = "https://news.ycombinator.com/"

# Resource-courtesy guard only, not a security control: refresh() takes no
# caller-supplied input, so there's nothing to manipulate - this just bounds
# how often anyone can make every validator re-render the page and burn an
# LLM call on it.
MIN_REFRESH_INTERVAL_SECONDS = 300

NUM_SEATS = 3


@allow_storage
@dataclass
class Seat:
    headline: str
    points: u256
    since: u256  # unix epoch seconds


@allow_storage
@dataclass
class PodiumEvent:
    rank: u256  # 1, 2, or 3
    headline: str
    points: u256
    since: u256  # unix epoch seconds
    until: u256  # unix epoch seconds


def _empty_seat() -> Seat:
    return Seat(headline="", points=0, since=0)


class Summit(gl.Contract):
    """A "living state" object with no claimant, no dispute, and no payout -
    it just continuously mirrors one real-world fact: whichever three
    stories are currently ranked #1, #2, and #3 on Hacker News's live front
    page (news.ycombinator.com). Real-world sources like this change on
    their own timeline; GenVM's browser-backed web.render lets validators
    independently confirm the current standing rather than trusting a
    cached or stale copy.

    Each of the three ranks is tracked as an independent "seat" - refresh()
    does not follow a story as it climbs the ranking. If a story is
    promoted from #3 to #2, that is a genuine handoff on *both* seats: seat
    3 archives its outgoing holder, and seat 2 archives its outgoing
    holder and crowns the promoted story with a fresh `since`. The same
    headline can legitimately appear more than once in history if it moved
    between seats - that is expected, not a bug.

    refresh() takes zero parameters - there is no user-supplied evidence
    URL or statement to authenticate, unlike a claim-adjudication
    contract. All three ranks are consensus-critical: a validator must
    independently read the identical #1, #2, and #3 headlines to AGREE,
    the same equivalence-principle check used everywhere else in GenVM.
    Point totals remain informational only, same as before - they can
    legitimately drift by the time a validator re-reads a fast-moving live
    page. No value ever moves through this contract.
    """

    podium_1: Seat
    podium_2: Seat
    podium_3: Seat
    last_refresh_at: u256
    history: DynArray[PodiumEvent]

    def __init__(self):
        self.podium_1 = _empty_seat()
        self.podium_2 = _empty_seat()
        self.podium_3 = _empty_seat()
        self.last_refresh_at = 0

    def _fetch_current_podium(self) -> dict:
        web_data = gl.nondet.web.render(FRONT_PAGE_URL, wait_after_loaded="1s", mode="text")

        prompt = f"""
You are reading Hacker News's live front page.

Page content:
\"\"\"
{web_data}
\"\"\"

Identify the current top 3 stories (ranks #1, #2, and #3), in order. For
each, report its exact headline as shown, and its point total (e.g. from
"142 points") as a plain integer.

Respond in JSON as an object with a "top3" array of exactly 3 entries,
ordered #1 first:
{{
    "top3": [
        {{"headline": str, "points": int}},
        {{"headline": str, "points": int}},
        {{"headline": str, "points": int}}
    ]
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
"""
        return gl.nondet.exec_prompt(prompt, response_format="json")

    def _consensus_podium(self) -> dict:
        def leader_fn() -> dict:
            return self._fetch_current_podium()

        def _headlines(result) -> list[str]:
            entries = result.get("top3") if isinstance(result, dict) else None
            if not isinstance(entries, list) or len(entries) != NUM_SEATS:
                return []
            return [str(e.get("headline", "")) for e in entries]

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my_result = leader_fn()
            # All three ranks are consensus-critical - a validator must
            # independently read the identical #1, #2, and #3 headlines to
            # AGREE. Point totals are compared nowhere here; they stay
            # informational only, same as the single-seat version.
            mine = _headlines(my_result)
            theirs = _headlines(leaders_res.calldata)
            return bool(mine) and mine == theirs

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    def _parse_points(self, raw) -> int:
        """Tolerantly parses the LLM's reported point total. Despite the
        prompt asking for "a plain integer," an LLM can still return a
        comma-formatted string (e.g. "1,234") for a high-scoring story -
        strip anything that isn't a digit rather than letting int() raise
        and revert the whole refresh() call over a value that's informational
        only, not part of consensus."""
        digits = "".join(ch for ch in str(raw) if ch.isdigit())
        return int(digits) if digits else 0

    def _seats(self) -> list[Seat]:
        return [self.podium_1, self.podium_2, self.podium_3]

    def _set_seat(self, index: int, seat: Seat) -> None:
        if index == 0:
            self.podium_1 = seat
        elif index == 1:
            self.podium_2 = seat
        else:
            self.podium_3 = seat

    @gl.public.write
    def refresh(self) -> None:
        now = int(datetime.now(timezone.utc).timestamp())

        if self.last_refresh_at != 0 and now - self.last_refresh_at < MIN_REFRESH_INTERVAL_SECONDS:
            raise gl.vm.UserError(
                f"Refreshed too recently - wait at least {MIN_REFRESH_INTERVAL_SECONDS}s between checks"
            )
        self.last_refresh_at = now

        result = self._consensus_podium()
        top3 = result.get("top3") if isinstance(result, dict) else None
        if not isinstance(top3, list) or len(top3) != NUM_SEATS:
            raise gl.vm.UserError("Could not identify the current top 3 stories")

        entries = []
        for entry in top3:
            headline = str(entry.get("headline", "")).strip()
            if not headline:
                raise gl.vm.UserError("Could not identify the current top 3 stories")
            entries.append((headline, self._parse_points(entry.get("points", 0))))

        current_seats = self._seats()
        for i in range(NUM_SEATS):
            headline, points = entries[i]
            seat = current_seats[i]
            rank = i + 1

            if headline == seat.headline:
                # Same story still holds this seat - just keep its point
                # total fresh.
                self._set_seat(i, Seat(headline=headline, points=points, since=seat.since))
                continue

            if seat.headline != "":
                # A genuine handoff on this seat - archive the outgoing
                # story before crowning the new one.
                self.history.append(
                    PodiumEvent(
                        rank=rank,
                        headline=seat.headline,
                        points=seat.points,
                        since=seat.since,
                        until=now,
                    )
                )

            self._set_seat(i, Seat(headline=headline, points=points, since=now))

    @gl.public.view
    def get_podium(self) -> list:
        return [
            {"rank": i + 1, "headline": seat.headline, "points": seat.points, "since": seat.since}
            for i, seat in enumerate(self._seats())
        ]

    @gl.public.view
    def get_history(self) -> list:
        return list(self.history)

    @gl.public.view
    def get_last_refresh_at(self) -> u256:
        return self.last_refresh_at

    @gl.public.view
    def get_min_refresh_interval_seconds(self) -> u256:
        return MIN_REFRESH_INTERVAL_SECONDS
