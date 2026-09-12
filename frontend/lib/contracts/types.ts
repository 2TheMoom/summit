/**
 * TypeScript types for the GenLayer Summit contract
 */

export interface Champion {
  headline: string;
  points: string;
  since: string;
}

export interface TitleHolder {
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
