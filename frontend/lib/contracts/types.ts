/**
 * TypeScript types for the GenLayer Summit contract
 */

export interface Seat {
  rank: number;
  headline: string;
  points: string;
  since: string;
}

export interface PodiumEvent {
  rank: number;
  headline: string;
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
