document.addEventListener('DOMContentLoaded', function() {
  const messages = document.getElementById('messages');
  const sourcesEl = document.getElementById('sources');
  const input = document.getElementById('chat-input');

  if (!messages) return;

  function append(text, isUser) {
    const div = document.createElement('div');
    div.style.cssText = `margin-bottom:12px;padding:10px 14px;border-radius:6px;${isUser ? 'background:#5c6bc0;color:white;text-align:right' : 'background:var(--md-default-fg-color--lightest)'}`;
    div.innerText = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  window.sendQuery = async function() {
    const question = input.value.trim();
    if (!question) return;
    input.value = '';
    append(question, true);
    sourcesEl.innerText = 'Searching wiki...';

    try {
      const res = await fetch('http://127.0.0.1:8002/query', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question})
      });
      const data = await res.json();
      append(data.answer, false);
      sourcesEl.innerText = data.sources.length
        ? 'Sources: ' + data.sources.map(s => s.split('/').pop().replace('.md','')).join(', ')
        : '';
    } catch(e) {
      append('Could not reach the query server. Make sure query_server.py is running.', false);
      sourcesEl.innerText = '';
    }
  }

  if (input) {
    input.addEventListener('keydown', function(e) {
      if (e.key === 'Enter') window.sendQuery();
    });
  }
});
