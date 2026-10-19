# Freeze log (append-only)

## Freeze A — protocol, subjects, code, frozen dependencies

- Commit: `79becc414dd0d1d9ef30db7b6a1ea42951e23ad4` (study repository `qsurvcert_pilot`, branch `impl/rq3-feasibility-gate`), 2026-10-09 08:32:40 +0300
- Manifest: `freeze/FREEZE_A.sha256` (70 files), SHA-256 `8085ddff7ad820ff497f14ca306318f7a18996be2ddd4ef93b95ce6ee93384e4`
- Clean-checkout check: every entry of FREEZE_A.sha256 verifies on a fresh worktree of the commit
- RFC 3161 timestamp: FreeTSA (https://freetsa.org/tsr), request `FREEZE_A.tsq` (SHA-256 digest of the manifest only, nonce 0x7E78884894A49167), reply `FREEZE_A.tsr`, serial 0x090FD43B, **2026-10-09 05:33:09 UTC**, status Granted; `openssl ts -verify -digest <manifest sha256> -in FREEZE_A.tsr -CAfile tsa/freetsa_cacert.pem -untrusted tsa/freetsa_tsa.crt` → **Verification: OK** (`FREEZE_A.tsr.txt`)
- Only the 32-byte digest left the machine.
- State at Freeze A: no mutant exists; no native mutant outcome exists.

## Freeze A receipt

- Commit: `66dfa9331722e8484f012d13f7fafb282977e949`, 2026-10-09 08:33:23 +0300 (FREEZE_A.tsq, FREEZE_A.tsr, FREEZE_A.tsr.txt, tsa/ certificates, this log)

## Freeze B — exact mutant population

- Commit: `a76211b9a47b87a1e959375603ae5cd973679c17`, 2026-10-09 08:35:52 +0300
- Manifest: `freeze/FREEZE_B.sha256` (245 files: 240 mutant files, MUTANT_MANIFEST.csv, MUTATION_POOL.csv, CENSUS.json, INDEPENDENCE.json, STATIC_CHECK.json), SHA-256 `0899b9a10e9f0566bbf3c67b3a32930bcd88b13880afcfea9745113a237792be`
- Population: 4 subjects x 30 = 120 mutants, 120 distinct definitions; materialization re-run byte-identical (deterministic); cohort enumerator PD-1 as declared at Freeze A
- Independence: 0 matches against 2,626 earlier programs (originals, mutants and pairs); static QUTest compatibility: 0 violations
- Clean-checkout check: FREEZE_A.sha256 and FREEZE_B.sha256 both verify on a fresh worktree of the commit
- RFC 3161 timestamp: FreeTSA, request `FREEZE_B.tsq` (digest only), reply `FREEZE_B.tsr`, serial 0x090FD659, **2026-10-09 05:35:54 UTC**, status Granted, `openssl ts -verify` → **Verification: OK** (`FREEZE_B.tsr.txt`)
- State at Freeze B: no mutant executed; no survival, diagnosis or validation outcome exists (records/ holds only original-program dry runs).
