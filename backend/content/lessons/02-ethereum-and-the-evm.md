---
title: Ethereum & the EVM
module: Module 1 · Foundations
order: 2
minutes: 25
---

# Ethereum & the EVM

Bitcoin is a calculator; Ethereum is a computer. The **Ethereum Virtual Machine (EVM)** is a global, single-threaded computer whose state every node agrees on. Programs on it are **smart contracts**; running them costs **gas**.

## Accounts: two kinds of citizens

| | Externally Owned Account (EOA) | Contract Account |
|---|---|---|
| Controlled by | Private key (a human/wallet) | Its own code |
| Can initiate transactions | ✅ | ❌ (only reacts) |
| Has code | ❌ | ✅ |
| Example | Your MetaMask address | Uniswap router |

Every account has a **nonce** (transaction counter) and a **balance** in wei. 1 ETH = 10¹⁸ wei — Ethereum has no floats, everything is integer math.

```javascript
// Wei arithmetic with BigInt — exactly how ethers.js does it internally
const WEI_PER_ETH = 10n ** 18n;

const balanceWei = 2_500_000_000_000_000_000n; // 2.5 ETH
console.log("balance in ETH:", Number(balanceWei) / Number(WEI_PER_ETH));

const gasLimit = 21_000n;               // basic transfer
const maxFeePerGas = 30_000_000_000n;   // 30 gwei
const maxCost = gasLimit * maxFeePerGas;
console.log("max tx fee:", Number(maxCost) / Number(WEI_PER_ETH), "ETH");
```

## Gas: why every operation has a price

Gas prevents infinite loops from freezing the world computer, and pays validators. Since EIP-1559:

- **Base fee** — burned 🔥 (destroyed forever), adjusts per block with demand
- **Priority fee (tip)** — goes to the validator
- `total fee = gasUsed × (baseFee + tip)`

```javascript
// Simulate EIP-1559 base fee adjustment across blocks
let baseFee = 30; // gwei
const TARGET = 15_000_000, MAX = 30_000_000;

const blocks = [29_000_000, 30_000_000, 8_000_000, 15_000_000, 25_000_000];
for (const gasUsed of blocks) {
  const delta = baseFee * ((gasUsed - TARGET) / TARGET) * 0.125;
  baseFee = Math.max(0, baseFee + delta);
  console.log(`block used ${(gasUsed/1e6).toFixed(0)}M gas → next base fee ${baseFee.toFixed(2)} gwei`);
}
```

> 💡 Notice: full blocks push the fee up 12.5%, empty blocks pull it down. Demand is priced automatically — no fee market auctions.

## The EVM itself

The EVM is a **stack machine** with 256-bit words. Solidity compiles to its bytecode. It has three data areas:

1. **Stack** — computation scratchpad (max 1024 deep)
2. **Memory** — temporary, wiped after each call
3. **Storage** — permanent key-value store, *the expensive one* (~20,000 gas to write a new slot!)

```python
# A miniature stack machine — the EVM's core idea in 20 lines
code = ["PUSH 6", "PUSH 7", "MUL", "PUSH 58", "ADD", "PRINT"]

stack = []
for op in code:
    parts = op.split()
    if parts[0] == "PUSH":
        stack.append(int(parts[1]))
    elif parts[0] == "MUL":
        b, a = stack.pop(), stack.pop()
        stack.append(a * b)
    elif parts[0] == "ADD":
        b, a = stack.pop(), stack.pop()
        stack.append(a + b)
    elif parts[0] == "PRINT":
        print("top of stack:", stack[-1])
```

```quiz
{
  "question": "Why does writing to storage cost ~20,000 gas while adding two numbers costs 3?",
  "options": [
    "Storage writes are cryptographically signed",
    "Every full node on Earth must persist that storage slot forever",
    "It's an arbitrary choice by the Ethereum Foundation",
    "Storage uses floating point which is slow"
  ],
  "answer": 1,
  "explain": "State is replicated across every node and lives forever. You're not paying for one write — you're paying rent-in-advance for tens of thousands of machines to store it permanently."
}
```

## Exercise

Ask the tutor: **"Make a Python file evm.py that extends the mini stack machine with SUB, DIV and a SSTORE/SLOAD storage dict, then run it with a small program."**
