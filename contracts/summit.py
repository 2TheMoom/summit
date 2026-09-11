# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from dataclasses import dataclass
from datetime import datetime, timezone
from genlayer import *

FRONT_PAGE_URL = "https://news.ycombinator.com/"

# Resource-courtesy guard only, not a security control: refresh() takes no
# caller-supplied input, so there's nothing to manipulate - this just bounds
# how often anyone can make every validator re-render the page and burn an
# LLM call on it.
MIN_REFRESH_INTERVAL_SECONDS = 300


@allow_storage
@dataclass
class TitleHolder:
    headline: str
    points: u256
    since: u256  # unix epoch seconds
    until: u256  # unix epoch seconds


class Summit(gl.Contract):
    """A "living state" object with no claimant, no dispute, and no payout -
    it just continuously mirrors one real-world fact: whichever story is
    currently ranked #1 on Hacker News's live front page
    (news.ycombinator.com). Real-world sources like this change on their
    own timeline; GenVM's browser-backed web.render lets validators
    independently confirm the current standing rather than trusting a
    cached or stale copy.

    refresh() takes zero parameters - there is no user-supplied evidence URL
    or statement to authenticate, unlike a claim-adjudication contract. The
    only question validators answer is "what does the one canonical page
    currently show at #1," settled the same way as any other GenVM
    equivalence-principle check. No value ever moves through this contract.
    """

    current_headline: str
    current_points: u256
    current_since: u256
    last_refresh_at: u256
    history: DynArray[TitleHolder]

    def __init__(self):
        self.current_headline = ""
        self.current_points = 0
        self.current_since = 0
        self.last_refresh_at = 0

    def _fetch_current_leader(self) -> dict:
        web_data = gl.nondet.web.render(FRONT_PAGE_URL, wait_after_loaded="1s", mode="text")

        prompt = f"""
You are reading Hacker News's live front page.

Page content:
\"\"\"
{web_data}
\"\"\"

Identify whichever story is currently ranked #1 (the top of the list). Report
its exact headline as shown, and its point total (e.g. from "142 points") as
a plain integer.

Respond in JSON:
{{
    "headline": str,
    "points": int
}}
It is mandatory that you respond only using the JSON format above,
nothing else. Don't include any other words or characters,
your output must be only JSON without any formatting prefix or suffix.
This result should be perfectly parsable by a JSON parser without errors.
"""
        return gl.nondet.exec_prompt(prompt, response_format="json")

    def _consensus_leader(self) -> dict:
        def leader_fn() -> dict:
            return self._fetch_current_leader()

        def validator_fn(leaders_res) -> bool:
            if not isinstance(leaders_res, gl.vm.Return):
                return False
            my_result = leader_fn()
            # Only the identity of #1 needs consensus - the point total is
            # informational and can drift by the time a validator re-reads
            # the live page, same as any other fast-moving nondet fact.
            return my_result["headline"] == leaders_res.calldata["headline"]

        return gl.vm.run_nondet_unsafe(leader_fn, validator_fn)

    @gl.public.write
    def refresh(self) -> None:
        now = int(datetime.now(timezone.utc).timestamp())

        if self.last_refresh_at != 0 and now - self.last_refresh_at < MIN_REFRESH_INTERVAL_SECONDS:
            raise gl.vm.UserError(
                f"Refreshed too recently - wait at least {MIN_REFRESH_INTERVAL_SECONDS}s between checks"
            )
        self.last_refresh_at = now

        result = self._consensus_leader()
        headline = str(result.get("headline", "")).strip()
        points = int(result.get("points", 0))

        if not headline:
            raise gl.vm.UserError("Could not identify a current #1 story")

        if headline == self.current_headline:
            # Same story still holds the top spot - just keep its recorded
            # point total fresh.
            self.current_points = points
            return

        if self.current_headline != "":
            # A genuine handoff - archive the outgoing story before crowning
            # the new one.
            self.history.append(
                TitleHolder(
                    headline=self.current_headline,
                    points=self.current_points,
                    since=self.current_since,
                    until=now,
                )
            )

        self.current_headline = headline
        self.current_points = points
        self.current_since = now

    @gl.public.view
    def get_current_champion(self) -> dict:
        return {
            "headline": self.current_headline,
            "points": self.current_points,
            "since": self.current_since,
        }

    @gl.public.view
    def get_history(self) -> list:
        return list(self.history)

    @gl.public.view
    def get_last_refresh_at(self) -> u256:
        return self.last_refresh_at

    @gl.public.view
    def get_min_refresh_interval_seconds(self) -> u256:
        return MIN_REFRESH_INTERVAL_SECONDS
