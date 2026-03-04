---
paths:
  - "frontend/*.html"
  - "frontend/*.js"
  - "frontend/*.css"
---

# Frontend Rules

## Icons

Always prioritize FontAwesome icons over custom icons or inline SVGs.

- Check the [FontAwesome free icon set](https://fontawesome.com/icons) before creating any custom icon solution.
- Use FontAwesome class syntax: `<i class="fa-solid fa-magnifying-glass"></i>`
- Only fall back to a custom icon if no suitable FontAwesome icon exists.
