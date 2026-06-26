/**
 * graph.js — AFI Knowledge Graph
 * D3 force-directed graph showing relationships between publications.
 *
 * Node types: AFI, DAFI, AFMAN, AFPD, DoDI (external), stub (gap)
 * Edge types: implements, references, supersedes
 */

(function () {
  const GRAPH_DATA_URL = document.currentScript
    ? new URL('graph.json', document.currentScript.src).href
    : 'javascripts/graph.json';

  // ---------------------------------------------------------------------------
  // Config
  // ---------------------------------------------------------------------------
  const CFG = {
    width:        800,
    height:       600,
    nodeMinR:     5,
    nodeMaxR:     14,
    chargeStr:   -220,
    linkDistance: 80,
    linkStrength: 0.4,
  };

  const EDGE_COLORS = {
    implements:  '#C8A951',  // gold
    references:  '#5B9BD5',  // light blue
    supersedes:  '#A8B2C1',  // silver
  };

  const EDGE_DASH = {
    implements:  'none',
    references:  '4,3',
    supersedes:  '2,4',
  };

  // ---------------------------------------------------------------------------
  // Init
  // ---------------------------------------------------------------------------
  document.addEventListener('DOMContentLoaded', init);

  function init() {
    const container = document.getElementById('graph-container');
    if (!container) return;

    container.innerHTML = '<p style="color:var(--md-default-fg-color--light);padding:2rem">Loading graph...</p>';

    fetch(GRAPH_DATA_URL)
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(data => renderGraph(container, data))
      .catch(err => {
        container.innerHTML = `<p style="color:#C8102E;padding:2rem">Could not load graph data: ${err.message}</p>`;
      });
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  function renderGraph(container, data) {
    container.innerHTML = '';

    const W = container.clientWidth || CFG.width;
    const H = CFG.height;

    // Controls bar
    const controls = document.createElement('div');
    controls.style.cssText = 'display:flex;gap:12px;flex-wrap:wrap;padding:8px 0 12px;align-items:center;font-size:0.78rem;';
    controls.innerHTML = buildControls(data);
    container.appendChild(controls);

    // SVG
    const svg = d3.select(container)
      .append('svg')
      .attr('width', '100%')
      .attr('viewBox', `0 0 ${W} ${H}`)
      .style('background', 'rgba(0,0,0,0.15)')
      .style('border-radius', '6px');

    // Defs: arrowheads
    const defs = svg.append('defs');
    Object.entries(EDGE_COLORS).forEach(([type, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${type}`)
        .attr('viewBox', '0 -4 8 8')
        .attr('refX', 18)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-4L8,0L0,4')
        .attr('fill', color)
        .attr('opacity', 0.7);
    });

    const g = svg.append('g');

    // Zoom
    svg.call(d3.zoom()
      .scaleExtent([0.3, 4])
      .on('zoom', e => g.attr('transform', e.transform))
    );

    // Simulation
    const sim = d3.forceSimulation(data.nodes)
      .force('link', d3.forceLink(data.edges)
        .id(d => d.id)
        .distance(CFG.linkDistance)
        .strength(CFG.linkStrength)
      )
      .force('charge', d3.forceManyBody().strength(CFG.chargeStr))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('collision', d3.forceCollide().radius(d => nodeR(d) + 4));

    // Edges
    const link = g.append('g')
      .selectAll('line')
      .data(data.edges)
      .join('line')
      .attr('stroke', d => EDGE_COLORS[d.type] || '#666')
      .attr('stroke-width', 1.2)
      .attr('stroke-dasharray', d => EDGE_DASH[d.type] || 'none')
      .attr('marker-end', d => `url(#arrow-${d.type})`)
      .attr('opacity', 0.6);

    // Nodes
    const node = g.append('g')
      .selectAll('g')
      .data(data.nodes)
      .join('g')
      .attr('cursor', d => d.url ? 'pointer' : 'default')
      .call(d3.drag()
        .on('start', dragStart)
        .on('drag',  dragging)
        .on('end',   dragEnd)
      )
      .on('click', (event, d) => {
        if (d.url) window.location.href = d.url;
      })
      .on('mouseover', (event, d) => highlight(d, link, node, true))
      .on('mouseout',  ()         => highlight(null, link, node, false));

    // Node circles
    node.append('circle')
      .attr('r', d => nodeR(d))
      .attr('fill', d => d.stub ? 'transparent' : d.color)
      .attr('stroke', d => d.stub ? '#C8102E' : d.color)
      .attr('stroke-width', d => d.stub ? 2 : 1)
      .attr('stroke-dasharray', d => d.stub ? '3,2' : 'none')
      .attr('opacity', d => d.external ? 0.55 : 0.9);

    // Node labels
    node.append('text')
      .text(d => shortLabel(d.id))
      .attr('dx', d => nodeR(d) + 3)
      .attr('dy', '0.35em')
      .attr('font-size', '9px')
      .attr('fill', 'var(--md-default-fg-color)')
      .attr('opacity', 0.8)
      .attr('pointer-events', 'none');

    // Tooltip
    const tooltip = d3.select(container)
      .append('div')
      .style('position', 'absolute')
      .style('background', 'rgba(0,30,60,0.95)')
      .style('color', 'white')
      .style('padding', '8px 12px')
      .style('border-radius', '4px')
      .style('font-size', '12px')
      .style('pointer-events', 'none')
      .style('display', 'none')
      .style('max-width', '260px')
      .style('border', '1px solid rgba(200,169,81,0.4)');

    node
      .on('mouseover.tip', (event, d) => {
        tooltip
          .style('display', 'block')
          .html(tooltipHTML(d));
      })
      .on('mousemove.tip', event => {
        const rect = container.getBoundingClientRect();
        tooltip
          .style('left', (event.clientX - rect.left + 12) + 'px')
          .style('top',  (event.clientY - rect.top  - 10) + 'px');
      })
      .on('mouseout.tip', () => tooltip.style('display', 'none'));

    // Simulation tick
    sim.on('tick', () => {
      link
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y);
      node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Filter controls wiring
    container.addEventListener('change', e => {
      const seriesFilter = container.querySelector('#filter-series');
      const typeFilter   = container.querySelector('#filter-type');
      const series = seriesFilter ? seriesFilter.value : 'all';
      const type   = typeFilter   ? typeFilter.value   : 'all';
      applyFilter(node, link, series, type);
    });

    // Legend
    const legend = document.createElement('div');
    legend.style.cssText = 'display:flex;gap:16px;flex-wrap:wrap;padding:8px 0;font-size:0.75rem;opacity:0.8;';
    legend.innerHTML = buildLegend();
    container.appendChild(legend);
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  function nodeR(d) {
    const base = d.external ? CFG.nodeMinR : CFG.nodeMaxR;
    return d.stub ? base * 0.8 : base;
  }

  function shortLabel(id) {
    // "AFI 36-2406" → "36-2406"
    return id.replace(/^(?:DAFI|AFI|AFMAN|DAFMAN|AFH|AFPD|DAFPD|AFGM)\s*/i, '');
  }

  function tooltipHTML(d) {
    const status = d.stub
      ? `<span style="color:#C8102E">⚠ Coverage Gap (${d.doc_type})</span>`
      : d.external
        ? '<span style="color:#A8B2C1">External directive</span>'
        : '<span style="color:#4CAF50">✓ In corpus</span>';
    return `
      <strong>${d.id}</strong><br>
      ${d.title !== d.id ? `<span style="opacity:0.8">${d.title.slice(0, 60)}${d.title.length > 60 ? '…' : ''}</span><br>` : ''}
      ${d.opr ? `OPR: ${d.opr}<br>` : ''}
      ${status}
      ${d.url ? '<br><span style="color:#C8A951;font-size:10px">Click to open wiki page →</span>' : ''}
    `;
  }

  function highlight(d, link, node, on) {
    if (!on || !d) {
      link.attr('opacity', 0.6);
      node.attr('opacity', 1);
      return;
    }
    const connected = new Set([d.id]);
    link.each(function(e) {
      if (e.source.id === d.id || e.target.id === d.id) {
        connected.add(e.source.id);
        connected.add(e.target.id);
      }
    });
    link.attr('opacity', e =>
      (e.source.id === d.id || e.target.id === d.id) ? 1 : 0.05
    );
    node.attr('opacity', n => connected.has(n.id) ? 1 : 0.15);
  }

  function applyFilter(node, link, series, type) {
    node.attr('display', d => {
      if (series !== 'all' && d.series !== series && !d.external) return 'none';
      if (type !== 'all' && d.type !== type) return 'none';
      return null;
    });
    link.attr('display', 'null');
  }

  function buildControls(data) {
    const seriesOptions = [...new Set(data.nodes
      .filter(n => !n.external)
      .map(n => n.series)
    )].sort();

    const seriesHtml = seriesOptions.map(s =>
      `<option value="${s}">${s}-series</option>`
    ).join('');

    return `
      <label style="color:var(--md-default-fg-color--light)">Filter series:
        <select id="filter-series" style="margin-left:4px;background:rgba(0,63,135,0.3);color:white;border:1px solid rgba(168,178,193,0.3);border-radius:3px;padding:2px 6px;">
          <option value="all">All series</option>
          ${seriesHtml}
        </select>
      </label>
      <label style="color:var(--md-default-fg-color--light)">Type:
        <select id="filter-type" style="margin-left:4px;background:rgba(0,63,135,0.3);color:white;border:1px solid rgba(168,178,193,0.3);border-radius:3px;padding:2px 6px;">
          <option value="all">All types</option>
          <option value="AFI">AFI</option>
          <option value="DAFI">DAFI</option>
          <option value="AFMAN">AFMAN</option>
          <option value="AFPD">AFPD</option>
          <option value="DoDI">DoDI</option>
        </select>
      </label>
      <span style="color:var(--md-default-fg-color--light);margin-left:auto;font-size:0.72rem">
        Scroll to zoom · drag to pan · click node to open
      </span>
    `;
  }

  function buildLegend() {
    const edges = Object.entries(EDGE_COLORS).map(([type, color]) => `
      <span style="display:flex;align-items:center;gap:4px">
        <svg width="24" height="10"><line x1="0" y1="5" x2="24" y2="5"
          stroke="${color}" stroke-width="2"
          stroke-dasharray="${EDGE_DASH[type]}"/></svg>
        ${type}
      </span>
    `).join('');

    return `
      <span style="color:var(--md-default-fg-color--light);font-weight:600">Edges:</span>
      ${edges}
      <span style="display:flex;align-items:center;gap:4px;margin-left:8px">
        <svg width="14" height="14"><circle cx="7" cy="7" r="6"
          fill="transparent" stroke="#C8102E" stroke-width="2"
          stroke-dasharray="3,2"/></svg>
        coverage gap
      </span>
      <span style="display:flex;align-items:center;gap:4px">
        <svg width="14" height="14"><circle cx="7" cy="7" r="5"
          fill="#A8B2C1" opacity="0.5"/></svg>
        external directive
      </span>
    `;
  }

  // Drag handlers
  function dragStart(event, d) {
    if (!event.active) event.sourceEvent.target.__sim && event.sourceEvent.target.__sim.alphaTarget(0.3).restart();
    d.fx = d.x;
    d.fy = d.y;
  }
  function dragging(event, d) { d.fx = event.x; d.fy = event.y; }
  function dragEnd(event, d) {
    if (!event.active) event.sourceEvent.target.__sim && event.sourceEvent.target.__sim.alphaTarget(0);
    d.fx = null;
    d.fy = null;
  }
})();
