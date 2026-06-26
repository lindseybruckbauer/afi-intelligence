// AFI Intelligence — Chat Interface
// Security: DOMPurify required (fails closed if not loaded)
// Persistence: localStorage, 10-turn cap, raw text stored (not HTML)

document.addEventListener('DOMContentLoaded', function () {
  const messages  = document.getElementById('messages');
  const sourcesEl = document.getElementById('sources');
  const input     = document.getElementById('chat-input');
  if (!messages) return;

  // Fail closed if security libs not loaded — do not render AI HTML without them
  if (typeof DOMPurify === 'undefined' || typeof marked === 'undefined') {
    const err = document.createElement('div');
    err.style.cssText = 'padding:12px;color:#C8102E;background:#fff0f0;border-radius:6px;';
    err.innerText = 'Security libraries failed to load. Chat is disabled. Please reload the page.';
    messages.appendChild(err);
    return;
  }

  const API_URL = (window.CHAT_API_URL || 'https://afi-intelligence.onrender.com').replace(/\/$/, '');

  // -----------------------------------------------------------------------
  // Persistence (localStorage)
  // -----------------------------------------------------------------------

  const STORAGE_KEY    = 'afi_chat_history_v1';
  const MAX_TURNS      = 10;   // mirrors server-side MAX_HISTORY_TURNS
  const SESSION_ID_KEY = 'afi_session_id';

  function getSessionId() {
    let id = sessionStorage.getItem(SESSION_ID_KEY);
    if (!id) {
      id = Math.random().toString(36).slice(2, 10);
      sessionStorage.setItem(SESSION_ID_KEY, id);
    }
    return id;
  }

  function loadHistory() {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return [];
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed.slice(-(MAX_TURNS * 2)) : [];
    } catch {
      return [];
    }
  }

  function saveHistory(hist) {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(hist.slice(-(MAX_TURNS * 2))));
    } catch {
      // Storage full or unavailable — continue without persistence
    }
  }

  function clearHistory() {
    if (!confirm('Clear all chat history?')) return;
    history = [];
    localStorage.removeItem(STORAGE_KEY);
    messages.innerHTML = '';
    if (sourcesEl) sourcesEl.innerText = '';
  }

  // Expose clear to the clear button in chat.md
  window.clearChatHistory = clearHistory;

  // -----------------------------------------------------------------------
  // Rendering
  // -----------------------------------------------------------------------

  function renderAssistantMarkdown(text) {
    // Always go through marked → DOMPurify. Never insert raw HTML.
    return DOMPurify.sanitize(marked.parse(text));
  }

  function appendMsg(text, isUser) {
    const div = document.createElement('div');
    div.style.cssText = [
      'margin-bottom:12px',
      'padding:10px 14px',
      'border-radius:6px',
      'line-height:1.5',
      isUser
        ? 'background:#003F87;color:white;text-align:right;white-space:pre-wrap'
        : 'background:var(--md-default-fg-color--lightest)',
    ].join(';');

    if (isUser) {
      div.innerText = text;  // innerText for user input — no HTML
    } else {
      div.innerHTML = renderAssistantMarkdown(text);
    }

    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
    return div;
  }

  function appendThinking() {
    const div = document.createElement('div');
    div.style.cssText = [
      'margin-bottom:12px',
      'padding:10px 14px',
      'border-radius:6px',
      'line-height:1.5',
      'background:var(--md-default-fg-color--lightest)',
      'color:var(--md-default-fg-color--light)',
      'font-style:italic',
    ].join(';');
    div.innerText = 'Searching corpus\u2026';
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
      if (s.section_number) label += ` \u00a7${s.section_number}`;
      return label;
    }).filter(Boolean);
    sourcesEl.innerText = labels.length ? `Sources: ${labels.join(' \u00b7 ')}` : '';
  }

  // -----------------------------------------------------------------------
  // Restore history on load
  // -----------------------------------------------------------------------

  let history = loadHistory();

  if (history.length > 0) {
    history.forEach(msg => appendMsg(msg.content, msg.role === 'user'));
    if (sourcesEl) {
      sourcesEl.innerText = '\u2191 Restored from previous session';
      setTimeout(() => { if (sourcesEl) sourcesEl.innerText = ''; }, 3000);
    }
  }

  // -----------------------------------------------------------------------
  // Send query
  // -----------------------------------------------------------------------

  window.sendQuery = async function () {
    const question = input.value.trim();
    if (!question) return;
    input.value = '';
    input.disabled = true;

    appendMsg(question, true);
    const thinking = appendThinking();

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
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `Server error ${res.status}`);
      }

      const data = await res.json();

      // Replace thinking placeholder with rendered response
      thinking.innerHTML = renderAssistantMarkdown(data.reply);
      thinking.style.fontStyle = '';
      thinking.style.color = '';

      // Update history and persist
      history.push({ role: 'user',      content: question   });
      history.push({ role: 'assistant', content: data.reply });
      if (history.length > MAX_TURNS * 2) {
        history = history.slice(-(MAX_TURNS * 2));
      }
      saveHistory(history);

      showSources(data.sources);

    } catch (e) {
      thinking.innerText =
        `Error: ${e.message || 'Could not reach the API server.'}\n\n` +
        'If running locally: make sure uvicorn api.main:app --port 8000 is running.';
      thinking.style.color  = '#C8102E';
      thinking.style.fontStyle = '';
      if (sourcesEl) sourcesEl.innerText = '';
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

  // -----------------------------------------------------------------------
  // Feedback
  // -----------------------------------------------------------------------

  window.submitFeedback = async function (rating) {
    const commentEl = document.getElementById('feedback-comment');
    const statusEl  = document.getElementById('feedback-status');
    const comment   = commentEl ? commentEl.value.trim().slice(0, 1000) : '';

    if (statusEl) statusEl.innerText = 'Sending\u2026';

    try {
      const res = await fetch(`${API_URL}/feedback`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
          rating:     rating,
          comment:    comment,
          session_id: getSessionId(),
        }),
      });
      if (!res.ok) throw new Error('Server error');
      if (statusEl) statusEl.innerText = 'Thanks for the feedback!';
      if (commentEl) commentEl.value = '';
    } catch {
      if (statusEl) statusEl.innerText = 'Could not send feedback. Please try again.';
    }
  };
});
