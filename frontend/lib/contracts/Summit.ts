import { createClient } from "genlayer-js";
import { getEthereumProvider } from "../genlayer/client";
import { getGenLayerChain } from "../genlayer/chains";
import type { Seat, PodiumEvent } from "./types";
import {
  estimateWriteFeePreset,
  feePresetToTransactionFees,
  type FeePresetEstimate,
  type FeePresetLevel,
} from "../genlayer/fees";

/**
 * genlayer-js decodes Python dataclasses (and dicts) as JS Map instances,
 * keyed by field name. This flattens one level of that into a plain object.
 */
function toPlainObject(raw: any): Record<string, any> {
  const entries = raw instanceof Map ? Array.from(raw.entries()) : Object.entries(raw ?? {});
  const obj: Record<string, any> = {};
  for (const [key, value] of entries) obj[key] = value;
  return obj;
}

function decodeSeat(raw: any): Seat {
  const obj = toPlainObject(raw);
  return {
    rank: Number(obj.rank ?? 0),
    headline: String(obj.headline ?? ""),
    points: String(obj.points ?? "0"),
    since: String(obj.since ?? "0"),
  };
}

function decodePodiumEvent(raw: any): PodiumEvent {
  const obj = toPlainObject(raw);
  return {
    rank: Number(obj.rank ?? 0),
    headline: String(obj.headline ?? ""),
    points: String(obj.points ?? "0"),
    since: String(obj.since ?? "0"),
    until: String(obj.until ?? "0"),
  };
}

/** What each way a verification can end without a majority means, in plain words. Nothing is written in any of them. */
const REFRESH_FAILED: Record<string, string> = {
  LEADER_TIMEOUT: "The validators' leader could not read the page in time. Nothing was changed on-chain. This happens often on the testnet: try again in a moment.",
  VALIDATORS_TIMEOUT: "The validators did not finish in time. Nothing was changed on-chain. Try again in a moment.",
  UNDETERMINED: "The validators could not agree on the same top three this time, so nothing was changed. Try again.",
  CANCELED: "This transaction was cancelled. Nothing was changed.",
};

/**
 * Summit contract class - a live mirror of Hacker News's top 3 front-page
 * stories, tracked as three independent seats. refresh() is the only
 * write method, takes no arguments, and moves no value.
 */
class Summit {
  private contractAddress: `0x${string}`;
  private client: any;
  private rpcUrl?: string;

  constructor(contractAddress: string, address?: string | null, rpcUrl?: string) {
    this.contractAddress = contractAddress as `0x${string}`;
    this.rpcUrl = rpcUrl;

    const config: any = { chain: getGenLayerChain() };
    if (address) {
      config.account = address as `0x${string}`;
      // sign with MetaMask's own provider, not whichever wallet owns window.ethereum (several can be installed)
      const provider = getEthereumProvider();
      if (provider) config.provider = provider;
    }
    if (rpcUrl) config.endpoint = rpcUrl;

    this.client = createClient(config);
  }

  updateAccount(address: string): void {
    const config: any = { chain: getGenLayerChain(), account: address as `0x${string}` };
    const provider = getEthereumProvider();
    if (provider) config.provider = provider;
    if (this.rpcUrl) config.endpoint = this.rpcUrl;
    this.client = createClient(config);
  }

  /**
   * refresh() renders a live page and runs a 3-entry LLM extraction on top
   * of it, then requires all three ranks to match between leader and
   * validators - a heavier nondet operation than a single-entry extraction,
   * and a stricter consensus bar. "high" (more rotations/appeal rounds) is
   * the sensible default, not "standard" - a thin fee budget risks a
   * leader timeout on this specific call.
   */
  async estimateRefreshFees(level: FeePresetLevel = "high"): Promise<FeePresetEstimate | undefined> {
    return estimateWriteFeePreset(
      this.client,
      { address: this.contractAddress, functionName: "refresh", args: [] },
      level,
    );
  }

  async getPodium(): Promise<Seat[]> {
    const result: any = await this.client.readContract({
      address: this.contractAddress, functionName: "get_podium", args: [],
    });
    return Array.isArray(result) ? result.map(decodeSeat) : [];
  }

  async getHistory(): Promise<PodiumEvent[]> {
    const result: any = await this.client.readContract({
      address: this.contractAddress, functionName: "get_history", args: [],
    });
    return Array.isArray(result) ? result.map(decodePodiumEvent) : [];
  }

  async getLastRefreshAt(): Promise<string> {
    const result = await this.client.readContract({
      address: this.contractAddress, functionName: "get_last_refresh_at", args: [],
    });
    return String(result ?? "0");
  }

  async getMinRefreshIntervalSeconds(): Promise<string> {
    const result = await this.client.readContract({
      address: this.contractAddress, functionName: "get_min_refresh_interval_seconds", args: [],
    });
    return String(result ?? "0");
  }

  async refresh(feePreset?: FeePresetEstimate, onSubmitted?: (txHash: string) => void): Promise<string> {
    const fees = feePresetToTransactionFees(feePreset);
    let txHash: string;
    try {
      txHash = await this.client.writeContract({
        address: this.contractAddress,
        functionName: "refresh",
        args: [],
        value: BigInt(0),
        ...(fees ? { fees } : {}),
      });
    } catch (error) {
      console.error("Error calling refresh:", error);
      throw new Error("Failed to submit the verify transaction. Please try again.");
    }

    onSubmitted?.(txHash);

    // Poll the transaction itself, so a validator timeout is reported as what it is (nothing changed, try again)
    // instead of a vague "confirmation timed out" after minutes of waiting.
    const deadline = Date.now() + 10 * 60_000;
    for (;;) {
      let tx: any = null;
      try {
        tx = await this.client.getTransaction({ hash: txHash });
      } catch (error) {
        console.error("Error reading the refresh transaction (will retry):", error);
      }
      const status = String(tx?.statusName ?? "");
      if (status === "ACCEPTED" || status === "FINALIZED") {
        const exec = String(tx?.txExecutionResultName ?? "");
        if (exec && exec !== "FINISHED_WITH_RETURN") {
          throw new Error(`The contract refused this verification (${exec}), so nothing changed. A verification right after another one is refused: wait 5 minutes. Transaction ${txHash}.`);
        }
        return txHash;
      }
      if (REFRESH_FAILED[status]) throw new Error(`${REFRESH_FAILED[status]} Transaction ${txHash}.`);
      if (Date.now() > deadline) {
        throw new Error(`Transaction ${txHash} is still being worked on after 10 minutes. It may still complete: check the explorer before trying again.`);
      }
      await new Promise((r) => setTimeout(r, 5000));
    }
  }
}

export default Summit;
