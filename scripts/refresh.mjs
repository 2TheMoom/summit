// Calls refresh() on the deployed Summit with a dedicated testnet wallet kept outside the repo, then prints the podium.
//   SUMMIT=0x... node scripts/refresh.mjs
import { readFileSync } from "fs";
import { createAccount, createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";

const SUMMIT = process.env.SUMMIT;
if (!SUMMIT) { console.error("set SUMMIT=<contract address>"); process.exit(1); }
const wallets = JSON.parse(readFileSync("C:/Users/olumi/.genlayer-test-wallets/wallets.json", "utf8"));
const client = createClient({ chain: testnetBradbury, account: createAccount(wallets["gl-test-1"].privateKey) });
const plain = (x) => (x instanceof Map ? Object.fromEntries([...x].map(([k, v]) => [k, plain(v)])) : Array.isArray(x) ? x.map(plain) : typeof x === "bigint" ? x.toString() : x);
const hash = await client.writeContract({ address: SUMMIT, functionName: "refresh", args: [] });
console.log("tx", hash);
const r = await client.waitForTransactionReceipt({ hash, status: "ACCEPTED", retries: 120, interval: 5000 });
console.log("status", r.statusName, "exec", r.txExecutionResultName, "result", r.resultName);
console.log("podium", JSON.stringify(plain(await client.readContract({ address: SUMMIT, functionName: "get_podium", args: [] }))));
