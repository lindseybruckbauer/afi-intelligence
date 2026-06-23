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

<div style="margin-top:32px;padding:16px;border-top:1px solid var(--md-default-fg-color--lightest);">
  <p style="margin:0 0 8px;font-size:0.85em;color:var(--md-default-fg-color--light);">
    Was this helpful?
  </p>
  <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px;">
    <button onclick="submitFeedback(5)"
      style="padding:6px 14px;border:1px solid #003F87;border-radius:4px;background:transparent;
             color:#003F87;cursor:pointer;font-size:0.9em;">
        Yes
    </button>
    <button onclick="submitFeedback(2)"
      style="padding:6px 14px;border:1px solid #888;border-radius:4px;background:transparent;
             color:var(--md-default-fg-color);cursor:pointer;font-size:0.9em;">
        Not really
    </button>
  </div>
  <textarea id="feedback-comment" rows="2"
    placeholder="Optional: what could be better? (max 1000 chars)"
    style="width:100%;max-width:600px;padding:8px;border:1px solid var(--md-default-fg-color--lightest);
           border-radius:4px;background:transparent;color:var(--md-default-fg-color);
           font-family:inherit;font-size:0.85em;resize:vertical;"></textarea>
  <div id="feedback-status" style="margin-top:4px;font-size:0.8em;
       color:var(--md-default-fg-color--light);min-height:1.2em;"></div>
</div>
 
<!-- Also add a clear history button near the chat header -->
<div style="margin-bottom:8px;text-align:right;">
  <button onclick="clearChatHistory()"
    style="padding:4px 10px;border:1px solid #888;border-radius:4px;background:transparent;
           color:var(--md-default-fg-color--light);cursor:pointer;font-size:0.8em;">
    Clear history
  </button>
</div>
