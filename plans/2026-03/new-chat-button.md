# Feature: + New Chat Button

**Branch:** `feat/new-chat-button`
**Date:** 2026-03

## Context

The chatbot has no way to start a fresh conversation without a full page reload. Adding a `+ NEW CHAT` button to the top of the left sidebar lets users reset the chat instantly. The `createNewSession()` function in `frontend/script.js` already handles everything needed — no backend changes required.

## Files to Modify

| File | Change |
|------|--------|
| `frontend/index.html` | Add button element above the Courses section |
| `frontend/style.css` | Add `.new-chat-button` styles matching existing sidebar headers |
| `frontend/script.js` | Wire button click to existing `createNewSession()` |

## Implementation Steps

1. **`frontend/index.html`** — Insert above `<!-- Course Stats -->`. Use the FontAwesome plus icon (already loaded via CDN) instead of a literal `+`:
   ```html
   <!-- New Chat -->
   <div class="sidebar-section">
       <button id="newChatButton" class="new-chat-button">
           <i class="fa-solid fa-plus"></i> New Chat
       </button>
   </div>
   ```

2. **`frontend/style.css`** — Add after `.sidebar-section:last-child` block, matching `.stats-header` / `.suggested-header` style (`0.875rem`, `font-weight: 600`, `text-transform: uppercase`, `letter-spacing: 0.5px`):
   ```css
   .new-chat-button {
       font-size: 0.875rem;
       font-weight: 600;
       color: var(--text-secondary);
       text-transform: uppercase;
       letter-spacing: 0.5px;
       background: none;
       border: none;
       padding: 0;
       width: 100%;
       text-align: left;
       cursor: pointer;
   }

   .new-chat-button:hover {
       color: var(--primary-color);
   }
   ```

3. **`frontend/script.js`** — Add inside `setupEventListeners()`, reusing the existing `createNewSession()`:
   ```javascript
   document.getElementById('newChatButton').addEventListener('click', createNewSession);
   ```

## Verification

- FontAwesome `fa-plus` icon renders before "NEW CHAT" text, above `COURSES` in the sidebar
- Clicking clears the chat and shows the welcome message (no page reload)
- Sending a new message after clicking returns a different `session_id` from the backend
