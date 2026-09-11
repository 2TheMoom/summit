"use client";

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { Navbar } from "@/components/Navbar";
import { Button } from "@/components/ui/button";
import { useCurrentChampion, useHistory, useLastRefreshAt, useRefresh } from "@/lib/hooks/useSummit";
import { useWallet } from "@/lib/genlayer/wallet";
import { getTxExplorerUrl } from "@/lib/genlayer/chains";
import { error as toastError } from "@/lib/utils/toast";

function formatDuration(fromSeconds: number, nowSeconds: number): string {
  const diff = Math.max(0, nowSeconds - fromSeconds);
  if (diff < 60) return `${diff}s`;
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} hr${hours === 1 ? "" : "s"}`;
  const days = Math.floor(hours / 24);
  return `${days} day${days === 1 ? "" : "s"}`;
}

function useNowSeconds() {
  const [now, setNow] = useState(() => Math.floor(Date.now() / 1000));
  useEffect(() => {
    const id = setInterval(() => setNow(Math.floor(Date.now() / 1000)), 15000);
    return () => clearInterval(id);
  }, []);
  return now;
}

export default function HomePage() {
  const { data: champion, isLoading: championLoading } = useCurrentChampion();
  const { data: history } = useHistory();
  const { data: lastRefreshAt } = useLastRefreshAt();
  const { address } = useWallet();
  const { refresh, isRefreshing, pendingTxHash } = useRefresh();
  const now = useNowSeconds();

  const hasChampion = !!champion?.headline;
  const since = champion?.since ? parseInt(champion.since, 10) : 0;
  const lastRefresh = lastRefreshAt ? parseInt(lastRefreshAt, 10) : 0;

  const handleVerify = () => {
    if (!address) {
      toastError("Connect your wallet to verify");
      return;
    }
    refresh(undefined);
  };

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar />

      <main className="flex-grow pt-24 pb-16">
        <div className="max-w-3xl mx-auto px-5 md:px-7">
          {/* Hero */}
          <section className="brand-card relative overflow-hidden text-center px-6 sm:px-8 py-10 sm:py-11">
            <div
              aria-hidden
              className="pointer-events-none absolute left-1/2 -translate-x-1/2 -top-36 w-[420px] h-[420px] rounded-full"
              style={{ background: "radial-gradient(circle, oklch(0.78 0.12 205 / 0.16) 0%, transparent 70%)" }}
            />

            <div className="relative w-14 h-14 mx-auto mb-4">
              <div
                className="absolute inset-[-10px] rounded-full border border-border"
                style={{ animation: "crestSpin 14s linear infinite" }}
              >
                <span className="absolute -top-[3px] left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-primary" />
              </div>
              <svg viewBox="0 0 40 40" className="relative z-10 w-full h-full">
                <path d="M20 6 L31 28 H9 Z" fill="none" stroke="var(--primary)" strokeWidth="2" />
                <path d="M20 8 L20 16.5 L25.5 13.7 Z" fill="var(--flag)" />
              </svg>
            </div>

            <div className="relative eyebrow">Current Titleholder</div>

            {championLoading ? (
              <div className="relative mt-5 flex justify-center">
                <Loader2 className="w-6 h-6 animate-spin text-primary" />
              </div>
            ) : hasChampion ? (
              <>
                <div className="relative mt-2 text-xl sm:text-2xl font-bold font-[family-name:var(--font-display)] max-w-[46ch] mx-auto text-balance">
                  {champion!.headline}
                </div>
                <div className="relative mt-1.5 font-mono text-4xl sm:text-5xl font-semibold text-primary tabular">
                  {champion!.points}
                  <span className="text-base sm:text-lg text-muted-foreground font-normal ml-2">points</span>
                </div>
                <div className="relative mt-4 flex flex-wrap justify-center gap-x-6 gap-y-1.5 font-mono text-xs text-muted-foreground">
                  <span>HOLDING SINCE <b className="text-foreground font-medium">{formatDuration(since, now)} ago</b></span>
                  {lastRefresh > 0 && (
                    <span>LAST VERIFIED <b className="text-foreground font-medium">{formatDuration(lastRefresh, now)} ago</b></span>
                  )}
                </div>
              </>
            ) : (
              <div className="relative mt-3 text-muted-foreground text-sm max-w-[42ch] mx-auto">
                Not yet verified on-chain. Be the first to check who currently holds #1.
              </div>
            )}

            <div className="relative mt-7">
              <Button onClick={handleVerify} variant="gradient" disabled={isRefreshing} size="lg">
                {isRefreshing ? (<><Loader2 className="w-4 h-4 mr-2 animate-spin" />Verifying...</>) : "Verify Now"}
              </Button>
              {isRefreshing && (
                <div className="mt-3 font-mono text-xs text-muted-foreground">
                  {pendingTxHash ? (
                    <>
                      Transaction submitted -{" "}
                      <a href={getTxExplorerUrl(pendingTxHash)} target="_blank" rel="noopener noreferrer" className="text-primary hover:underline">
                        view on explorer
                      </a>
                    </>
                  ) : (
                    "Preparing transaction..."
                  )}
                </div>
              )}
            </div>
          </section>

          {/* How Summit verifies */}
          <section className="mt-10">
            <h2 className="text-base font-bold">How Summit Verifies</h2>
            <p className="mt-1.5 text-sm text-muted-foreground max-w-[62ch]">
              No claim, no submission, nothing for a caller to manipulate - <code className="font-mono text-foreground bg-muted px-1 py-0.5 rounded">refresh()</code> takes zero parameters. It just re-checks the one canonical source.
            </p>
            <div className="mt-4 grid sm:grid-cols-3 gap-3.5">
              <div className="brand-card p-4">
                <div className="eyebrow mb-2">1</div>
                <div className="text-sm font-semibold">Render the live page</div>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  Validators independently load news.ycombinator.com in a real browser environment.
                </p>
              </div>
              <div className="brand-card p-4">
                <div className="eyebrow mb-2">2</div>
                <div className="text-sm font-semibold">Read what&apos;s #1</div>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  Each validator&apos;s model extracts the current top story and its points, independently of the others.
                </p>
              </div>
              <div className="brand-card p-4">
                <div className="eyebrow mb-2">3</div>
                <div className="text-sm font-semibold">Reach consensus</div>
                <p className="mt-1.5 text-xs text-muted-foreground leading-relaxed">
                  The equivalence principle requires validators to agree before state updates.
                </p>
              </div>
            </div>
          </section>

          {/* Succession */}
          <section className="mt-10 pb-4">
            <div className="flex items-baseline justify-between gap-3 flex-wrap">
              <h2 className="text-base font-bold">Succession</h2>
              <span className="eyebrow">{history?.length ?? 0} past titleholder{history?.length === 1 ? "" : "s"}</span>
            </div>
            <div className="mt-4 relative pl-7">
              <div className="absolute left-2 top-1.5 bottom-1.5 w-px bg-border" />

              {hasChampion && (
                <div className="relative pb-6">
                  <span className="absolute -left-7 top-0.5 w-[17px] h-[17px] text-primary">
                    <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 2v16M4 3h11l-2.5 3L15 9H4" /></svg>
                  </span>
                  <div className="flex items-baseline justify-between gap-3 flex-wrap">
                    <span className="font-semibold text-sm text-primary">{champion!.headline}</span>
                    <span className="font-mono text-xs text-muted-foreground tabular">{champion!.points} points</span>
                  </div>
                  <div className="font-mono text-[0.7rem] text-muted-foreground mt-0.5">Holding · {formatDuration(since, now)} and counting</div>
                </div>
              )}

              {history && history.length > 0 ? (
                [...history].reverse().map((h, i) => (
                  <div key={i} className="relative pb-6 last:pb-0">
                    <span className="absolute -left-7 top-0.5 w-[17px] h-[17px] text-muted-foreground">
                      <svg viewBox="0 0 20 20" fill="none" stroke="currentColor" strokeWidth="1.8"><path d="M4 2v16M4 3h11l-2.5 3L15 9H4" /></svg>
                    </span>
                    <div className="flex items-baseline justify-between gap-3 flex-wrap">
                      <span className="font-semibold text-sm">{h.headline}</span>
                      <span className="font-mono text-xs text-muted-foreground tabular">{h.points} points</span>
                    </div>
                    <div className="font-mono text-[0.7rem] text-muted-foreground mt-0.5">
                      Held for {formatDuration(parseInt(h.since, 10), parseInt(h.until, 10))}
                    </div>
                  </div>
                ))
              ) : !hasChampion ? (
                <p className="text-sm text-muted-foreground">No history yet - the first verification crowns the inaugural titleholder.</p>
              ) : null}
            </div>
          </section>
        </div>
      </main>

      <footer className="border-t border-border py-5">
        <div className="max-w-3xl mx-auto px-5 md:px-7 flex items-center justify-between flex-wrap gap-3 font-mono text-xs text-muted-foreground">
          <span>Built on GenLayer Bradbury Testnet</span>
          <div className="flex items-center gap-5">
            <a href="https://genlayer.com" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors">GenLayer</a>
            <a href="https://news.ycombinator.com" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors">Hacker News</a>
            <a href="https://github.com/2TheMoom/summit" target="_blank" rel="noopener noreferrer" className="hover:text-primary transition-colors">GitHub</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
