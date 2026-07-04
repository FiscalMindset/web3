---
title: Blockchain Foundations
module: Module 1 · Foundations
order: 1
minutes: 20
---

# Blockchain Foundations

A blockchain is a **linked list with trust issues**. Each block points at the previous one — not by memory address, but by *cryptographic hash*. Change any byte in history and every hash after it breaks.

## Hashing: the glue of the chain

A hash function takes any input and produces a fixed-size fingerprint. Ethereum uses Keccak-256; Bitcoin uses SHA-256. Two properties matter:

1. **Deterministic** — same input, same output, forever.
2. **Avalanche effect** — flip one bit, the output changes completely.

Try it right here — press **Run** and watch how `"web3"` vs `"web4"` gives totally unrelated hashes:

```javascript
const { createHash } = require("node:crypto");

for (const word of ["web3", "web4"]) {
  const h = createHash("sha256").update(word).digest("hex");
  console.log(`${word} → ${h}`);
}
```

## Building a tiny blockchain

Let's build the simplest possible chain: each block stores data, a timestamp, and the previous block's hash.

```javascript
const { createHash } = require("node:crypto");

const sha = (s) => createHash("sha256").update(s).digest("hex");

class Block {
  constructor(index, data, prevHash) {
    this.index = index;
    this.data = data;
    this.prevHash = prevHash;
    this.hash = sha(index + data + prevHash);
  }
}

const chain = [new Block(0, "genesis", "0".repeat(64))];
chain.push(new Block(1, "alice pays bob 5", chain[0].hash));
chain.push(new Block(2, "bob pays carol 2", chain[1].hash));

console.log(chain.map(b => `#${b.index} ${b.hash.slice(0, 16)}… ← ${b.prevHash.slice(0, 16)}…`).join("\n"));

// Now tamper with history:
chain[1].data = "alice pays bob 5000";
const recomputed = sha(chain[1].index + chain[1].data + chain[1].prevHash);
console.log("\nBlock 1 stored hash:    " + chain[1].hash.slice(0, 16) + "…");
console.log("Block 1 recomputed:     " + recomputed.slice(0, 16) + "…");
console.log("Tampering detected:", recomputed !== chain[1].hash);
```

> 💡 **Ask the tutor**: try "why can't I just recompute all the hashes after tampering?" — that question leads straight to proof-of-work.

## Why can't attackers just rewrite everything?

Because of **consensus**. Thousands of nodes hold copies of the chain. To rewrite history you'd need to outpace the entire honest network — via hash power (Proof of Work) or staked capital (Proof of Stake). Ethereum moved to Proof of Stake in 2022 ("The Merge"), cutting energy use ~99.95%.

| | Proof of Work | Proof of Stake |
|---|---|---|
| Security deposit | Electricity + hardware | Staked ETH (32 per validator) |
| Attack cost | Buy 51% of hash power | Buy & stake huge amounts of ETH (which gets slashed) |
| Finality | Probabilistic | Checkpoint finality (~13 min) |

```quiz
{
  "question": "If you change data in block #1 of a 10-block chain, what breaks?",
  "options": [
    "Only block #1's hash",
    "Block #1's hash, and the prevHash links of every block after it",
    "Nothing, blockchains auto-repair",
    "Only the last block"
  ],
  "answer": 1,
  "explain": "Block #2 stores block #1's ORIGINAL hash as prevHash. After tampering, recomputed hash ≠ stored prevHash, and this mismatch cascades through every following block."
}
```

## Exercise

Ask the tutor: **"Create a file chain.js that adds proof-of-work mining (difficulty 4) to the tiny blockchain, then run it."** Watch it create and execute the file in your workspace →
