# Wiki Assistant

Ask anything about the 36-series AFI corpus. The assistant searches the full text of 10 Air Force Instructions plus cross-publication gap, overlap, and authority analysis — and cites its sources.

<div id="chat-container" style="max-width:700px;margin:0 auto">
  <div id="messages" style="min-height:200px;padding:16px;border-radius:8px;background:var(--md-code-bg-color);margin-bottom:16px;font-size:14px;line-height:1.6"></div>
  <div style="display:flex;gap:8px">
    <input id="chat-input" type="text" placeholder="Ask a question about the wiki..."
      style="flex:1;padding:10px 14px;border-radius:6px;border:1px solid var(--md-default-fg-color--lightest);background:var(--md-code-bg-color);color:var(--md-default-fg-color);font-size:14px"/>
    <button onclick="sendQuery()"
      style="padding:10px 20px;border-radius:6px;background:#5c6bc0;color:white;border:none;cursor:pointer;font-size:14px">Ask</button>
  </div>
  <div id="sources" style="margin-top:8px;font-size:12px;color:var(--md-default-fg-color--light)"></div>
</div>
