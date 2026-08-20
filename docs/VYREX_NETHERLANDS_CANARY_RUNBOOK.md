# Provider node canary runbook

Статус: Vyrex отменён владельцем. 2026-08-20 получен однодневный пробник реселлера
`159.200.230.224`; фактический origin — AS58212 dataforest GmbH, Frankfurt, а не Hetzner.
Пробник добавлен только в telemetry allowlist, без Remnawave и без пользователей.

## Инварианты

- Не менять `/sub/<sub_id>`, device subscription IDs и VLESS UUID пользователей.
- Новая Node, Config Profile, inbounds, hosts и internal squad создаются отдельно.
- До прохождения 72 часов использовать только synthetic user; реальные пользователи
  и production squad не затрагиваются.
- Private Reality key и RemnaNode secret хранятся только на control-plane/VPS в файлах
  `0600`; в Git и отчёты попадают только public key/SID/порты.
- Один провайдер/ASN не должен стать единственной площадкой всех production nodes.

## Данные, необходимые перед VPN canary

- публичный IPv4/IPv6 и SSH endpoint кандидата;
- root/sudo access через secret storage;
- выделенный hostname, направленный только на новую VPS;
- заявленный port policy, лимит/стоимость трафика и abuse constraints.

## Установка

1. Зафиксировать provider/ASN, CPU/RAM/disk/network и baseline до установки.
2. Обновить ОС, включить time sync, firewall и автоматические security updates.
3. Создать отдельный Remnawave Config Profile с уникальными
   inbound tags, TCP Reality и Hysteria2/UDP. Не переиспользовать private key.
4. Создать Node и isolated canary squad; добавить только synthetic user.
5. Установить RemnaNode по официальному методу, secret передать вне shell history.
6. Установить `monitoring/arcvpn_node_agent.py`, service/timer и отдельный env `0600`.
7. Проверить reboot recovery, panel outage behaviour и rollback (detach canary squad).

## Baseline и 72 часа

Node agent работает каждую минуту; network probe — каждые 10 минут. Отчёт:

```bash
python3 monitoring/compare_node_quality.py \
  --db /root/ArcVPN/database/vpn_bot.db \
  --hours 72 --source agent \
  --evening-start-utc 15 --evening-end-utc 21 \
  --output /root/ArcVPN/backup/diagnostics/provider-canary-72h.json
```

Обязательные измерения:

- coverage, loss, jitter, latency p50/p95, DNS/HTTPS p50/p95;
- download p10/p50/p95 и отдельные single/multi-stream tests из РФ;
- CPU, RAM, load и CPU steal, особенно 18:00–00:00 МСК;
- TCP Reality через реальный Xray client;
- Hysteria2 и UDP/QUIC через реальный клиент, не TCP-connect;
- YouTube playback/thumbnail/generate_204, Instagram media, Gemini и Claude;
- route/ASN/exit country, IPv4/IPv6/DNS leaks;
- restart/reboot, потеря Panel и восстановление Node.

YouTube/Instagram/Gemini/Claude проверяются функционально и без логина. HTTP 403 из-за
геополитики/anti-bot фиксируется отдельно от network failure; обход CAPTCHA не выполнять.
Ручные тесты из РФ проводить минимум утром, днём и каждый вечер, одинаковым клиентом и
сравнивать с France, Finland и Germany в те же временные окна.

## Gate

- не менее 95% ожидаемых samples;
- loss p95 <= 1%; jitter p95 <= 20 ms; CPU steal p95 <= 5%;
- download p10 >= 100 Mbps;
- нет устойчивого вечернего ухудшения latency/loss/speed более чем на 30% от day baseline;
- оба транспорта и UDP проходят весь период;
- все четыре внешних сервиса работоспособны либо ограничение доказано как service policy,
  одинаковое для сравниваемых нод;
- rollback rehearsal успешен, URL/UUID не менялись.

## Решение

- `production`: все gates пройдены и кандидат не хуже медианы действующих обычных nodes;
- `reserve`: стабильна, но скорость/latency хуже либо есть воспроизводимое ограничение сервиса;
- `reject`: gate провален, вечерняя деградация, высокий steal/loss или transport instability.

После положительного synthetic gate: 2–5 добровольцев, затем 5% → 25% → 50% → 100%.
Каждая ступень минимум 24 часа; автоматический rollback — detach Vyrex inbounds/host от
production squad без изменения пользователя, UUID или URL.

Однодневный бесплатный trial не удовлетворяет 72-часовому gate. Его можно использовать
для первичного 24-часового отсева; для доказательного решения сервер нужно продлить минимум
на три дня. Заявление реселлера о Hetzner не принимать без совпадения origin ASN/IP WHOIS.
