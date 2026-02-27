import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.patches as patches
import numpy as np

# Navy theme colors
BG_COLOR = '#1a2980'       # Vivid navy blue (figure background)
CHART_BG = '#ffffff'       # White (chart plot area for readability)
TEXT_COLOR = '#2c3e50'     # Dark text for white chart backgrounds
TITLE_COLOR = '#f0b90b'    # Gold for titles
ACCENT_BLUE = '#2980b9'    # Rich blue for lines
GRID_COLOR = '#d0d0d0'     # Light gray grid on white bg

def _apply_chart_style(fig, ax):
    """Apply navy + white chart theme to a matplotlib figure/axes."""
    fig.patch.set_facecolor(BG_COLOR)
    ax.set_facecolor(CHART_BG)
    ax.tick_params(colors=TEXT_COLOR, labelsize=8)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('#bdc3c7')
    ax.spines['left'].set_color('#bdc3c7')
    ax.xaxis.label.set_color(TEXT_COLOR)
    ax.yaxis.label.set_color(TEXT_COLOR)
    ax.title.set_color(TITLE_COLOR)

def generate_coinbase_premium_chart(trend_data, output_path):
    """
    Generate a 1-hour trend chart for Coinbase Premium Index with dark theme.
    """
    times = [d['time'] for d in trend_data]
    values = [d['value'] for d in trend_data]
    
    fig, ax = plt.subplots(figsize=(7, 3))
    _apply_chart_style(fig, ax)
    
    # Gradient line
    ax.plot(times, values, color=ACCENT_BLUE, linewidth=2, zorder=3)
    ax.fill_between(times, values, min(values) - 0.01, color=ACCENT_BLUE, alpha=0.15)
    
    # Zero line
    ax.axhline(y=0, color='#e74c3c', linewidth=0.8, linestyle='--', alpha=0.7)
    
    ax.set_title("Coinbase Premium Index (1 Saatlik Trend)", fontsize=11, fontweight='bold', pad=10, color=TITLE_COLOR)
    ax.set_xlabel("Zaman", fontsize=8)
    ax.set_ylabel("Premium (%)", fontsize=8)
    
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45, fontsize=7)
    ax.grid(True, linestyle='--', alpha=0.3, color=GRID_COLOR)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    return output_path

def generate_fear_greed_gauge(value, classification, output_path):
    """
    Generate a semi-circle gauge chart for Fear & Greed Index.
    value: int 0-100
    classification: str e.g. 'Fear', 'Greed', 'Extreme Fear', etc.
    """
    fig, ax = plt.subplots(figsize=(5, 3.2))
    fig.patch.set_facecolor(CHART_BG)
    ax.set_facecolor(CHART_BG)
    
    # Draw gauge segments
    segment_colors = ['#ea3943', '#ea8c00', '#f5d100', '#93c47d', '#16c784']
    segment_labels = ['Extreme\nFear', 'Fear', 'Neutral', 'Greed', 'Extreme\nGreed']
    n_segments = len(segment_colors)
    total_angle = 180  # semi-circle
    segment_angle = total_angle / n_segments
    
    for i, color in enumerate(segment_colors):
        start_angle = 180 - i * segment_angle
        wedge = patches.Wedge(
            center=(0.5, 0),
            r=0.45,
            theta1=start_angle - segment_angle,
            theta2=start_angle,
            facecolor=color,
            edgecolor=CHART_BG,
            linewidth=2,
            alpha=0.85
        )
        ax.add_patch(wedge)
        
        # Add segment label
        mid_angle = np.radians(start_angle - segment_angle / 2)
        lx = 0.5 + 0.33 * np.cos(mid_angle)
        ly = 0.0 + 0.33 * np.sin(mid_angle)
        ax.text(lx, ly, segment_labels[i], ha='center', va='center',
                fontsize=5.5, color='white', fontweight='bold', alpha=1.0)
    
    # Inner circle to make it a donut
    inner_circle = patches.Circle((0.5, 0), 0.2, facecolor=CHART_BG, edgecolor=CHART_BG)
    ax.add_patch(inner_circle)
    
    # Draw needle
    needle_angle = np.radians(180 - (value / 100) * 180)
    needle_x = 0.5 + 0.38 * np.cos(needle_angle)
    needle_y = 0.0 + 0.38 * np.sin(needle_angle)
    ax.annotate('', xy=(needle_x, needle_y), xytext=(0.5, 0),
                arrowprops=dict(arrowstyle='->', color='#2c3e50', lw=2.5))
    
    # Center dot
    center_dot = patches.Circle((0.5, 0), 0.03, facecolor='#2c3e50', edgecolor=CHART_BG, zorder=5)
    ax.add_patch(center_dot)
    
    # Value text
    ax.text(0.5, -0.1, str(value), ha='center', va='center',
            fontsize=28, fontweight='bold', color='#e67e22')
    ax.text(0.5, -0.2, classification, ha='center', va='center',
            fontsize=11, color=TEXT_COLOR, fontstyle='italic')
    
    # Title
    ax.text(0.5, 0.55, 'Crypto Fear & Greed Index', ha='center', va='center',
            fontsize=12, fontweight='bold', color='#2c3e50')
    
    ax.set_xlim(-0.05, 1.05)
    ax.set_ylim(-0.3, 0.65)
    ax.set_aspect('equal')
    ax.axis('off')
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=CHART_BG)
    plt.close()
    return output_path

def generate_macro_bar_chart(macro_data, output_path):
    """
    Generate a horizontal bar chart for macro indicators with dark theme.
    macro_data: dict {name: value, ...}
    """
    names = list(macro_data.keys())
    values = list(macro_data.values())
    
    # Short labels
    short_names = {
        'US 10-Year Treasury Yield': '10Y Yield',
        'NASDAQ 100 Futures': 'NQ Futures',
    }
    display_names = [short_names.get(n, n) for n in names]
    
    fig, ax = plt.subplots(figsize=(7, 3.5))
    _apply_chart_style(fig, ax)
    
    # Color bars based on value magnitude (normalized)
    bar_colors = []
    for v in values:
        if v > 1000:
            bar_colors.append('#f0b90b')  # gold for large values
        elif v > 100:
            bar_colors.append(ACCENT_BLUE)
        elif v > 10:
            bar_colors.append('#93c47d')
        else:
            bar_colors.append('#ff6b6b')
    
    bars = ax.barh(display_names, values, color=bar_colors, edgecolor='white', height=0.6, alpha=0.9)
    
    # Value labels on bars
    for bar, val in zip(bars, values):
        label = f'{val:,.2f}'
        x_pos = bar.get_width()
        ax.text(x_pos + max(values) * 0.02, bar.get_y() + bar.get_height() / 2,
                label, va='center', ha='left', color=TEXT_COLOR, fontsize=7.5, fontweight='bold')
    
    ax.set_title('Macro Indicators & Traditional Assets', fontsize=11, fontweight='bold', pad=10)
    ax.set_xlabel('Value', fontsize=8)
    ax.grid(True, axis='x', linestyle='--', alpha=0.2, color=GRID_COLOR)
    ax.invert_yaxis()
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    return output_path

def generate_crypto_market_chart(crypto_overview, output_path):
    """
    Generate a 4-panel summary card for crypto market metrics:
    Total Market Cap, Total3, BTC Dominance, Stablecoin Dominance.
    """
    fig, axes = plt.subplots(1, 4, figsize=(10, 2.5))
    fig.patch.set_facecolor(BG_COLOR)
    
    metrics = [
        {
            'title': 'Total Market Cap',
            'value': f"${crypto_overview['total_market_cap']/1e12:.2f}T",
            'color': '#f0b90b',
        },
        {
            'title': 'Total3\n(Excl. BTC+ETH)',
            'value': f"${crypto_overview['total3']/1e12:.2f}T",
            'color': '#60a5fa',
        },
        {
            'title': 'BTC Dominance',
            'value': f"{crypto_overview['btc_dominance']:.1f}%",
            'color': '#f7931a',
        },
        {
            'title': 'Stablecoin\nDominance',
            'value': f"{crypto_overview['stablecoin_dominance']:.1f}%",
            'color': '#26a17b',
        },
    ]
    
    for ax, metric in zip(axes, metrics):
        ax.set_facecolor('#162670')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        # Round rectangle background
        rect = patches.FancyBboxPatch(
            (0.05, 0.05), 0.9, 0.9,
            boxstyle="round,pad=0.05",
            facecolor='#1e3a8a',
            edgecolor='#3b5bdb',
            linewidth=1.5,
        )
        ax.add_patch(rect)
        
        # Title
        ax.text(0.5, 0.75, metric['title'], ha='center', va='center',
                fontsize=8, color='#b0c4de', fontweight='bold')
        
        # Value
        ax.text(0.5, 0.35, metric['value'], ha='center', va='center',
                fontsize=16, color=metric['color'], fontweight='bold')
    
    fig.suptitle('Crypto Market Overview', fontsize=12, fontweight='bold',
                 color=TITLE_COLOR, y=1.02)
    
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor=BG_COLOR)
    plt.close()
    return output_path
