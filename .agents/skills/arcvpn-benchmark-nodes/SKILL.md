---
name: arcvpn-benchmark-nodes
description: Benchmark ArcVPN VPS nodes using the owner's Multitest preference, preserve full terminal output, and compare Russian routes honestly. Use for requests to measure node speed, ping, IP/geolocation, or server performance; not as a substitute for real client VPN testing.
---

# Benchmark ArcVPN nodes

1. Read `AGENTS.md`, `docs/operations/server-benchmark-method.md`, and
   `.codex/server-inventory.toml`; use `$arcvpn-server-ops` for access.
   Confirm targets are owner-controlled and active. Do not test returned,
   offline or unknown servers just because an old inventory lists them.
2. Use the owner's Multitest modules appropriate to the question. RU iPerf
   (menu 5) is the primary Russia comparison; TLAB (6) has separate forward
   and reverse tests including Kazan, subject to public-server failures;
   bench.sh (9) is a global/system test, not a Moscow/Kazan proxy. If the
   requested city is absent, run a separately labelled verified endpoint or
   say it was not measured. Keep original module names, versions and SHA256.
3. Review remote code and nested downloads before execution. Prefer the
   audited cached scripts; do not blindly execute latest curl|bash. No report
   uploads, BBR/IPv6/network tuning, service restarts or destructive cleanup.
   Bound runtime, workload and disk use; run heavy tests sequentially per host.
4. Preserve raw logs privately and provide the owner the *complete* copyable
   terminal text (ANSI/spinner rendering may be normalized without rewriting
   measurements). Include tool exit codes, timestamps, endpoints and failures;
   do not offer only a paraphrased table when full output was requested.
5. Interpret RU module Upload/Download as sender/receiver of one forward
   iPerf run, not two independent directions. Flag 0 receiver/nonzero sender,
   fallback cities, timeout, hidden TLAB rows and Ookla crashes as invalid or
   inconclusive rather than zero bandwidth. Compare repeated runs and evening
   behavior; ping, channel rate and VPN user throughput are distinct.
6. Keep direct VPS benchmarks separate from real-tunnel tests through Happ,
   Moscow, CDN and Telegram. Do not reprioritize AutoSelect or buy/retire a
   node based on one run. Report post-test node health and concise, evidence-
   backed conclusions. Save only non-secret aggregate results in Git.
