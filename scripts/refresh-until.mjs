// Sends refresh() until one is ACCEPTED with a majority, logging every attempt (LEADER_TIMEOUT and VALIDATORS_TIMEOUT are retried).
//   SUMMIT=0x... MAX=15 node scripts/refresh-until.mjs
import { readFileSync } from "fs";
import { createAccount, createClient } from "genlayer-js";
import { testnetBradbury } from "genlayer-js/chains";

const SUMMIT = process.env.SUMMIT, MAX = Number(process.env.MAX || 15);
if (!SUMMIT) { console.error("set SUMMIT=<contract address>"); process.exit(1); }
const wallets = JSON.parse(readFileSync("C:/Users/olumi/.genlayer-test-wallets/wallets.json", "utf8"));
const client = createClient({ chain: testnetBradbury, account: createAccount(wallets["gl-test-1"].privateKey) });
const plain = (x) => (x instanceof Map ? Object.fromEntries([...x].map(([k, v]) => [k, plain(v)])) : Array.isArray(x) ? x.map(plain) : typeof x === "bigint" ? x.toString() : x);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const ts = () => new Date().toISOString().slice(11, 19);
for (let a = 1; a <= MAX; a++) {
  const hash = await client.writeContract({ address: SUMMIT, functionName: "refresh", args: [] });
  console.log(`[${ts()}] attempt ${a} sent ${hash}`);
  let r;
  for (let i = 0; i < 120; i++) {
    r = await client.getTransaction({ hash }).catch(() => null);
    if (r && r.statusName !== "PENDING" && r.statusName !== "ACTIVATED" && r.statusName !== "PROPOSING" && r.statusName !== "COMMITTING" && r.statusName !== "REVEALING") break;
    await sleep(15000);
  }
  console.log(`[${ts()}] attempt ${a}: ${r?.statusName} exec=${r?.txExecutionResultName} result=${r?.resultName}`);
  if (r && (r.statusName === "ACCEPTED" || r.statusName === "FINALIZED") && r.txExecutionResultName === "FINISHED_WITH_RETURN") {
    console.log("podium", JSON.stringify(plain(await client.readContract({ address: SUMMIT, functionName: "get_podium", args: [] }))));
    console.log("DONE", hash);
    process.exit(0);
  }
  await sleep(20000);
}
console.log("no attempt was accepted"); process.exit(1);
