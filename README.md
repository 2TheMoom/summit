# Summit

## About
A GenLayer "living state" Intelligent Contract with no claimant, no dispute,
and no payout - it just continuously mirrors one real-world fact: whichever
story is currently ranked #1 on Hacker News's live front page. Anyone can
call `refresh()`, which takes zero parameters. Validators independently
render the one canonical page, extract who's currently at the top, and reach
consensus via GenLayer's equivalence principle before state updates. Past
titleholders are archived on-chain as a succession history.

Unlike an adjudicated claim or an escrow-with-verdict, there's nothing here
for a caller to submit or manipulate - `refresh()` only ever asks "what does
this one page currently show," settled the same way any other nondet fact
is settled in GenVM. Because no native value ever moves through this
contract, it also sidesteps a currently-open GenLayer platform bug affecting
`emit_transfer` (see [genlayerlabs/genvm-manager#20](https://github.com/genlayerlabs/genvm-manager/issues/20)),
which has forced a documented "known limitation" section onto two other
GenLayer projects from this account.

### Why Hacker News, not something more novel
The original design targeted GenLayer's own live points leaderboard
(portal.genlayer.foundation/points) - mirroring who's currently the top
contributor felt like a sharper pitch than a generic example. In practice
that page is a 4MB+ client-rendered SPA with a reCAPTCHA script, and it
repeatedly caused the GenVM leader to be terminated *before it even
attempted the render* (confirmed via a minimal diagnostic contract and
execution traces showing `web_module: { calls: 0 }`). The same diagnostic
against Hacker News's plain server-rendered front page (~34KB, no JS)
reached full validator consensus on the first attempt. The mechanic is
identical either way; only the mirrored source changed.

## Live deployment
Deployed on **GenLayer Bradbury Testnet** (chain ID 4221):
- **Contract:** [`0xa4C55a5ca99af26b466785Bbc381D307830DdA05`](https://explorer-bradbury.genlayer.com/address/0xa4C55a5ca99af26b466785Bbc381D307830DdA05)
- Verified via 11 passing direct-mode tests (`pytest tests/direct/`), covering
  first-time crowning, same-titleholder point refreshes, handoffs with
  history archiving, the refresh cooldown, the no-identifiable-leader guard,
  and tolerant parsing of a comma-formatted point total.
- Verified live end-to-end on this exact deployment: `refresh()` reached full
  validator majority (`AGREE`, 3/5 validators) and correctly crowned the real
  current #1 Hacker News story on-chain - `get_current_champion()` returned
  `{ headline: "Introducing System One Models and Jev (typesafe.ai)", points:
  1250, since: 1789544963 }`, matching the live page at call time.
- Re-verified again on 2026-09-23, over a week later: `get_current_champion()`
  still reads correctly (contract state holds up over time with no drift or
  corruption), and a fresh `refresh()` call succeeded - `AGREE`, correctly
  crowning `"Fixing the Portobello Police Station Clock"` (148 points) as the
  new live #1 story, with the full succession history preserved. See the note
  below for what that attempt actually took.

### A note on live consensus stability
Live-testing wasn't perfectly smooth on the way here. Two earlier calls
against this same deployment finished as `NO_MAJORITY` and
`VALIDATORS_TIMEOUT` rather than a clean `AGREE`, despite direct-mode tests
passing and the transaction data showing the contract logic itself executing
correctly (`FINISHED_WITH_RETURN`, no exception) both times - in the
`NO_MAJORITY` case, two of five validators independently computed and agreed
on the identical result (`"Show HN: Make your first edit to OpenStreetMap"`),
but two others timed out and one hit `DETERMINISTIC_VIOLATION`, short of a
majority. Every plain read call made during that window also hit raw RPC
connect-timeouts, and GenLayer Studio's own hosted environment failed to
deploy its own unmodified reference contract the same night - consistent
with broader Bradbury testnet degradation on 2026-09-13/14 rather than a
Summit-specific defect, and borne out by the clean success above once
network conditions recovered. The theoretical mechanism worth naming
regardless: `_consensus_leader`'s validator check re-renders the live page a
second time to confirm internal consistency, and a source that changes on a
timescale of minutes (unlike a fixed on-chain fact) has some chance of
returning a different snapshot on that second render if a round runs slow -
plausible under degraded network conditions, though not what was observed
here once the network was healthy.

**Update, 2026-09-23:** the same pattern recurred and resolved the same way.
Four consecutive `refresh()` attempts that night came back `VALIDATORS_TIMEOUT`
(a majority of validators timing out on the render step, one or two still
independently agreeing where they did complete). A fifth attempt eventually
reached `ACCEPTED`/`AGREE` after a longer-than-usual consensus round, and
correctly crowned the real live story. Nothing about the contract changed
between attempts one and five - this is consistent, recurring evidence of
transient Bradbury-side render capacity issues rather than a Summit-specific
defect, and the pattern of "degrades, then clears on its own without a code
change" now has two independent occurrences a week and a half apart.

## What's included
- `contracts/summit.py` — the Summit Intelligent Contract
- `tests/direct/test_summit.py` — direct-mode tests (in-memory, mocked web/LLM)
- **Contract linting** — static analysis to catch common contract issues before deployment
- **CI pipeline** — GitHub Actions workflow for linting and direct tests
- A Next.js 15 frontend (TypeScript, TanStack Query, Radix UI) - a live
  scoreboard-style readout of the current titleholder, a succession
  timeline of past titleholders, and a "Verify Now" trigger
- Configuration file template and deployment scripts

## Requirements
- Python >= 3.12
- [GenLayer CLI](https://github.com/genlayerlabs/genlayer-cli) globally installed: `npm install -g genlayer`
- GenLayer Studio (for integration tests and deployment): Install from [Docs](https://docs.genlayer.com/developers/intelligent-contracts/tooling-setup#using-the-genlayer-studio) or use the hosted [GenLayer Studio](https://studio.genlayer.com/)

## Project Structure

```
contracts/              # Python intelligent contracts
  summit.py              # Summit
tests/
  direct/                # Fast in-memory tests (no Studio required)
    test_summit.py
frontend/                # Next.js 15 app (TypeScript, TanStack Query, Radix UI)
deploy/                  # TypeScript deployment scripts
gltest.config.yaml       # Test runner network configuration
pyproject.toml           # Python/pytest configuration
.github/workflows/       # CI pipeline
```

## Quick Start

### 1. Set up Python environment

```shell
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Lint the contract

```shell
genvm-lint check contracts/summit.py
```

### 3. Run direct mode tests

```shell
pytest tests/direct/ -v
```

### 4. Deploy the contract

1. Choose your network: `genlayer network`
2. Deploy: `genlayer deploy` (runs the script in `/deploy/deployScript.ts`)

### 5. Set up the frontend

1. Copy `frontend/.env.example` to `frontend/.env`
2. Add your deployed contract address as `NEXT_PUBLIC_CONTRACT_ADDRESS`
3. Run:

```shell
cd frontend
npm install
npm run dev
```

The app will be available at http://localhost:3000/.

## How Summit Works

1. **`refresh()`** — callable by anyone, no arguments, no value. Validators
   independently render `news.ycombinator.com` in a real browser
   environment, ask an LLM to identify the current #1 story and its point
   total, and reach consensus on the story's identity via the equivalence
   principle (the point total is informational and can drift trivially
   between independent reads, so only the story identity is consensus-
   checked). A minimum interval between refreshes (default 5 minutes)
   guards against wasted validator work, not against manipulation - there's
   nothing to manipulate.
2. **On a handoff** — the outgoing titleholder is archived to an on-chain
   history log with how long they held the top spot, before the new
   titleholder is crowned.
3. **`get_current_champion` / `get_history` / `get_last_refresh_at`** — read
   back the live state and succession history.

## Testing Strategy

| Test Type | Command | Speed | Requires Studio |
|-----------|---------|-------|-----------------|
| **Lint** | `genvm-lint check contracts/summit.py` | ~250ms | No |
| **Direct** | `pytest tests/direct/ -v` | ~ms/test | No |

## Community
- **[Discord](https://discord.gg/8Jm4v89VAu)**: Discussions, support, and announcements
- **[Telegram](https://t.me/genlayer)**: Informal chats and quick updates

## Documentation
For detailed information, see our [documentation](https://docs.genlayer.com/).

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
