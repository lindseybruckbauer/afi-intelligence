document.addEventListener('DOMContentLoaded', function() {
  const container = document.getElementById('graph-container');
  if (!container) return;

  const colors = {
    entity: '#5c6bc0',
    concept: '#26a69a',
    source: '#ef5350',
    other: '#78909c'
  };

  const width = container.clientWidth || 700;
  const height = container.clientHeight || 600;

  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('width', '100%');
  svg.setAttribute('height', '100%');
  svg.setAttribute('viewBox', `0 0 ${width} ${height}`);
  container.appendChild(svg);

  const tooltip = document.createElement('div');
  tooltip.style.cssText = 'position:absolute;background:rgba(0,0,0,0.8);color:white;padding:6px 10px;border-radius:4px;font-size:12px;pointer-events:none;opacity:0;transition:opacity 0.2s;max-width:200px;z-index:100';
  container.appendChild(tooltip);

  // resolve base URL from the script tag itself
  const base = window.location.origin + '/team-wiki';
  const jsonUrl = base + '/javascripts/graph.json';

  fetch(jsonUrl)
    .then(r => r.json())
    .then(data => renderGraph(data))
    .catch(err => {
      console.error('graph.json fetch failed:', jsonUrl, err);
    });

  function renderGraph(data) {
    const nodes = data.nodes.map(n => ({...n}));
    const edges = data.edges.map(e => ({...e}));

    const degree = {};
    nodes.forEach(n => degree[n.id] = 0);
    edges.forEach(e => {
      degree[e.source] = (degree[e.source] || 0) + 1;
      degree[e.target] = (degree[e.target] || 0) + 1;
    });

    nodes.forEach((n, i) => {
      const angle = (i / nodes.length) * 2 * Math.PI;
      const radius = Math.min(width, height) * 0.35;
      n.x = width/2 + radius * Math.cos(angle);
      n.y = height/2 + radius * Math.sin(angle);
      n.vx = 0;
      n.vy = 0;
    });

    const nodeMap = {};
    nodes.forEach(n => nodeMap[n.id] = n);

    for (let iter = 0; iter < 300; iter++) {
      for (let i = 0; i < nodes.length; i++) {
        for (let j = i+1; j < nodes.length; j++) {
          const a = nodes[i], b = nodes[j];
          const dx = b.x - a.x;
          const dy = b.y - a.y;
          const dist = Math.sqrt(dx*dx + dy*dy) || 1;
          const force = 4000 / (dist * dist);
          a.vx -= force * dx/dist;
          a.vy -= force * dy/dist;
          b.vx += force * dx/dist;
          b.vy += force * dy/dist;
        }
      }
      edges.forEach(e => {
        const a = nodeMap[e.source];
        const b = nodeMap[e.target];
        if (!a || !b) return;
        const dx = b.x - a.x;
        const dy = b.y - a.y;
        const dist = Math.sqrt(dx*dx + dy*dy) || 1;
        const force = (dist - 120) * 0.02;
        a.vx += force * dx/dist;
        a.vy += force * dy/dist;
        b.vx -= force * dx/dist;
        b.vy -= force * dy/dist;
      });
      nodes.forEach(n => {
        n.vx *= 0.8;
        n.vy *= 0.8;
        n.x = Math.max(40, Math.min(width-40, n.x + n.vx));
        n.y = Math.max(40, Math.min(height-40, n.y + n.vy));
      });
    }

    edges.forEach(e => {
      const a = nodeMap[e.source];
      const b = nodeMap[e.target];
      if (!a || !b) return;
      const line = document.createElementNS('http://www.w3.org/2000/svg', 'line');
      line.setAttribute('x1', a.x);
      line.setAttribute('y1', a.y);
      line.setAttribute('x2', b.x);
      line.setAttribute('y2', b.y);
      line.setAttribute('stroke', 'rgba(255,255,255,0.15)');
      line.setAttribute('stroke-width', '1');
      svg.appendChild(line);
    });

    nodes.forEach(n => {
      const r = 6 + Math.min(degree[n.id] * 1.5, 14);
      const color = colors[n.type] || colors.other;

      const circle = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      circle.setAttribute('cx', n.x);
      circle.setAttribute('cy', n.y);
      circle.setAttribute('r', r);
      circle.setAttribute('fill', color);
      circle.setAttribute('stroke', 'rgba(255,255,255,0.3)');
      circle.setAttribute('stroke-width', '1.5');
      circle.style.cursor = 'pointer';

      circle.addEventListener('mouseenter', (ev) => {
        tooltip.style.opacity = '1';
        tooltip.innerText = `${n.id} (${n.type})`;
        tooltip.style.left = (ev.offsetX + 12) + 'px';
        tooltip.style.top = (ev.offsetY - 10) + 'px';
        circle.setAttribute('stroke', 'white');
        circle.setAttribute('stroke-width', '2.5');
      });
      circle.addEventListener('mouseleave', () => {
        tooltip.style.opacity = '0';
        circle.setAttribute('stroke', 'rgba(255,255,255,0.3)');
        circle.setAttribute('stroke-width', '1.5');
      });

      svg.appendChild(circle);

      const text = document.createElementNS('http://www.w3.org/2000/svg', 'text');
      text.setAttribute('x', n.x);
      text.setAttribute('y', n.y + r + 12);
      text.setAttribute('text-anchor', 'middle');
      text.setAttribute('fill', 'rgba(255,255,255,0.7)');
      text.setAttribute('font-size', '10');
      text.style.pointerEvents = 'none';
      text.textContent = n.id.length > 14 ? n.id.slice(0,14)+'…' : n.id;
      svg.appendChild(text);
    });
  }
});
