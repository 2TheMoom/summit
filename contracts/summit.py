# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

from dataclasses import dataclass
from datetime import datetime, timezone
from genlayer import *

LEADERBOARD_URL = "https://portal.genlayer.foundation/points"

# Resource-courtesy guard only, not a security control: refresh() takes no
# caller-supplied input, so there's nothing to manipulate - this just bounds
# how often anyone can make every validator re-render the page and burn an
# LLM call on it.
MIN_REFRESH_INTERVAL_SECONDS = 300


@allow_storage
@dataclass
class TitleHolder:
    name: str
    points: u256
    since: u256  # unix epoch seconds
    until: u256  # unix epoch seconds


class Summit(gl.Contract):
    """A "living state" object with no claimant, no dispute, and no payout -
    it just continuously mirrors one real-world fact: who is currently #1 on
    GenLayer's own live contributor points leaderboard
    (portal.genlayer.foundation/points). That page is a client-rendered SPA,
    unreadable by a plain HTTP fetch, which is exactly the kind of source
    GenVM's browser-backed web.render is built for.

    refresh() takes zero parameters - there is no user-supplied evidence URL
    or statement to authenticate, unlike a claim-adjudication contract. The
    only question validators answer is "who does the one canonical page
    currently show as #1," settled the same way as any other GenVM
    equivalence-principle check. No value ever moves through this contract.
    """

    current_name: str
    current_points: u256
    current_since: u256
    last_refresh_at: u256
    history: DynArray[TitleHolder]

    def __init__(self):
        self.current_name = ""
        self.current_points = 0
        self.current_since = 0
        self.last_refresh_at = 0

    def _fetch_current_leader(self) -> dict:
        web_data = gl.nondet.web.render(LEADERBOARD_URL, wait_after_loaded="2s", mode="text")

        prompt = f"""
You are reading a live leaderboard page from GenLayer's own contributor portal.

Page content:
\"\"\"
{web_data}
\"\"\"

Identify whoever is currently ranked #1 (the top of the standings). Report their
displayed name or handle exactly as shown, and their point total (a "GLP" figure,
which may be formatted with commas) as a plain integer.

Respond in JSON:
{{
    "name": str,
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
            return my_result["name"] == leaders_res.calldata["name"]

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
        name = str(result.get("name", "")).strip()
        points = int(result.get("points", 0))

        if not name:
            raise gl.vm.UserError("Could not identify a current #1 on the leaderboard")

        if name == self.current_name:
            # Same titleholder - just keep their recorded point total fresh.
            self.current_points = points
            return

        if self.current_name != "":
            # A genuine handoff - archive the outgoing titleholder before
            # crowning the new one.
            self.history.append(
                TitleHolder(
                    name=self.current_name,
                    points=self.current_points,
                    since=self.current_since,
                    until=now,
                )
            )

        self.current_name = name
        self.current_points = points
        self.current_since = now

    @gl.public.view
    def get_current_champion(self) -> dict:
        return {
            "name": self.current_name,
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
