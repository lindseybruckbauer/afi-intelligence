// AFI Intelligence — Chat Interface
// API URL: set window.CHAT_API_URL before this script loads to override,
// otherwise falls back to localhost:8000 (local dev / ngrok tunnel).
//
// For demo with ngrok: add a <script>window.CHAT_API_URL='https://xxx.ngrok.io'</script>
// in chat.md before the mkdocs extra_javascript block loads.

document.addEventListener('DOMContentLoaded', function () {
  const messages  = document.getElementById('messages');
  const sourcesEl = document.getElementById('sources');
  const input     = document.getElementById('chat-input');
  if (!messages) return;

  const API_URL = (window.CHAT_API_URL || 'https://afi-intelligence.onrender.com').replace(/\/$/, '');

  let history = [];   // [{role, content}] — maintains conversation context

  function appendMsg(text, isUser) {
    const div = document.createElement('div');
    div.style.cssText = [
      'margin-bottom:12px',
      'padding:10px 14px',
      'border-radius:6px',
      'white-space:pre-wrap',
      'line-height:1.5',
      isUser
        ? 'background:#003F87;color:white;text-align:right'
        : 'background:var(--md-default-fg-color--lightest)',
    ].join(';');
    div.innerText = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function showSources(sources) {
    if (!sourcesEl) return;
    if (!sources || sources.length === 0) {
      sourcesEl.innerText = '';
      return;
    }
    const labels = sources.map(s => {
      let label = s.pub_number || '';
      if (s.section_number) label += ` §${s.section_number}`;
      return label;
    }).filter(Boolean);
    sourcesEl.innerText = labels.length ? `Sources: ${labels.join(' · ')}` : '';
  }

  window.sendQuery = async function () {
    const question = input.value.trim();
    if (!question) return;
    input.value = '';
    input.disabled = true;

    appendMsg(question, true);
    const thinking = appendMsg('Searching corpus…', false);

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          message: question,
          history: history,
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned ${res.status}`);
      }

      const data = await res.json();
      const rawHtml = typeof marked !== "undefined" ? marked.parse(data.reply) : data.reply;
      thinking.innerHTML = typeof DOMPurify !== "undefined" ? DOMPurify.sanitize(rawHtml) : rawHtml;

      // Update conversation history for multi-turn context
      history.push({ role: 'user',      content: question     });
      history.push({ role: 'assistant', content: data.reply   });

      showSources(data.sources);

    } catch (e) {
      thinking.innerText =
        'Could not reach the API server.\n\n' +
        'If running locally: make sure uvicorn api.main:app --port 8000 is running.\n' +
        'If using ngrok: verify the tunnel is active and CHAT_API_URL is set.';
      thinking.style.color = '#C8102E';
      sourcesEl.innerText = '';
    } finally {
      input.disabled = false;
      input.focus();
    }
  };

  if (input) {
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        window.sendQuery();
      }
    });
  }
});
