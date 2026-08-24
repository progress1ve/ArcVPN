<script>
  import { writable } from 'svelte/store'
  import { SvelteFlow, Background, BackgroundVariant, Controls, MiniMap, addEdge } from '@xyflow/svelte'
  import ArcFlowNode from './ArcFlowNode.svelte'
  import '@xyflow/svelte/dist/style.css'

  export let data
  const nodes = writable([])
  const graphEdges = writable([])
  let activeScheme = 'auto'
  let draftChanged = false
  let findingsOpen = true
  let addedIndex = 0
  let selectedNodeId = ''
  let appliedGraphKey = ''
  let pendingGraphKey = ''
  const nodeTypes = { arc: ArcFlowNode }

  $: schemes = data?.remnawave?.connection_schemes || []
  $: mainNodes = (data?.remnawave?.nodes || []).filter((node) => !node.disabled).slice(0, 4)
  $: lteEdges = data?.remnawave?.lte_edges || []
  $: if (schemes.length && !schemes.some((scheme) => scheme.id === activeScheme)) activeScheme = schemes[0].id
  $: graphKey = JSON.stringify({ activeScheme, main: mainNodes.map((node) => [node.uuid || node.id, node.name, node.connected, node.users_online]), edges: lteEdges.map((item) => [item.id, item.country_code]) })
  $: if (graphKey !== appliedGraphKey) synchronizeGraph(graphKey)
  $: findings = validateGraph($nodes, $graphEdges)
  $: blocked = findings.some((item) => item.severity === 'critical')
  $: selectedNode = $nodes.find((node) => node.id === selectedNodeId)

  const palette = [['Входная нода','in'],['Транзитная нода','transit'],['CDN','cdn'],['WARP','warp'],['Внешний прокси','proxy'],['Blackhole','block']]

  function synchronizeGraph(nextKey) {
    if (draftChanged && appliedGraphKey) pendingGraphKey = nextKey
    else {
      rebuildGraph()
      appliedGraphKey = nextKey
      pendingGraphKey = ''
    }
  }
  function switchScheme(event) {
    activeScheme = event.currentTarget.value
    draftChanged = false
    appliedGraphKey = ''
    pendingGraphKey = ''
  }
  function resetDraft() {
    draftChanged = false
    rebuildGraph()
    appliedGraphKey = pendingGraphKey || graphKey
    pendingGraphKey = ''
  }
  function markNodeChanges(changes) {
    if (changes?.some((change) => ['position', 'add', 'remove'].includes(change.type))) draftChanged = true
  }
  function markEdgeChanges(changes) {
    if (changes?.some((change) => ['add', 'remove'].includes(change.type))) draftChanged = true
  }

  function rebuildGraph() {
    const items = mainNodes.length ? mainNodes : [{ name: 'Нет доступных main-нод', connected: false }]
    const available = items.filter((node) => node.connected).length
    const online = items.reduce((total, node) => total + Number(node.users_online || 0), 0)
    const scheme = schemes.find((item) => item.id === activeScheme) || schemes[0] || { kind: 'client_balancer' }
    const gateway = flowNode('gateway', 'Gateway', 'клиентский профиль', 25, 215, 'gateway', '⌂', { entry: true })
    const internet = flowNode('internet', 'Internet', 'итоговый egress', 825, 215, 'internet', '◎', { exit: true })
    if (scheme.kind === 'direct_cdn') {
      nodes.set([
        gateway,
        flowNode('cdn', 'CDN', scheme.public_host || 'публичный edge', 285, 215, 'cdn', '☁', { badge: scheme.healthy ? 'online' : 'ошибка', offline: !scheme.healthy }),
        flowNode('origin', 'Входная нода', scheme.origin || 'RemnaNode origin', 555, 215, 'node', '▣', { badge: 'XHTTP' }),
        internet
      ])
      graphEdges.set([edge('gateway-cdn', 'gateway', 'cdn', 'TLS/XHTTP'), edge('cdn-origin', 'cdn', 'origin', 'origin'), edge('origin-internet', 'origin', 'internet')])
    } else {
      const fallback = scheme.kind === 'client_cdn_fallback'
      nodes.set([
        gateway,
        flowNode('selector', fallback ? 'Видимый балансировщик' : 'Автовыбор', `leastLoad · ${scheme.probe_interval_seconds || 20} сек`, 280, 215, 'selector', '⌘'),
        flowNode('main-pool', 'Входные ноды', `${available}/${items.length} доступны · ${online} онлайн`, 545, fallback ? 90 : 215, available ? 'node' : 'node offline', '▣', { badge: available ? 'online' : 'offline', offline: !available }),
        ...(fallback ? [flowNode('cdn', 'Скрытый CDN fallback', scheme.origins?.join(' + ') || 'NL + DE', 545, 340, 'cdn', '☁', { badge: 'полный отказ' })] : []),
        internet
      ])
      graphEdges.set([
        edge('gateway-selector', 'gateway', 'selector', 'профиль'),
        edge('selector-main', 'selector', 'main-pool', 'main'),
        edge('main-internet', 'main-pool', 'internet'),
        ...(fallback ? [edge('selector-cdn', 'selector', 'cdn', 'если main недоступны', true), edge('cdn-internet', 'cdn', 'internet', 'CDN', true)] : [])
      ])
    }
    selectedNodeId = ''
    draftChanged = false
  }
  function flowNode(id, title, subtitle, x, y, className, icon = '●', extra = {}) { return { id, type: 'arc', position: { x, y }, data: { title, subtitle, tone: className.split(' ')[0], icon, ...extra }, class: className } }
  function edge(id, source, target, label = '', fallback = false) { return { id, source, target, label, type: 'smoothstep', animated: fallback, class: fallback ? 'fallback' : 'main' } }
  function addBlock(kind, title) {
    addedIndex += 1
    nodes.update((items) => [...items, flowNode(`draft-${kind}-${addedIndex}`, title, 'черновик · настройте связь', 360 + addedIndex * 24, 90 + addedIndex * 42, `${kind} draft`)])
    draftChanged = true
  }
  function connectBlocks(connections) {
    const connection = Array.isArray(connections) ? connections[0] : connections
    if (!connection?.source || !connection?.target || connection.source === connection.target) return
    graphEdges.update((items) => addEdge({ ...connection, id: `draft-edge-${Date.now()}` }, items))
    draftChanged = true
  }
  function validateGraph(nodeItems, edgeItems) {
    const result = []
    const ids = new Set(nodeItems.map((item) => item.id))
    const incoming = new Set(edgeItems.map((item) => item.target))
    const outgoing = new Set(edgeItems.map((item) => item.source))
    for (const item of edgeItems) if (!ids.has(item.source) || !ids.has(item.target)) result.push({ severity: 'critical', title: 'Связь ведёт к отсутствующему блоку', code: 'EDGE_TARGET_MISSING' })
    for (const item of nodeItems.filter((node) => node.id.startsWith('draft-'))) {
      if (!incoming.has(item.id) && !outgoing.has(item.id)) result.push({ severity: 'critical', title: `${item.data?.title || 'Блок'} не подключён`, code: 'BLOCK_ISOLATED' })
    }
    if (!incoming.has('internet')) result.push({ severity: 'critical', title: 'У маршрута нет выхода в Интернет', code: 'EGRESS_MISSING' })
    if (!outgoing.has('gateway')) result.push({ severity: 'critical', title: 'Gateway не подключён к маршруту', code: 'INGRESS_MISSING' })
    if (!result.length) result.push({ severity: 'ok', title: 'Маршрут связен, критических ошибок нет', code: 'DRAFT_VALID' })
    return result
  }
</script>

<section class="page" aria-labelledby="schemes-title">
  <header><div><span>СХЕМЫ ПОДКЛЮЧЕНИЙ</span><h2 id="schemes-title">Лаборатория маршрутов</h2><p>Просмотрите рабочий маршрут или соберите локальный черновик для проверки.</p></div><nav aria-label="Выбор рабочей схемы"><label class="scheme-select"><small>Рабочая схема</small><select value={activeScheme} on:change={switchScheme} disabled={!schemes.length}>{#each schemes as scheme}<option value={scheme.id}>{scheme.name}</option>{/each}</select></label></nav></header>
  <div class="planning-note" role="note"><b>Только локальное планирование</b><span>Редактор не применяет конфигурацию в Remnawave и не меняет подписки. Обновление метрик не сотрёт черновик.</span></div>
  {#if !schemes.length}<div class="empty"><b>Схемы не получены</b><p>Проверьте Remnawave и обновите данные панели.</p></div>{:else}
  <section class="workspace">
    <aside><small>ПАЛИТРА БЛОКОВ</small><p>Добавьте блок, затем соедините его маркеры на холсте. Изменения остаются черновиком.</p>{#each palette as item}<button class={item[1]} on:click={() => addBlock(item[1], item[0])}><i></i>{item[0]}<b>+</b></button>{/each}<footer>Gateway и Интернет — системные блоки, их нельзя удалить.</footer></aside>
    <div class="board">
      <header><b><strong>{$nodes.length}</strong> блоков <i>·</i> <strong>{$graphEdges.length}</strong> связей</b><div><span class:bad={blocked}>{blocked ? 'Черновик не прошёл проверку' : draftChanged ? 'Локальный черновик изменён' : 'Рабочая схема загружена'}</span>{#if pendingGraphKey}<em class="freshness">Метрики обновились</em>{/if}<button on:click={resetDraft} disabled={!draftChanged && !pendingGraphKey}>Сбросить черновик</button></div></header>
      <div class="canvas"><SvelteFlow {nodes} edges={graphEdges} {nodeTypes} fitView minZoom={0.55} maxZoom={1.65} nodesConnectable={true} elementsSelectable={true} onnodeclick={({ node }) => selectedNodeId = node.id} onconnect={connectBlocks} onnodeschange={markNodeChanges} onedgeschange={markEdgeChanges}><Background variant={BackgroundVariant.Dots} gap={20} size={1} /><MiniMap pannable zoomable /><Controls /></SvelteFlow>{#if selectedNode}<aside class="inspector"><header><span>Параметры блока</span><button on:click={() => selectedNodeId = ''} aria-label="Закрыть параметры блока">×</button></header><strong>{selectedNode.data.title}</strong><small>{selectedNode.data.subtitle}</small><dl><div><dt>Тип</dt><dd>{selectedNode.data.tone}</dd></div><div><dt>Вход</dt><dd>{selectedNode.data.entry ? 'Системный' : 'Подключён'}</dd></div><div><dt>Выход</dt><dd>{selectedNode.data.exit ? 'Internet' : 'Маршрут'}</dd></div></dl><p>Это локальный черновик: публикация из этого экрана не выполняется.</p></aside>{/if}</div>
      <section class="findings"><button class="findings-head" on:click={() => findingsOpen = !findingsOpen} aria-expanded={findingsOpen}><i class:good={!blocked}></i><b>Проверка схемы</b><span>{findings.length} {findings.length === 1 ? 'результат' : 'результата'}</span><em>{findingsOpen ? '⌃' : '⌄'}</em></button>{#if findingsOpen}<div class="findings-list">{#each findings as finding}<article class:good={finding.severity === 'ok'}><i>{finding.severity === 'ok' ? '✓' : '×'}</i><span><b>{finding.title}</b><small>{finding.code}</small></span></article>{/each}</div>{/if}</section>
    </div>
  </section>
  {/if}
</section>

<style>
.page{display:grid;gap:22px}.page>header{display:flex;align-items:end;justify-content:space-between;gap:30px}.page>header span,aside>small{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.14em}h2{margin:7px 0 5px;font-size:30px}p{margin:0;color:#7890a5}.page>header nav{display:flex;max-width:54%;gap:6px;overflow:auto}.page>header nav button{padding:9px 12px;border:1px solid #1c2a38;border-radius:12px;background:#0c131d;color:#7890a5;white-space:nowrap}.page>header nav button.active{border-color:#37617f;background:#14283a;color:#bde7ff}.workspace{display:grid;grid-template-columns:190px minmax(0,1fr);min-height:650px;overflow:hidden;border:1px solid #1d2b39;border-radius:24px;background:#08111a}.workspace>aside{display:flex;flex-direction:column;gap:7px;padding:18px 12px;border-right:1px solid #1d2b39;background:#0d1621}.workspace>aside p{margin:4px 2px 8px;font-size:10px;line-height:1.45}.workspace>aside button{display:flex;align-items:center;gap:9px;min-height:42px;padding:0 10px;border:1px solid #213140;border-radius:11px;background:#111d29;color:#b4c5d2;text-align:left;cursor:pointer}.workspace>aside button>b{margin-left:auto;color:#688297}.workspace>aside button>i{width:10px;height:10px;border-radius:3px;background:#55d5ac}.workspace>aside .transit>i{background:#4bb7ef}.workspace>aside .cdn>i{background:#ef9b4b}.workspace>aside .warp>i{background:#9d7bea}.workspace>aside .proxy>i{background:#d66bd1}.workspace>aside .block>i{background:#7b8792}.workspace>aside footer{margin-top:auto;color:#607486;font-size:9px;line-height:1.45}.board{display:grid;grid-template-rows:45px 545px auto;min-width:0}.board>header{display:flex;align-items:center;justify-content:space-between;padding:0 16px;border-bottom:1px solid #1d2b39}.board>header>b{font-size:10px}.board>header>b strong{font-size:12px}.board>header b i{color:#557087;font-style:normal}.board>header>div{display:flex;align-items:center;gap:8px}.board>header span{padding:6px 9px;border-radius:9px;background:#123126;color:#78deb0;font-size:9px}.board>header span.bad{background:#352026;color:#ff9da7}.board>header button{border:1px solid #253746;border-radius:9px;padding:6px 10px;background:#101b27;color:#9db2c4;font-size:9px;cursor:pointer}.board>header button:disabled{opacity:.35}.canvas{height:545px;background:#08111a}.findings{border-top:1px solid #1d2b39;background:#0b141e}.findings-head{box-sizing:border-box;width:100%;min-height:48px;display:grid;grid-template-columns:10px auto 1fr auto;align-items:center;gap:9px;padding:0 16px;border:0;background:transparent;color:#d8e5ee;text-align:left;cursor:pointer}.findings-head>i{width:8px;height:8px;border-radius:50%;background:#ff7474}.findings-head>i.good{background:#61d8a5}.findings-head span{color:#6f8497;font-size:9px}.findings-head em{font-style:normal}.findings-list{display:grid;gap:7px;padding:0 14px 13px}.findings-list article{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #4d2930;border-radius:11px;background:#20151b}.findings-list article>i{display:grid;width:22px;height:22px;place-items:center;border-radius:50%;background:#47222b;color:#ff9ca6;font-style:normal;font-weight:900}.findings-list article>span{display:grid}.findings-list article small{color:#8a6870;font-family:monospace;font-size:8px}.findings-list article.good{border-color:#21483b;background:#10231d}.findings-list article.good>i{background:#183c30;color:#72d9ad}.findings-list article.good small{color:#5f8d7b}
:global(.svelte-flow){--xy-background-color:#08111a;--xy-node-border:1px solid #2c4152;--xy-node-border-radius:13px;--xy-node-background-color:#111c28;--xy-node-color:#dbe9f3;--xy-edge-stroke:#29b8a9;--xy-edge-stroke-width:2;--xy-controls-button-background-color:#111d29;--xy-controls-button-color:#bde7ff;--xy-controls-button-border-color:#26394a;--xy-minimap-background-color:#0d1621}:global(.svelte-flow__node){width:190px;min-height:64px;padding:13px 14px;text-align:left;white-space:pre-line;line-height:1.45;box-shadow:0 12px 30px #0006;font-size:11px;font-weight:800}:global(.svelte-flow__node.gateway){border-color:#70466f}:global(.svelte-flow__node.selector){border-color:#2a826d}:global(.svelte-flow__node.cdn){border-color:#6d5aaa}:global(.svelte-flow__node.internet){border-color:#327693}:global(.svelte-flow__node.offline){border-color:#7f3f48;color:#ffafb7}:global(.svelte-flow__edge.fallback path){stroke:#9d7bea;stroke-dasharray:8 6}:global(.svelte-flow__edge-text){fill:#89a0b3;font-size:9px}:global(.svelte-flow__edge-textbg){fill:#0d1621}:global(.svelte-flow__minimap){border:1px solid #26394a;border-radius:12px;overflow:hidden}:global(.svelte-flow__controls){border:1px solid #26394a;border-radius:10px;overflow:hidden}
@media(max-width:1000px){.page>header{align-items:stretch;flex-direction:column}.page>header nav{max-width:100%}.workspace{grid-template-columns:1fr}.workspace>aside{display:none}}@media(max-width:700px){.workspace{min-height:560px}.canvas{height:455px}.page>header h2{font-size:25px}}
.page{gap:18px}.page>header{align-items:center}.page>header h2{font-size:27px;letter-spacing:-.035em}.page>header p{font-size:12px}.scheme-select{display:grid;min-width:270px;gap:6px}.scheme-select small{color:#6d8498;font-size:9px;text-transform:uppercase;letter-spacing:.12em}.scheme-select select{height:42px;border:1px solid #253746;border-radius:11px;padding:0 36px 0 13px;background:#0d1824;color:#dcebf5;font:700 12px inherit;outline:none}.workspace{grid-template-columns:178px minmax(0,1fr);min-height:614px;border-radius:20px}.workspace>aside{padding:16px 11px}.workspace>aside button{min-height:39px;border-radius:9px}.board{grid-template-rows:43px 500px auto}.canvas{position:relative;height:500px}.inspector{position:absolute;z-index:8;top:14px;right:14px;box-sizing:border-box;width:225px;padding:15px;border:1px solid #2c4052;border-radius:15px;background:#0c1723eF;box-shadow:0 18px 45px #0008}.inspector header{display:flex;align-items:center;justify-content:space-between}.inspector header span{color:#6f879a;font-size:9px;text-transform:uppercase;letter-spacing:.1em}.inspector header button{border:0;background:transparent;color:#91a7b9;font-size:20px;cursor:pointer}.inspector>strong{display:block;margin-top:12px}.inspector>small,.inspector p{color:#7890a5;font-size:9px}.inspector dl{display:grid;gap:7px;margin:14px 0}.inspector dl div{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #1d2d3b}.inspector dt{color:#6e8497;font-size:9px}.inspector dd{margin:0;color:#c3d5e2;font:9px 'JetBrains Mono',monospace}:global(.svelte-flow__node-arc){width:auto!important;min-height:0!important;padding:0!important;border:0!important;background:transparent!important;box-shadow:none!important}:global(.svelte-flow__edge path){stroke:#2eaa9e;stroke-width:1.6}:global(.svelte-flow__edge.fallback path){stroke:#8c74cf;stroke-dasharray:7 6}:global(.svelte-flow__edge-text){font-size:8px}:global(.svelte-flow__minimap){width:145px!important;height:92px!important}:global(.svelte-flow__attribution){font-size:7px;opacity:.35}
@media(max-width:1000px){.scheme-select{min-width:0}.workspace{grid-template-columns:1fr}.workspace>aside{display:none}.board{grid-template-rows:43px 480px auto}.canvas{height:480px}}
.planning-note{display:flex;align-items:center;gap:12px;padding:12px 15px;border:1px solid #294359;border-radius:14px;background:#101c28;color:#8da5b8;font-size:11px}.planning-note b{color:#bde7ff;white-space:nowrap}.empty{padding:32px;border:1px dashed #26394a;border-radius:20px;text-align:center}.empty b{display:block;margin-bottom:7px}.freshness{color:#e8b957;font-size:9px;font-style:normal}.page,.workspace,.board{min-width:0}:global(button:focus-visible),.scheme-select select:focus-visible{outline:2px solid #9bd9ff;outline-offset:2px}@media(max-width:700px){.planning-note{align-items:flex-start;flex-direction:column}.board>header>div{gap:4px}.freshness{display:none}}
</style>
