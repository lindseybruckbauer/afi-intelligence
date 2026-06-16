document.addEventListener('DOMContentLoaded', function () {
  const messages  = document.getElementById('messages');
  const sourcesEl = document.getElementById('sources');
  const input     = document.getElementById('chat-input');
  if (!messages) return;

  const API_URL = 'https://afi-intelligence.onrender.com';
  let history = [];

  function appendMsg(text, isUser) {
    const div = document.createElement('div');
    div.style.cssText = [
      'margin-bottom:12px','padding:10px 14px','border-radius:6px',
      'white-space:pre-wrap','line-height:1.5',
      isUser ? 'background:#003F87;color:white;text-align:right'
             : 'background:var(--md-default-fg-color--lightest)'
    ].join(';');
    div.innerText = text;
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
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
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({message: question, history: history}),
      });
      const data = await res.json();
      thinking.innerText = data.reply;
      history.push({role:'user', content:question});
      history.push({role:'assistant', content:data.reply});
      if (sourcesEl) {
        const labels = (data.sources||[]).map(s => {
          let l = s.pub_number||'';
          if (s.section_number) l += ` §${s.section_number}`;
          return l;
        }).filter(Boolean);
        sourcesEl.innerText = labels.length ? 'Sources: '+labels.join(' · ') : '';
      }
    } catch(e) {
      thinking.innerText = 'Could not reach the API. It may be cold-starting — wait 20 seconds and try again.';
    } finally {
      input.disabled = false;
      input.focus();
    }
  };

  if (input) input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); window.sendQuery(); }
  });
});
