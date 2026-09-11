/**
 * TypeScript types for the GenLayer Summit contract
 */

export interface Champion {
  name: string;
  points: string;
  since: string;
}

export interface TitleHolder {
  name: string;
  points: string;
  since: string;
  until: string;
}

export interface TransactionReceipt {
  status: string;
  hash: string;
  blockNumber?: number;
  [key: string]: any;
}

export const LEADERBOARD_SOURCE_URL = "https://portal.genlayer.foundation/points";
