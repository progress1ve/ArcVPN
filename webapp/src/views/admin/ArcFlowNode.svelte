<script>
  import { Handle, Position } from '@xyflow/svelte'
  export let data = {}
</script>

<div class="unit" class:offline={data.offline} data-tone={data.tone || 'node'}>
  {#if !data.entry}<Handle type="target" position={Position.Left} />{/if}
  <span class="glyph">{data.icon || '●'}</span>
  <span class="copy"><strong>{data.title}</strong><small>{data.subtitle}</small></span>
  {#if data.badge}<em>{data.badge}</em>{/if}
  {#if !data.exit}<Handle type="source" position={Position.Right} />{/if}
</div>

<style>
  .unit{box-sizing:border-box;width:202px;min-height:64px;display:flex;align-items:center;gap:11px;padding:10px 13px;border:1px solid #294258;border-radius:13px;background:#101c28;color:#e5f0f8;box-shadow:0 12px 28px #0005}.glyph{display:grid;flex:0 0 34px;height:34px;place-items:center;border:1px solid #28516a;border-radius:10px;background:#102d40;color:#8ed8ff;font-size:15px}.copy{display:flex;min-width:0;flex:1;flex-direction:column;gap:3px}.copy strong,.copy small{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.copy strong{font-size:11px}.copy small{color:#7791a5;font:9px 'JetBrains Mono',monospace}.unit em{padding:4px 6px;border-radius:7px;background:#153328;color:#77d8ac;font-size:7px;font-style:normal;font-weight:900;text-transform:uppercase}.unit[data-tone='gateway']{border-color:#654e68}.unit[data-tone='gateway'] .glyph{border-color:#59435f;background:#251d30;color:#d0aff2}.unit[data-tone='selector']{border-color:#347365}.unit[data-tone='selector'] .glyph{border-color:#2e665b;background:#102e29;color:#78dab8}.unit[data-tone='cdn']{border-color:#67558d}.unit[data-tone='cdn'] .glyph{border-color:#594779;background:#251d3a;color:#bca4ff}.unit[data-tone='warp']{border-color:#554b86}.unit[data-tone='internet']{border-color:#346a85}.unit.offline{border-color:#76414a;color:#ffb0b8}.unit.offline em{background:#3a2026;color:#ff9da7}:global(.svelte-flow__handle){width:8px;height:8px;border:2px solid #07111a;background:#8ed8ff}:global(.svelte-flow__handle-left){left:-5px}:global(.svelte-flow__handle-right){right:-5px}
</style>
