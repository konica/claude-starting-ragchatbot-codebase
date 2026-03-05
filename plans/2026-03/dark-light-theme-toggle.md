# Dark/Light Theme Toggle

## Context

The app currently has a dark-only theme. Users should be able to switch between dark and light themes via a toggle button. All colors are already defined as CSS custom properties in `:root`, making this straightforward to implement.

## Files to Modify

### `frontend/style.css`
- Move existing dark theme variables under `[data-theme="dark"]` (and keep as `:root` default)
- Add `[data-theme="light"]` block with light theme variables
- Add theme toggle button styles (positioned top-right of the chat area header)
- Add `transition` on `body` for smooth theme switching
- Style the toggle button with sun/moon FontAwesome icons

### `frontend/index.html`
- Add a theme toggle button in the chat header area (top-right)
- Use FontAwesome icons: `fa-sun` (light mode indicator) / `fa-moon` (dark mode indicator)

### `frontend/script.js`
- Add click handler to toggle `data-theme` between `"dark"` and `"light"` on `<html>`
- Swap the icon between sun and moon on toggle

## Implementation Steps

1. **CSS: Define light theme variables** — Add a `[data-theme="light"]` selector with light-appropriate values for all existing CSS variables (background, surface, text, borders, message colors, etc.)
2. **CSS: Add transition** — Add `transition: background-color 0.3s ease, color 0.3s ease` to `body` and key containers for smooth switching
3. **CSS: Style the toggle button** — Position it absolute top-right inside the chat main area, circular icon button, with hover/focus states
4. **HTML: Add toggle button** — Place a `<button>` with FontAwesome moon icon (default dark) inside the `.chat-main` area
5. **JS: Wire up toggle logic** — On click, flip `data-theme` attribute on `<html>`, swap icon class between `fa-moon` and `fa-sun`

## Light Theme Color Mapping

| Variable | Dark (current) | Light |
|---|---|---|
| `--background` | `#0f172a` | `#f8fafc` |
| `--surface` | `#1e293b` | `#ffffff` |
| `--surface-hover` | `#334155` | `#f1f5f9` |
| `--text-primary` | `#f1f5f9` | `#0f172a` |
| `--text-secondary` | `#94a3b8` | `#64748b` |
| `--border-color` | `#334155` | `#e2e8f0` |
| `--user-message` | `#2563eb` | `#2563eb` (keep) |
| `--assistant-message` | `#374151` | `#f1f5f9` |
| `--shadow` | `rgba(0,0,0,0.3)` | `rgba(0,0,0,0.1)` |
| `--welcome-bg` | `#1e3a5f` | `#eff6ff` |
| `--welcome-border` | `#2563eb` | `#93bbfd` |
| `--focus-ring` | `rgba(37,99,235,0.2)` | `rgba(37,99,235,0.15)` |

Primary color (`#2563eb`) and primary hover stay the same — they work on both backgrounds.

## Verification

1. Start the server (`./run.sh`)
2. Open `http://localhost:8000`
3. Verify dark theme is default
4. Click the toggle button — confirm smooth transition to light theme
5. Verify all elements are readable: sidebar, messages, sources, code blocks, input field
6. Click again to return to dark — confirm round-trip
7. Test keyboard navigation (Tab to button, Enter/Space to toggle)
8. Test on mobile viewport (responsive behavior)
