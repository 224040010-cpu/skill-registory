# CSS Aesthetics Reference

Complete CSS guidance for distinctive frontend designs.

## The Distilled Aesthetics Prompt

Append to system prompt or include in instructions when generating HTML/CSS:

```
<frontend_aesthetics>
You tend to converge toward generic, "on distribution" outputs. In frontend design, this creates what users call the "AI slop" aesthetic. Avoid this: make creative, distinctive frontends that surprise and delight. Focus on:

Typography: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics.

Color & Theme: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes. Draw from IDE themes and cultural aesthetics for inspiration.

Motion: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions.

Backgrounds: Create atmosphere and depth rather than defaulting to solid colors. Layer CSS gradients, use geometric patterns, or add contextual effects that match the overall aesthetic.

Avoid generic AI-generated aesthetics:
- Overused font families (Inter, Roboto, Arial, system fonts)
- Clichéd color schemes (particularly purple gradients on white backgrounds)
- Predictable layouts and component patterns
- Cookie-cutter design that lacks context-specific character

Interpret creatively and make unexpected choices that feel genuinely designed for the context. Vary between light and dark themes, different fonts, different aesthetics. You still tend to converge on common choices (Space Grotesk, for example) across generations. Avoid this: it is critical that you think outside the box!
</frontend_aesthetics>
```

## Theme Examples

### Dark Tech Theme (IDE-inspired)

```css
:root {
    --bg-primary: #0d1117;
    --bg-secondary: #161b22;
    --bg-tertiary: #21262d;
    --text-primary: #c9d1d9;
    --text-secondary: #8b949e;
    --accent-primary: #58a6ff;
    --accent-secondary: #238636;
    --accent-warning: #d29922;
    --accent-error: #f85149;
    --border-color: #30363d;
    --font-display: 'Clash Display', sans-serif;
    --font-body: 'IBM Plex Sans', sans-serif;
    --font-mono: 'JetBrains Mono', monospace;
}

body {
    background: linear-gradient(180deg, var(--bg-primary) 0%, #0a0e14 100%);
    color: var(--text-primary);
    font-family: var(--font-body);
}
```

### Warm Editorial Theme

```css
:root {
    --bg-primary: #faf7f2;
    --bg-secondary: #f5f0e8;
    --text-primary: #1a1a1a;
    --text-secondary: #666;
    --accent-primary: #b8860b;
    --accent-secondary: #8b4513;
    --border-color: #e0d8c8;
    --font-display: 'Playfair Display', serif;
    --font-body: 'Crimson Pro', serif;
    --font-mono: 'Fira Code', monospace;
}

body {
    background: 
        radial-gradient(ellipse at top right, rgba(184, 134, 11, 0.05) 0%, transparent 50%),
        var(--bg-primary);
}
```

### Solarpunk Theme

```css
:root {
    --bg-primary: #1a2f1a;
    --bg-secondary: #243324;
    --text-primary: #e8f5e8;
    --text-secondary: #a8d4a8;
    --accent-primary: #7cb342;
    --accent-secondary: #ffb300;
    --accent-tertiary: #4fc3f7;
    --border-color: #3d5c3d;
    --font-display: 'Bricolage Grotesque', sans-serif;
    --font-body: 'Source Sans 3', sans-serif;
}

body {
    background: 
        linear-gradient(135deg, #1a2f1a 0%, #0f1f0f 50%, #1a2520 100%),
        url("data:image/svg+xml,..."); /* geometric leaf pattern */
}
```

### Cyberpunk/Neon Theme

```css
:root {
    --bg-primary: #0a0a0f;
    --bg-secondary: #12121a;
    --text-primary: #ffffff;
    --text-secondary: #888;
    --accent-primary: #ff00ff;
    --accent-secondary: #00ffff;
    --accent-tertiary: #ffff00;
    --glow-primary: 0 0 20px rgba(255, 0, 255, 0.5);
    --glow-secondary: 0 0 20px rgba(0, 255, 255, 0.5);
}

.neon-text {
    text-shadow: var(--glow-primary);
}

.card {
    border: 1px solid var(--accent-primary);
    box-shadow: var(--glow-primary);
}
```

## Animation Patterns

### Staggered Page Load

```css
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

.animate-in {
    animation: fadeInUp 0.5s ease-out forwards;
    opacity: 0;
}

.animate-in:nth-child(1) { animation-delay: 0.1s; }
.animate-in:nth-child(2) { animation-delay: 0.2s; }
.animate-in:nth-child(3) { animation-delay: 0.3s; }
.animate-in:nth-child(4) { animation-delay: 0.4s; }
```

### Subtle Hover Effects

```css
.card {
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.15);
}

.button {
    transition: all 0.15s ease;
}

.button:hover {
    transform: scale(1.02);
    filter: brightness(1.1);
}
```

### Loading Skeleton

```css
@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

.skeleton {
    background: linear-gradient(
        90deg,
        var(--bg-secondary) 0%,
        var(--bg-tertiary) 50%,
        var(--bg-secondary) 100%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: 4px;
}
```

## Background Patterns

### Gradient Mesh

```css
body {
    background: 
        radial-gradient(at 40% 20%, rgba(88, 166, 255, 0.15) 0px, transparent 50%),
        radial-gradient(at 80% 0%, rgba(35, 134, 54, 0.1) 0px, transparent 50%),
        radial-gradient(at 0% 50%, rgba(210, 153, 34, 0.1) 0px, transparent 50%),
        var(--bg-primary);
}
```

### Dot Grid

```css
body {
    background-image: radial-gradient(
        circle at 1px 1px,
        var(--border-color) 1px,
        transparent 0
    );
    background-size: 24px 24px;
}
```

### Noise Texture

```css
body::before {
    content: '';
    position: fixed;
    inset: 0;
    background: url("data:image/svg+xml,..."); /* noise SVG */
    opacity: 0.03;
    pointer-events: none;
}
```

## Typography Scale

Use a modular scale for consistent hierarchy:

```css
:root {
    --text-xs: 0.75rem;    /* 12px */
    --text-sm: 0.875rem;   /* 14px */
    --text-base: 1rem;     /* 16px */
    --text-lg: 1.125rem;   /* 18px */
    --text-xl: 1.5rem;     /* 24px */
    --text-2xl: 2rem;      /* 32px */
    --text-3xl: 2.5rem;    /* 40px */
    --text-4xl: 3.5rem;    /* 56px */
    
    --weight-light: 300;
    --weight-normal: 400;
    --weight-medium: 500;
    --weight-bold: 700;
    --weight-black: 900;
}
```

## Google Fonts Import Examples

```html
<!-- Technical/Code aesthetic -->
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Space+Grotesk:wght@300;500;700&display=swap" rel="stylesheet">

<!-- Editorial/Premium -->
<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=Crimson+Pro:wght@300;400;600&display=swap" rel="stylesheet">

<!-- Modern/Startup -->
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;600&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet">
```
