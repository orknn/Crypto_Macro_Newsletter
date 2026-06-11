# render/tokens.py

STYLE_TOKENS = {
    'fonts': {
        'sans': 'Inter, system-ui, -apple-system, sans-serif',
        'serif': '"Playfair Display", Georgia, serif',
        'mono': '"JetBrains Mono", Menlo, Consolas, monospace'
    },
    'colors': {
        'bg': '#0b0f17',         # Deep dark blue-black
        'bg2': '#121824',        # Slightly lighter panel background
        'bg3': '#1c2436',        # Highlight card background
        'border': '#26344d',     # Muted border color
        'text': '#f0f4f9',       # High contrast off-white text
        'dim': '#94a3b8',        # Slate-400 dim text
        'gold': '#f59e0b',       # Amber-500 gold accent
        'gold2': '#fb923c',      # Orange-400 warm accent
        'green': '#10b981',      # Emerald-500 bullish green
        'red': '#ef4444',        # Red-500 bearish red
        'accent': '#3b82f6'      # Blue-500 cold accent
    }
}

CSS_VARIABLES = f"""
:root {{
    --bg: {STYLE_TOKENS['colors']['bg']};
    --bg2: {STYLE_TOKENS['colors']['bg2']};
    --bg3: {STYLE_TOKENS['colors']['bg3']};
    --border: {STYLE_TOKENS['colors']['border']};
    --text: {STYLE_TOKENS['colors']['text']};
    --dim: {STYLE_TOKENS['colors']['dim']};
    --gold: {STYLE_TOKENS['colors']['gold']};
    --gold2: {STYLE_TOKENS['colors']['gold2']};
    --green: {STYLE_TOKENS['colors']['green']};
    --red: {STYLE_TOKENS['colors']['red']};
    --accent: {STYLE_TOKENS['colors']['accent']};
    
    --sans: {STYLE_TOKENS['fonts']['sans']};
    --serif: {STYLE_TOKENS['fonts']['serif']};
    --mono: {STYLE_TOKENS['fonts']['mono']};
}}
"""
