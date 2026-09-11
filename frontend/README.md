# Summit Frontend

Next.js frontend for Summit - a live scoreboard-style readout of whoever's
currently #1 on Hacker News, verified on GenLayer.

## Setup

1. Install dependencies:

```bash
npm install
```

2. Create `.env` file:
```bash
cp .env.example .env
```

3. Configure environment variables:
   - `NEXT_PUBLIC_CONTRACT_ADDRESS` - Summit contract address
   - `NEXT_PUBLIC_GENLAYER_RPC_URL` - GenLayer Bradbury RPC URL (default: https://rpc-bradbury.genlayer.com)

## Development

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

## Build

```bash
npm run build
npm start
```

## Tech Stack

- **Next.js 15** - React framework with App Router
- **TypeScript** - Type safety
- **Tailwind CSS v4** - Styling, "Alpine Signal" theme
- **genlayer-js** - GenLayer blockchain SDK
- **TanStack Query (React Query)** - Data fetching and caching
- **Radix UI** - Accessible component primitives
- **shadcn/ui** - Pre-built UI components

## Wallet Management

The app connects via MetaMask to GenLayer's Bradbury testnet.

## Features

- **Live titleholder readout**: The current #1 Hacker News story and its point total, always in sync with the real page.
- **Verify Now**: Anyone can trigger `refresh()` to re-check the live source.
- **Succession timeline**: Past titleholders, archived on-chain with how long each held the top spot.
