---
title: Wallets, Keys & Transactions
module: Module 1 · Foundations
order: 3
minutes: 20
---

# Wallets, Keys & Transactions

Your wallet doesn't hold coins. It holds a **private key** — a 256-bit number — and the coins live on the chain, mapped to the address derived from that key. *Not your keys, not your coins* is literal.

## From private key to address

The pipeline is one-way at every step:

```
private key (256-bit random) → [elliptic curve] → public key → [keccak256, last 20 bytes] → address
```

You can go left-to-right in microseconds. Going right-to-left would take longer than the age of the universe. That asymmetry *is* the security model.

```javascript
// Generate a (toy) keypair pipeline — same shape as the real thing.
// Real wallets use the secp256k1 curve; we simulate the one-way steps with hashing.
const { createHash, randomBytes } = require("node:crypto");

const privateKey = randomBytes(32).toString("hex");
const publicKey  = createHash("sha512").update(privateKey).digest("hex"); // stand-in for EC multiply
const address    = "0x" + createHash("sha256").update(publicKey).digest("hex").slice(-40);

console.log("private key:", privateKey.slice(0, 16) + "…  (NEVER share)");
console.log("public key: ", publicKey.slice(0, 16) + "…");
console.log("address:    ", address);
```

## Seed phrases (BIP-39)

Twelve words encode 128 bits of entropy plus a checksum. Each word is an index into a fixed 2048-word list — 12 words × 11 bits = 132 bits. One seed derives *infinite* accounts (BIP-32/44 hierarchical derivation).

```python
# Why 12 words is enough: the math of seed phrase security
combos = 2048 ** 12
guesses_per_sec = 10**12          # a trillion guesses/sec (generous attacker)
seconds = combos / guesses_per_sec
years = seconds / (60*60*24*365)

print(f"possible phrases : {combos:.2e}")
print(f"years to brute-force at 1T guesses/sec: {years:.2e}")
print(f"age of universe  : 1.38e+10 years — {years/1.38e10:.1e}× longer")
```

## Anatomy of a transaction

Every Ethereum transaction is a signed message with these fields:

| Field | Meaning |
|---|---|
| `nonce` | Sender's tx counter — prevents replay |
| `to` | Recipient (empty = contract deployment) |
| `value` | Wei to transfer |
| `data` | Calldata — which function + arguments |
| `maxFeePerGas` / `maxPriorityFeePerGas` | EIP-1559 fee caps |
| `signature (v, r, s)` | Proof the key-holder authorised it |

The signature is the magic: it proves authorship **without revealing the private key**, and it covers every field — change one byte and the signature is invalid.

```javascript
// Signing & verification, conceptually (HMAC as a stand-in for ECDSA)
const { createHmac } = require("node:crypto");

const privateKey = "my-secret-key";
const tx = { nonce: 7, to: "0xCAFE…", value: "1.5 ETH" };

const sign = (tx, key) => createHmac("sha256", key).update(JSON.stringify(tx)).digest("hex");

const signature = sign(tx, privateKey);
console.log("signature:", signature.slice(0, 24) + "…");

// A node verifies by recomputing. Now an attacker bumps the value:
const tampered = { ...tx, value: "999 ETH" };
console.log("valid for original :", sign(tx, privateKey) === signature);
console.log("valid for tampered :", sign(tampered, privateKey) === signature);
```

```quiz
{
  "question": "You send a transaction with nonce 5, then immediately another with nonce 7. What happens to the second?",
  "options": [
    "It executes first because higher nonce = higher priority",
    "It waits in the mempool until a transaction with nonce 6 is processed",
    "It fails permanently",
    "The network merges them"
  ],
  "answer": 1,
  "explain": "Nonces must be strictly sequential per account. Tx 7 is valid but can't execute until 6 lands — this is also how you can 'cancel' a stuck tx: resend the same nonce with a higher fee."
}
```

## Exercise

Ask the tutor: **"Create wallet.py that derives 5 toy addresses from one seed using hierarchical hashing (like BIP-32), and run it."**
