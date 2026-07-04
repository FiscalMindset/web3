---
title: Rust for Web3
module: Module 4 · Beyond Ethereum
order: 7
minutes: 30
---

# Rust for Web3

JavaScript talks *to* blockchains. **Rust builds them.** Solana programs, Polkadot, NEAR, Sui and Aptos node software, most of Ethereum's newest clients (Reth), the fastest zk-provers — all Rust. If you want to go deeper than dApp frontends, this is the language of the engine room.

## Why chains chose Rust

| Need | Why Rust delivers |
|---|---|
| No crashes from memory bugs | Ownership + borrow checker: whole bug classes (use-after-free, data races) can't compile |
| Deterministic performance | No garbage collector — no random GC pauses while validating blocks |
| Untrusted input everywhere | `Result`/`Option` force you to handle every failure path explicitly |
| Tiny on-chain binaries | Compiles to lean native code and WASM/SBF for on-chain deployment |

## Ownership in 60 seconds

Every value has exactly **one owner**. When the owner goes out of scope, the value is freed. No GC needed, no manual `free` — the compiler proves it.

```rust
fn main() {
    let chain = vec!["genesis", "block1", "block2"];

    let stolen = chain;              // ownership MOVES to `stolen`
    // println!("{:?}", chain);      // ← uncomment: compile error! `chain` no longer owns it

    println!("{:?}", stolen);

    // borrowing: look, don't take
    let len = measure(&stolen);      // & = immutable borrow
    println!("chain length: {}", len);
    println!("still mine: {:?}", stolen); // works — we only lent it
}

fn measure(c: &Vec<&str>) -> usize {
    c.len()
}
```

Run it, then uncomment the marked line and run again — the compiler error you'll see is Rust *preventing a use-after-move at compile time*. On a blockchain node, that's a double-spend-style bug that never ships.

## A blockchain in Rust

Same idea as lesson 01's JavaScript version — but typed, and using Rust's std hasher:

```rust
use std::collections::hash_map::DefaultHasher;
use std::hash::{Hash, Hasher};

#[derive(Debug)]
struct Block {
    index: u64,
    data: String,
    prev_hash: u64,
    hash: u64,
}

fn hash_of(index: u64, data: &str, prev: u64) -> u64 {
    let mut h = DefaultHasher::new();
    (index, data, prev).hash(&mut h);
    h.finish()
}

impl Block {
    fn new(index: u64, data: &str, prev_hash: u64) -> Self {
        let hash = hash_of(index, data, prev_hash);
        Block { index, data: data.to_string(), prev_hash, hash }
    }
}

fn main() {
    let mut chain = vec![Block::new(0, "genesis", 0)];
    chain.push(Block::new(1, "alice pays bob 5", chain[0].hash));
    chain.push(Block::new(2, "bob pays carol 2", chain[1].hash));

    for b in &chain {
        println!("#{} {:016x} ← {:016x}", b.index, b.hash, b.prev_hash);
    }

    // tamper, then verify like a full node would
    chain[1].data = "alice pays bob 5000".to_string();
    let valid = chain.windows(2).all(|w| {
        w[1].prev_hash == hash_of(w[0].index, &w[0].data, w[0].prev_hash)
    });
    println!("\nchain valid after tampering? {}", valid);
}
```

## Errors you cannot ignore

In JS, a forgotten `try/catch` crashes at runtime. In Rust, fallible operations return `Result<T, E>` and the compiler **refuses to let you forget**:

```rust
fn transfer(balance: u64, amount: u64) -> Result<u64, String> {
    balance
        .checked_sub(amount)                     // returns Option — overflow-safe math
        .ok_or_else(|| format!("insufficient funds: have {balance}, need {amount}"))
}

fn main() {
    for amt in [30, 500] {
        match transfer(100, amt) {
            Ok(rest) => println!("✅ sent {amt}, remaining {rest}"),
            Err(e) => println!("❌ {e}"),
        }
    }
}
```

`checked_sub` is exactly how real Solana programs guard lamport math — an unchecked subtraction underflow in a smart contract is a mint-infinite-money bug.

```quiz
{
  "question": "Why do blockchain nodes avoid garbage-collected languages for their core?",
  "options": [
    "GC languages can't do cryptography",
    "A GC pause at the wrong moment delays block validation/production — determinism and latency matter",
    "Garbage collectors use too much disk",
    "They can't — Ethereum's Go client Geth doesn't exist"
  ],
  "answer": 1,
  "explain": "It's about tail latency and determinism, not possibility (Geth is Go!). But performance-critical newer clients and chains (Reth, Solana, Sui) chose Rust precisely to eliminate GC pauses and memory bugs. "
}
```

## Exercise

Ask the tutor: **"Create pow.rs — add proof-of-work mining (leading zero bits on the u64 hash) to the Rust blockchain, run it, and show how mining time grows with difficulty."**
