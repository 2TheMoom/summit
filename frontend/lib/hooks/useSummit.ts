"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import Summit from "../contracts/Summit";
import { getContractAddress, getStudioUrl } from "../genlayer/client";
import { useWallet } from "../genlayer/wallet";
import { success, error, configError } from "../utils/toast";
import type { Champion, TitleHolder } from "../contracts/types";

export function useSummitContract(): Summit | null {
  const { address } = useWallet();
  const contractAddress = getContractAddress();
  const rpcUrl = getStudioUrl();

  const contract = useMemo(() => {
    if (!contractAddress) {
      configError(
        "Setup Required",
        "Contract address not configured. Please set NEXT_PUBLIC_CONTRACT_ADDRESS in your .env file.",
        { label: "Setup Guide", onClick: () => window.open("/docs/setup", "_blank") }
      );
      return null;
    }
    return new Summit(contractAddress, address, rpcUrl);
  }, [contractAddress, address, rpcUrl]);

  return contract;
}

export function useCurrentChampion() {
  const contract = useSummitContract();

  return useQuery<Champion, Error>({
    queryKey: ["currentChampion"],
    queryFn: () => (contract ? contract.getCurrentChampion() : Promise.resolve({ headline: "", points: "0", since: "0" })),
    refetchOnWindowFocus: true,
    staleTime: 2000,
    enabled: !!contract,
  });
}

export function useHistory() {
  const contract = useSummitContract();

  return useQuery<TitleHolder[], Error>({
    queryKey: ["history"],
    queryFn: () => (contract ? contract.getHistory() : Promise.resolve([])),
    refetchOnWindowFocus: true,
    staleTime: 2000,
    enabled: !!contract,
  });
}

export function useLastRefreshAt() {
  const contract = useSummitContract();

  return useQuery<string, Error>({
    queryKey: ["lastRefreshAt"],
    queryFn: () => (contract ? contract.getLastRefreshAt() : Promise.resolve("0")),
    refetchOnWindowFocus: true,
    staleTime: 2000,
    enabled: !!contract,
  });
}

export function useRefresh() {
  const contract = useSummitContract();
  const { address } = useWallet();
  const queryClient = useQueryClient();
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pendingTxHash, setPendingTxHash] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      if (!contract) throw new Error("Contract not configured. Please set NEXT_PUBLIC_CONTRACT_ADDRESS in your .env file.");
      if (!address) throw new Error("Wallet not connected. Please connect your wallet to verify.");
      setIsRefreshing(true);
      setPendingTxHash(null);
      const feePreset = await contract.estimateRefreshFees("high");
      return contract.refresh(feePreset, setPendingTxHash);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["currentChampion"] });
      queryClient.invalidateQueries({ queryKey: ["history"] });
      queryClient.invalidateQueries({ queryKey: ["lastRefreshAt"] });
      setIsRefreshing(false);
      success("Verified!", { description: "The title now reflects the live standings." });
    },
    onError: (err: any) => {
      console.error("Error refreshing:", err);
      setIsRefreshing(false);
      error("Verification failed", { description: err?.message || "Please try again." });
    },
  });

  return {
    ...mutation,
    isRefreshing,
    pendingTxHash,
    clearPendingTx: () => setPendingTxHash(null),
    refresh: mutation.mutate,
  };
}
