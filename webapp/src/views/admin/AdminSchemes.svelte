<script>
  import { writable } from 'svelte/store'
  import { SvelteFlow, Background, BackgroundVariant, Controls, MiniMap, addEdge } from '@xyflow/svelte'
  import '@xyflow/svelte/dist/style.css'

  export let data
  const nodes = writable([])
  const graphEdges = writable([])
  let activeScheme = 'auto'
  let draftChanged = false
  let findingsOpen = true
  let addedIndex = 0

  $: schemes = data?.remnawave?.connection_schemes || []
  $: mainNodes = (data?.remnawave?.nodes || []).filter((node) => !node.disabled).slice(0, 4)
  $: lteEdges = data?.remnawave?.lte_edges || []
  $: if (schemes.length && !schemes.some((scheme) => scheme.id === activeScheme)) activeScheme = schemes[0].id
  $: graphKey = JSON.stringify({ activeScheme, main: mainNodes.map((node) => [node.uuid || node.id, node.name, node.connected, node.users_online]), edges: lteEdges.map((item) => [item.id, item.country_code]) })
  $: rebuildGraph(graphKey)
  $: findings = validateGraph($nodes, $graphEdges)
  $: blocked = findings.some((item) => item.severity === 'critical')

  const palette = [['Входная нода','in'],['Транзитная нода','transit'],['CDN','cdn'],['WARP','warp'],['Внешний прокси','proxy'],['Blackhole','block']]

  function rebuildGraph() {
    const items = mainNodes.length ? mainNodes : [{ name: 'Нет доступных main-нод', connected: false }]
    nodes.set([
      flowNode('gateway', 'Gateway', 'Клиентский вход', 25, 190, 'gateway'),
      flowNode('selector', 'Автовыбор', 'leastLoad · main only', 270, 190, 'selector'),
      ...items.map((node, index) => flowNode(`main-${index}`, node.name, `${node.users_online || 0} онлайн · ${node.connected ? 'доступна' : 'нет связи'}`, 555, 38 + index * 105, node.connected ? 'node' : 'node offline')),
      flowNode('cdn', 'Скрытый CDN fallback', lteEdges.map((item) => item.country_code).filter(Boolean).join(' + ') || 'DE + NL', 555, 470, 'cdn'),
      flowNode('internet', 'Интернет', 'Итоговый egress', 845, 190, 'internet')
    ])
    graphEdges.set([
      edge('gateway-selector', 'gateway', 'selector', 'профиль'),
      ...items.map((_, index) => edge(`selector-main-${index}`, 'selector', `main-${index}`, 'main')),
      ...items.map((_, index) => edge(`main-${index}-internet`, `main-${index}`, 'internet')),
      edge('selector-cdn', 'selector', 'cdn', 'только полный отказ', true),
      edge('cdn-internet', 'cdn', 'internet', 'CDN', true)
    ])
    draftChanged = false
  }
  function flowNode(id, title, subtitle, x, y, className) { return { id, position: { x, y }, data: { label: `${title}\n${subtitle}` }, class: className } }
  function edge(id, source, target, label = '', fallback = false) { return { id, source, target, label, animated: fallback, class: fallback ? 'fallback' : 'main' } }
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
      if (!incoming.has(item.id) && !outgoing.has(item.id)) result.push({ severity: 'critical', title: `${String(item.data?.label || '').split('\n')[0]} не подключён`, code: 'BLOCK_ISOLATED' })
    }
    if (!incoming.has('internet')) result.push({ severity: 'critical', title: 'У маршрута нет выхода в Интернет', code: 'EGRESS_MISSING' })
    if (!outgoing.has('gateway')) result.push({ severity: 'critical', title: 'Gateway не подключён к маршруту', code: 'INGRESS_MISSING' })
    if (!result.length) result.push({ severity: 'ok', title: 'Маршрут связен, критических ошибок нет', code: 'DRAFT_VALID' })
    return result
  }
</script>

<section class="page">
  <header><div><span>СХЕМЫ ПОДКЛЮЧЕНИЙ</span><h2>Маршрут без догадок</h2><p>Перетаскивайте блоки, масштабируйте схему и проверяйте реальный fallback.</p></div><nav>{#each schemes as scheme}<button class:active={activeScheme === scheme.id} on:click={() => activeScheme = scheme.id}>{scheme.name.replace(/^\S+\s/, '')}</button>{/each}</nav></header>
  <section class="workspace">
    <aside><small>ПАЛИТРА БЛОКОВ</small><p>Добавьте блок, затем соедините его маркеры на холсте. Изменения остаются черновиком.</p>{#each palette as item}<button class={item[1]} on:click={() => addBlock(item[1], item[0])}><i></i>{item[0]}<b>+</b></button>{/each}<footer>Gateway и Интернет — системные блоки, их нельзя удалить.</footer></aside>
    <div class="board">
      <header><b><strong>{$nodes.length}</strong> блоков <i>·</i> <strong>{$graphEdges.length}</strong> связей</b><div><span class:bad={blocked}>{blocked ? 'Применение заблокировано' : draftChanged ? 'Черновик изменён' : 'Схема готова'}</span><button on:click={() => rebuildGraph(graphKey)} disabled={!draftChanged}>Сбросить</button></div></header>
      <div class="canvas"><SvelteFlow {nodes} edges={graphEdges} fitView minZoom={0.45} maxZoom={1.8} nodesConnectable={true} elementsSelectable={true} onconnect={connectBlocks} onnodeschange={() => draftChanged = true} onedgeschange={() => draftChanged = true}><Background variant={BackgroundVariant.Dots} gap={18} size={1} /><MiniMap pannable zoomable /><Controls /></SvelteFlow></div>
      <section class="findings"><button class="findings-head" on:click={() => findingsOpen = !findingsOpen} aria-expanded={findingsOpen}><i class:good={!blocked}></i><b>Проверка схемы</b><span>{findings.length} {findings.length === 1 ? 'результат' : 'результата'}</span><em>{findingsOpen ? '⌃' : '⌄'}</em></button>{#if findingsOpen}<div class="findings-list">{#each findings as finding}<article class:good={finding.severity === 'ok'}><i>{finding.severity === 'ok' ? '✓' : '×'}</i><span><b>{finding.title}</b><small>{finding.code}</small></span></article>{/each}</div>{/if}</section>
    </div>
  </section>
</section>

<style>
.page{display:grid;gap:22px}.page>header{display:flex;align-items:end;justify-content:space-between;gap:30px}.page>header span,aside>small{color:#80c9f4;font-size:10px;font-weight:900;letter-spacing:.14em}h2{margin:7px 0 5px;font-size:30px}p{margin:0;color:#7890a5}.page>header nav{display:flex;max-width:54%;gap:6px;overflow:auto}.page>header nav button{padding:9px 12px;border:1px solid #1c2a38;border-radius:12px;background:#0c131d;color:#7890a5;white-space:nowrap}.page>header nav button.active{border-color:#37617f;background:#14283a;color:#bde7ff}.workspace{display:grid;grid-template-columns:190px minmax(0,1fr);min-height:650px;overflow:hidden;border:1px solid #1d2b39;border-radius:24px;background:#08111a}.workspace>aside{display:flex;flex-direction:column;gap:7px;padding:18px 12px;border-right:1px solid #1d2b39;background:#0d1621}.workspace>aside p{margin:4px 2px 8px;font-size:10px;line-height:1.45}.workspace>aside button{display:flex;align-items:center;gap:9px;min-height:42px;padding:0 10px;border:1px solid #213140;border-radius:11px;background:#111d29;color:#b4c5d2;text-align:left;cursor:pointer}.workspace>aside button>b{margin-left:auto;color:#688297}.workspace>aside button>i{width:10px;height:10px;border-radius:3px;background:#55d5ac}.workspace>aside .transit>i{background:#4bb7ef}.workspace>aside .cdn>i{background:#ef9b4b}.workspace>aside .warp>i{background:#9d7bea}.workspace>aside .proxy>i{background:#d66bd1}.workspace>aside .block>i{background:#7b8792}.workspace>aside footer{margin-top:auto;color:#607486;font-size:9px;line-height:1.45}.board{display:grid;grid-template-rows:45px 545px auto;min-width:0}.board>header{display:flex;align-items:center;justify-content:space-between;padding:0 16px;border-bottom:1px solid #1d2b39}.board>header>b{font-size:10px}.board>header>b strong{font-size:12px}.board>header b i{color:#557087;font-style:normal}.board>header>div{display:flex;align-items:center;gap:8px}.board>header span{padding:6px 9px;border-radius:9px;background:#123126;color:#78deb0;font-size:9px}.board>header span.bad{background:#352026;color:#ff9da7}.board>header button{border:1px solid #253746;border-radius:9px;padding:6px 10px;background:#101b27;color:#9db2c4;font-size:9px;cursor:pointer}.board>header button:disabled{opacity:.35}.canvas{height:545px;background:#08111a}.findings{border-top:1px solid #1d2b39;background:#0b141e}.findings-head{box-sizing:border-box;width:100%;min-height:48px;display:grid;grid-template-columns:10px auto 1fr auto;align-items:center;gap:9px;padding:0 16px;border:0;background:transparent;color:#d8e5ee;text-align:left;cursor:pointer}.findings-head>i{width:8px;height:8px;border-radius:50%;background:#ff7474}.findings-head>i.good{background:#61d8a5}.findings-head span{color:#6f8497;font-size:9px}.findings-head em{font-style:normal}.findings-list{display:grid;gap:7px;padding:0 14px 13px}.findings-list article{display:flex;align-items:center;gap:10px;padding:10px 12px;border:1px solid #4d2930;border-radius:11px;background:#20151b}.findings-list article>i{display:grid;width:22px;height:22px;place-items:center;border-radius:50%;background:#47222b;color:#ff9ca6;font-style:normal;font-weight:900}.findings-list article>span{display:grid}.findings-list article small{color:#8a6870;font-family:monospace;font-size:8px}.findings-list article.good{border-color:#21483b;background:#10231d}.findings-list article.good>i{background:#183c30;color:#72d9ad}.findings-list article.good small{color:#5f8d7b}
:global(.svelte-flow){--xy-background-color:#08111a;--xy-node-border:1px solid #2c4152;--xy-node-border-radius:13px;--xy-node-background-color:#111c28;--xy-node-color:#dbe9f3;--xy-edge-stroke:#29b8a9;--xy-edge-stroke-width:2;--xy-controls-button-background-color:#111d29;--xy-controls-button-color:#bde7ff;--xy-controls-button-border-color:#26394a;--xy-minimap-background-color:#0d1621}:global(.svelte-flow__node){width:190px;min-height:64px;padding:13px 14px;text-align:left;white-space:pre-line;line-height:1.45;box-shadow:0 12px 30px #0006;font-size:11px;font-weight:800}:global(.svelte-flow__node.gateway){border-color:#70466f}:global(.svelte-flow__node.selector){border-color:#2a826d}:global(.svelte-flow__node.cdn){border-color:#6d5aaa}:global(.svelte-flow__node.internet){border-color:#327693}:global(.svelte-flow__node.offline){border-color:#7f3f48;color:#ffafb7}:global(.svelte-flow__edge.fallback path){stroke:#9d7bea;stroke-dasharray:8 6}:global(.svelte-flow__edge-text){fill:#89a0b3;font-size:9px}:global(.svelte-flow__edge-textbg){fill:#0d1621}:global(.svelte-flow__minimap){border:1px solid #26394a;border-radius:12px;overflow:hidden}:global(.svelte-flow__controls){border:1px solid #26394a;border-radius:10px;overflow:hidden}
@media(max-width:1000px){.page>header{align-items:stretch;flex-direction:column}.page>header nav{max-width:100%}.workspace{grid-template-columns:1fr}.workspace>aside{display:none}}@media(max-width:700px){.workspace{min-height:560px}.canvas{height:455px}.page>header h2{font-size:25px}}
</style>
