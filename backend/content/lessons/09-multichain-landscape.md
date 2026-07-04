---
title: The Multi-Chain Landscape
module: Module 4 · Beyond Ethereum
order: 9
minutes: 25
---

# The Multi-Chain Landscape

There is no "best chain" — there are different answers to the same impossible question: **how do you get security, decentralization, and speed at once?** (You don't. You pick two and engineer around the third.)

## The map

| Chain | VM / Lang | Model | Finality | Superpower | Cost of it |
|---|---|---|---|---|---|
| Bitcoin | Script (tiny) | UTXO | ~60 min | Maximum credible neutrality | Almost no programmability |
| Ethereum | EVM / Solidity | Accounts | ~13 min | Deepest liquidity + security | Expensive L1, slow |
| Solana | SBF / Rust | Accounts (stateless programs) | ~seconds | Raw throughput, parallel exec | Heavy validators |
| Arbitrum / Base / OP (L2s) | EVM / Solidity | Rollups → Ethereum | mins (soft: secs) | Cheap EVM, inherits ETH security | Sequencer centralization (today) |
| Cosmos | CosmWasm / Rust, Go | App-chains + IBC | ~6 sec | Sovereign chains that interoperate | Each chain bootstraps its own security |
| Polkadot | WASM / Rust | Parachains | ~30 sec | Shared security for custom chains | Complexity, slot economics |

## UTXO vs Accounts — the oldest split

```python
# Bitcoin doesn't have balances. It has unspent outputs (UTXOs) — like cash notes.
utxos = [
    {"txid": "a1", "amount": 0.7, "owner": "alice"},
    {"txid": "b2", "amount": 0.5, "owner": "alice"},
]

def send(utxos, owner, to, amount):
    picked, total = [], 0
    for u in [u for u in utxos if u["owner"] == owner]:
        picked.append(u); total += u["amount"]
        if total >= amount: break
    if total < amount:
        return None, f"insufficient: {total} < {amount}"
    rest = [u for u in utxos if u not in picked]
    rest.append({"txid": "new1", "amount": amount, "owner": to})
    change = round(total - amount, 8)
    if change:  # you always spend WHOLE notes and get change back
        rest.append({"txid": "new2", "amount": change, "owner": owner})
    return rest, f"spent {len(picked)} utxos, change {change}"

utxos, msg = send(utxos, "alice", "bob", 0.9)
print(msg)
for u in utxos: print(u)
```

Run it — notice Alice's two "notes" become one for Bob plus change back to herself. Ethereum/Solana instead keep a mutable balance per account: simpler to program, harder to parallelize and less private.

## Rollups: Ethereum's scaling bet

An L2 executes transactions off-chain, then posts compressed data + proof to Ethereum:

```python
# Why rollups are cheap: amortizing L1 cost across a batch
l1_base_fee_gwei = 30
gas_per_blob_batch = 250_000        # rough cost to post a batch
txs_per_batch = 1500

l1_cost_eth = gas_per_blob_batch * l1_base_fee_gwei * 1e-9
per_tx = l1_cost_eth / txs_per_batch

print(f"batch posting cost : {l1_cost_eth:.5f} ETH")
print(f"L1 security per tx : {per_tx*1e6:.2f} micro-ETH (~fractions of a cent)")
print(f"vs direct L1 send  : {21000 * l1_base_fee_gwei * 1e-9:.5f} ETH")
```

- **Optimistic rollups** (Arbitrum, OP, Base): assume validity, allow ~7 days for fraud proofs.
- **ZK rollups** (zkSync, Starknet, Scroll, Linea): post a validity proof — mathematically final immediately. The provers? Written in Rust.

## Picking your stack as a developer

- **Solidity + EVM** → biggest job market, most tooling, deploys on 20+ chains (L1s + all L2s).
- **Rust** → Solana programs (via Anchor), plus core infrastructure everywhere: clients, provers, indexers. Steeper curve, rarer skills, better pay.
- **Go / TypeScript** → node tooling, indexers, bots, dApp frontends.

The strongest position: understand the EVM *and* Solana's model — most real teams are multi-chain now.

```quiz
{
  "question": "An optimistic rollup withdrawal to L1 takes ~7 days. Why?",
  "options": [
    "Ethereum is congested",
    "The sequencer batches withdrawals weekly",
    "That's the fraud-proof window: time for anyone to prove the rollup posted an invalid state",
    "Bridges are slow by regulation"
  ],
  "answer": 2,
  "explain": "Optimistic = assume the posted state is valid unless someone proves otherwise. The challenge window is the security. ZK rollups replace it with a validity proof, so exits are fast — that's their core advantage."
}
```

## Exercise

Ask the tutor: **"Quiz me across all chains: 5 rapid-fire questions comparing Ethereum, Solana, Bitcoin and L2s — grade my answers and tell me what to study next."**
