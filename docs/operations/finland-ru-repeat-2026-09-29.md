# FI russian-iperf3-servers repeat

Owner requested another original RU speed module and admin automation plan.
Run UTC16:29:31–16:31:20 (MSK19:29:31–19:31:20), 109 seconds, exit0.
Source SHA256 068d37703beab0ec7e44a24ed45f6e911af51511ea6476a85add7250fab3d3dc.
Audited cached upstream script; unmodified standard mode, 8 streams,10s,
15s per-test timeout, wrapper overall900s. No tuning/topology/restart.

Original terminal output:

```text
Server             Download        Upload          Ping
------             --------        ------          ----
Moscow             5606.4 Mbps     5606.4 Mbps     27 ms
Saint Petersburg   2202.0 Mbps     2223.1 Mbps     24 ms
Nizhny Novgorod    2114.2 Mbps     2134.9 Mbps     30 ms
Chelyabinsk        1751.9 Mbps     1768.4 Mbps     78 ms
Tyumen             518.7 Mbps      537.3 Mbps      56 ms
```

Labels are upstream's sender/receiver of one forward test, not independent
upload/download. No fallback city in this run. Strong positive repeat; cannot
infer constant bandwidth or mobile Telegram performance. Keep FI/EE equal;
earlier weaker results remain valid historical evidence, not verdict.
Post-run remnanode running, nginx active. Full owner output outside Git:
Temp/ArcVPN-multitest-569/FI-ru-repeat.txt and FI-ru-repeat.raw.log;
remote /opt/arcvpn/staging/fi-ru-repeat.log. No secret in committed evidence.

Earlier Multitest5/6/9 completed on FI/EE: FI9 Ookla crashed with std::logic_error,
exit134 on standalone Novosibirsk; this is not a zero-speed measurement.
Additional FI9 retry was stopped on owner's accelerated-closeout request.
Supplementary Kazan: FI2377Mbps forward receiver /154 reverse receiver,
67.932ms; EE915/609Mbps,38.627ms. EE Novosibirsk Ookla854.91 download,
566.90 upload,100.44ms. Private complete logs under the same Temp folder.

Architecture proposal: docs/roadmaps/admin-node-automation.md. Not implemented;
no new/modified skills. Next: owner agrees/revises workflow before runtime work.
