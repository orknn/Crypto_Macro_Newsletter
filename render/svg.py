# render/svg.py
import math
from datetime import datetime
from render.tokens import STYLE_TOKENS

def generate_sparkline(prices, width=100, height=30):
    """Generate a clean sparkline for 7-day price trajectory."""
    if not prices or len(prices) < 2:
        return ""
    
    # Clean prices
    prices = [float(p) for p in prices if p is not None]
    if len(prices) < 2:
        return ""
        
    min_val, max_val = min(prices), max(prices)
    diff = max_val - min_val if max_val != min_val else 1.0
    
    points = []
    for i, val in enumerate(prices):
        x = (i / (len(prices) - 1)) * width
        y = height - ((val - min_val) / diff) * height
        # Ensure some padding
        y = max(2, min(height - 2, y))
        points.append(f"{x:.1f},{y:.1f}")
        
    path_d = f"M {points[0]} " + " ".join([f"L {p}" for p in points[1:]])
    
    # Determine color (green if last >= first, red otherwise)
    color = STYLE_TOKENS['colors']['green'] if prices[-1] >= prices[0] else STYLE_TOKENS['colors']['red']
    
    svg = f'''
    <svg width="{width}" height="{height}" viewBox="0 0 {width} {height}" style="display:inline-block; vertical-align:middle; overflow:visible;">
      <path d="{path_d}" fill="none" stroke="{color}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
      <circle cx="{width}" cy="{points[-1].split(',')[1]}" r="2.5" fill="{color}"/>
    </svg>
    '''
    return svg

def generate_net_liquidity_chart(series, width=600, height=200):
    """Draw a 3-year line chart of Net Liquidity."""
    if not series or len(series) < 2:
        return '<div style="color:var(--dim); text-align:center; padding:20px;">No historical Net Liquidity data</div>'
        
    dates = [s['date'] for s in series]
    values = [s['value'] for s in series]
    
    min_val, max_val = min(values), max(values)
    diff = max_val - min_val if max_val != min_val else 1.0
    # Add 5% padding to y-axis limits
    min_val -= diff * 0.05
    max_val += diff * 0.05
    diff = max_val - min_val
    
    padding_left = 50
    padding_right = 20
    padding_top = 20
    padding_bottom = 30
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom
    
    points = []
    for i, val in enumerate(values):
        x = padding_left + (i / (len(values) - 1)) * chart_w
        y = padding_top + chart_h - ((val - min_val) / diff) * chart_h
        points.append(f"{x:.1f},{y:.1f}")
        
    path_d = f"M {points[0]} " + " ".join([f"L {p}" for p in points[1:]])
    area_d = f"M {padding_left:.1f},{padding_top + chart_h:.1f} " + " ".join([f"L {p}" for p in points]) + f" L {padding_left + chart_w:.1f},{padding_top + chart_h:.1f} Z"
    
    # X-axis label index selection
    labels = []
    n = len(series)
    label_indices = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
    for idx in label_indices:
        dt = series[idx]['date']
        # Convert YYYY-MM-DD to MMM YY
        try:
            parsed = datetime.strptime(dt, "%Y-%m-%d")
            lbl = parsed.strftime("%b %y")
        except:
            lbl = dt
        lx = padding_left + (idx / (n - 1)) * chart_w
        labels.append(f'<text x="{lx:.1f}" y="{height - 8}" fill="var(--dim)" font-size="9" text-anchor="middle" font-family="var(--sans)">{lbl}</text>')
        
    # Y-axis ticks
    y_ticks = []
    for k in range(4):
        val = min_val + (k / 3) * diff
        ly = padding_top + chart_h - (k / 3) * chart_h
        y_ticks.append(f'''
        <line x1="{padding_left}" y1="{ly:.1f}" x2="{width - padding_right}" y2="{ly:.1f}" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.4"/>
        <text x="{padding_left - 8}" y="{ly + 3:.1f}" fill="var(--dim)" font-size="9" text-anchor="end" font-family="var(--mono)">${val:.2f}T</text>
        ''')
        
    color_accent = STYLE_TOKENS['colors']['accent']
    
    svg = f'''
    <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
      <!-- Grid -->
      {''.join(y_ticks)}
      <!-- Area Gradient -->
      <defs>
        <linearGradient id="liqGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="{color_accent}" stop-opacity="0.18"/>
          <stop offset="100%" stop-color="{color_accent}" stop-opacity="0.00"/>
        </linearGradient>
      </defs>
      <path d="{area_d}" fill="url(#liqGrad)" />
      <!-- Line -->
      <path d="{path_d}" fill="none" stroke="{color_accent}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      <!-- X-axis Labels -->
      {''.join(labels)}
      <!-- Axis border line -->
      <line x1="{padding_left}" y1="{padding_top + chart_h}" x2="{width - padding_right}" y2="{padding_top + chart_h}" stroke="var(--border)" stroke-width="1"/>
    </svg>
    '''
    return svg

def generate_inflation_chart(series, width=600, height=200):
    """Draw a 5-year line chart containing CPI, Core CPI, Core PCE YoY."""
    if not series or len(series) < 2:
        return '<div style="color:var(--dim); text-align:center; padding:20px;">No inflation history data</div>'
        
    dates = [s['date'] for s in series]
    cpi = [s['cpi'] for s in series]
    core_cpi = [s['core_cpi'] for s in series]
    core_pce = [s['core_pce'] for s in series]
    
    all_vals = cpi + core_cpi + core_pce
    min_val, max_val = min(all_vals), max(all_vals)
    # Make sure we see 2.0% line and 0% line
    min_val = min(0.0, min_val - 0.5)
    max_val = max(3.0, max_val + 0.5)
    diff = max_val - min_val
    
    padding_left = 50
    padding_right = 20
    padding_top = 20
    padding_bottom = 30
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom
    
    def get_points(vals):
        pts = []
        for i, val in enumerate(vals):
            x = padding_left + (i / (len(vals) - 1)) * chart_w
            y = padding_top + chart_h - ((val - min_val) / diff) * chart_h
            pts.append(f"{x:.1f},{y:.1f}")
        return pts
        
    pts_cpi = get_points(cpi)
    pts_core_cpi = get_points(core_cpi)
    pts_core_pce = get_points(core_pce)
    
    path_cpi = f"M {pts_cpi[0]} " + " ".join([f"L {p}" for p in pts_cpi[1:]])
    path_core_cpi = f"M {pts_core_cpi[0]} " + " ".join([f"L {p}" for p in pts_core_cpi[1:]])
    path_core_pce = f"M {pts_core_pce[0]} " + " ".join([f"L {p}" for p in pts_core_pce[1:]])
    
    # 2% target line
    y_target = padding_top + chart_h - ((2.0 - min_val) / diff) * chart_h
    target_line = f'<line x1="{padding_left}" y1="{y_target:.1f}" x2="{width - padding_right}" y2="{y_target:.1f}" stroke="{STYLE_TOKENS["colors"]["gold"]}" stroke-width="1" stroke-dasharray="4,4"/>'
    target_label = f'<text x="{width - padding_right - 4}" y="{y_target - 4:.1f}" fill="{STYLE_TOKENS["colors"]["gold"]}" font-size="8" text-anchor="end" font-family="var(--sans)">2.0% Target</text>'
    
    # X labels
    n = len(series)
    labels = []
    label_indices = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
    for idx in label_indices:
        dt = series[idx]['date']
        lx = padding_left + (idx / (n - 1)) * chart_w
        labels.append(f'<text x="{lx:.1f}" y="{height - 8}" fill="var(--dim)" font-size="9" text-anchor="middle" font-family="var(--sans)">{dt}</text>')
        
    # Y-axis ticks
    y_ticks = []
    for k in range(5):
        val = min_val + (k / 4) * diff
        ly = padding_top + chart_h - (k / 4) * chart_h
        y_ticks.append(f'''
        <line x1="{padding_left}" y1="{ly:.1f}" x2="{width - padding_right}" y2="{ly:.1f}" stroke="var(--border)" stroke-width="0.5" opacity="0.3"/>
        <text x="{padding_left - 8}" y="{ly + 3:.1f}" fill="var(--dim)" font-size="9" text-anchor="end" font-family="var(--mono)">{val:.1f}%</text>
        ''')
        
    svg = f'''
    <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
      {''.join(y_ticks)}
      {target_line}
      {target_label}
      <!-- CPI line -->
      <path d="{path_cpi}" fill="none" stroke="{STYLE_TOKENS['colors']['accent']}" stroke-width="2" stroke-linecap="round"/>
      <!-- Core CPI line -->
      <path d="{path_core_cpi}" fill="none" stroke="{STYLE_TOKENS['colors']['red']}" stroke-width="1.5" stroke-linecap="round"/>
      <!-- Core PCE line -->
      <path d="{path_core_pce}" fill="none" stroke="{STYLE_TOKENS['colors']['green']}" stroke-width="1.5" stroke-linecap="round"/>
      
      {''.join(labels)}
      <line x1="{padding_left}" y1="{padding_top + chart_h}" x2="{width - padding_right}" y2="{padding_top + chart_h}" stroke="var(--border)" stroke-width="1"/>
    </svg>
    '''
    return svg

def generate_etf_flow_chart(etf_history, width=600, height=140):
    """Draw a bar chart of daily or weekly ETF flows (last N periods)."""
    if not etf_history or len(etf_history) == 0:
        return '<div style="color:var(--dim); text-align:center; padding:15px;">No historical ETF flow data</div>'
        
    values = [float(item['Total_flow_m']) for item in etf_history]
    dates = [item['date'] for item in etf_history]
    
    max_val = max(abs(v) for v in values) if values else 100.0
    if max_val == 0:
        max_val = 100.0
        
    padding_top = 10
    padding_bottom = 20
    chart_h = height - padding_top - padding_bottom
    zero_y = padding_top + chart_h / 2
    
    # Scale: maps max absolute value to chart_h / 2
    scale = (chart_h / 2) / max_val
    
    n = len(etf_history)
    bar_gap = 4
    bar_width = max(2, (width - (n - 1) * bar_gap) / n)
    
    bars = []
    labels = []
    
    for i, item in enumerate(etf_history):
        val = float(item['Total_flow_m'])
        dt = item['date']
        
        # Format date for readability (e.g. 10 Jun)
        try:
            parsed = datetime.strptime(dt, "%d %b %Y") if len(dt.split()) == 3 else datetime.strptime(dt, "%Y-%m-%d")
            lbl = parsed.strftime("%d %b")
        except:
            lbl = dt.replace("2026-", "").replace("2025-", "")
            
        x = i * (bar_width + bar_gap)
        bar_h = abs(val) * scale
        bar_h = max(1, bar_h) # ensure thin bar visible
        
        if val >= 0:
            y = zero_y - bar_h
            color = STYLE_TOKENS['colors']['green']
        else:
            y = zero_y
            color = STYLE_TOKENS['colors']['red']
            
        bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bar_width:.1f}" height="{bar_h:.1f}" fill="{color}" rx="1"/>')
        
        # Show label on every other bar or fewer
        modulo = max(1, n // 5)
        if i % modulo == 0 or i == n - 1:
            lx = x + bar_width / 2
            labels.append(f'<text x="{lx:.0f}" y="{height - 2}" font-size="8" fill="var(--dim)" text-anchor="middle" font-family="var(--sans)">{lbl}</text>')
            
    y_labels = [
        f'<text x="{width - 4}" y="{padding_top + 8}" font-size="7.5" fill="var(--dim)" font-family="var(--mono)" text-anchor="end">+${max_val:.0f}M</text>',
        f'<text x="{width - 4}" y="{zero_y - 2}" font-size="7.5" fill="var(--dim)" font-family="var(--mono)" text-anchor="end">0</text>',
        f'<text x="{width - 4}" y="{height - padding_bottom - 2}" font-size="7.5" fill="var(--dim)" font-family="var(--mono)" text-anchor="end">-${max_val:.0f}M</text>',
    ]
    
    svg = f'''
    <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
      <!-- Zero Line -->
      <line x1="0" y1="{zero_y:.1f}" x2="{width}" y2="{zero_y:.1f}" stroke="var(--border)" stroke-width="0.5"/>
      <!-- Bars -->
      {''.join(bars)}
      <!-- Labels -->
      {''.join(labels)}
      {''.join(y_labels)}
    </svg>
    '''
    return svg

def generate_winners_losers_chart(winners, losers, width=600, height=180):
    """Draw a horizontal bar chart of 5 winners and 5 losers."""
    items = winners + losers
    if not items:
        return '<div style="color:var(--dim); text-align:center; padding:15px;">No winners/losers data</div>'
        
    # Limit to 10 items total
    items = items[:10]
    
    max_val = max(abs(item.get('Change %', 0.0)) for item in items) if items else 1.0
    if max_val == 0:
        max_val = 1.0
        
    padding_left = 60
    padding_right = 60
    chart_w = width - padding_left - padding_right
    center_x = padding_left + chart_w / 2
    
    scale = (chart_w / 2) / max_val
    bar_h = 10
    bar_gap = 5
    
    svg_bars = []
    for i, item in enumerate(items):
        name = item.get('Symbol', item.get('Name', ''))
        chg = float(item.get('Change %', 0.0))
        y = 10 + i * (bar_h + bar_gap)
        
        w = abs(chg) * scale
        
        if chg >= 0:
            x = center_x
            color = STYLE_TOKENS['colors']['green']
            text_anchor = "start"
            text_x = center_x + w + 5
            label_x = center_x - 10
            label_anchor = "end"
        else:
            x = center_x - w
            color = STYLE_TOKENS['colors']['red']
            text_anchor = "end"
            text_x = center_x - w - 5
            label_x = center_x + 10
            label_anchor = "start"
            
        svg_bars.append(f'''
        <rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{bar_h}" fill="{color}" rx="1"/>
        <text x="{label_x:.1f}" y="{y + 8:.1f}" font-size="8.5" fill="var(--text)" text-anchor="{label_anchor}" font-family="var(--sans)" font-weight="600">{name}</text>
        <text x="{text_x:.1f}" y="{y + 8:.1f}" font-size="8.5" fill="var(--dim)" text-anchor="{text_anchor}" font-family="var(--mono)">{chg:+.2f}%</text>
        ''')
        
    svg = f'''
    <svg width="100%" height="{10 + len(items)*(bar_h+bar_gap) + 10}" style="display:block; overflow:visible;">
      <!-- Center Zero Line -->
      <line x1="{center_x:.1f}" y1="0" x2="{center_x:.1f}" y2="100%" stroke="var(--border)" stroke-width="0.5"/>
      {''.join(svg_bars)}
    </svg>
    '''
    return svg

def generate_correlation_matrix_svg(corr_matrix, width=500, height=400):
    """Draw a correlation matrix heatmap."""
    if not corr_matrix:
        return '<div style="color:var(--dim); text-align:center; padding:15px;">No correlation matrix data</div>'
        
    keys = list(corr_matrix.keys())
    n = len(keys)
    
    padding_left = 60
    padding_right = 10
    padding_top = 40
    padding_bottom = 20
    
    cell_w = (width - padding_left - padding_right) / n
    cell_h = (height - padding_top - padding_bottom) / n
    
    svg_cells = []
    
    # Headers
    for idx, key in enumerate(keys):
        # Column header
        col_x = padding_left + idx * cell_w + cell_w / 2
        svg_cells.append(f'<text x="{col_x:.1f}" y="{padding_top - 10}" fill="var(--dim)" font-size="10" font-weight="600" text-anchor="middle" font-family="var(--sans)">{key}</text>')
        # Row header
        row_y = padding_top + idx * cell_h + cell_h / 2 + 3
        svg_cells.append(f'<text x="{padding_left - 10}" y="{row_y:.1f}" fill="var(--dim)" font-size="10" font-weight="600" text-anchor="end" font-family="var(--sans)">{key}</text>')
        
    for r_idx, row_key in enumerate(keys):
        for c_idx, col_key in enumerate(keys):
            val = float(corr_matrix[row_key][col_key])
            
            # Color map based on correlation
            # Green for positive, Red for negative, Neutral/opacity for near 0
            abs_val = abs(val)
            if val >= 0:
                color = STYLE_TOKENS['colors']['green']
            else:
                color = STYLE_TOKENS['colors']['red']
                
            cell_x = padding_left + c_idx * cell_w
            cell_y = padding_top + r_idx * cell_h
            
            # draw cell rectangle with opacity matching the strength of correlation
            cell_opacity = max(0.04, abs_val * 0.9)
            text_color = '#ffffff' if abs_val > 0.4 else 'var(--text)'
            
            svg_cells.append(f'''
            <rect x="{cell_x + 1:.1f}" y="{cell_y + 1:.1f}" width="{cell_w - 2:.1f}" height="{cell_h - 2:.1f}" fill="{color}" opacity="{cell_opacity:.3f}" rx="2"/>
            <text x="{cell_x + cell_w/2:.1f}" y="{cell_y + cell_h/2 + 3:.1f}" fill="{text_color}" font-size="9.5" font-family="var(--mono)" font-weight="700" text-anchor="middle">{val:+.2f}</text>
            ''')
            
    svg = f'''
    <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
      {''.join(svg_cells)}
    </svg>
    '''
    return svg

def generate_cycle_heatmap_svg(heatmap, width=500, height=180):
    """Draw a monthly BTC returns heatmap table."""
    if not heatmap:
        return '<div style="color:var(--dim); text-align:center; padding:15px;">No cycle heatmap data</div>'
        
    years = sorted(list(heatmap.keys()))
    months = [str(m) for m in range(1, 13)]
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    
    padding_left = 50
    padding_right = 10
    padding_top = 30
    padding_bottom = 10
    
    cell_w = (width - padding_left - padding_right) / 12
    cell_h = (height - padding_top - padding_bottom) / len(years)
    
    svg_cells = []
    
    # Month Headers
    for idx, name in enumerate(month_names):
        col_x = padding_left + idx * cell_w + cell_w / 2
        svg_cells.append(f'<text x="{col_x:.1f}" y="{padding_top - 8}" fill="var(--dim)" font-size="9" text-anchor="middle" font-family="var(--sans)">{name}</text>')
        
    for r_idx, year in enumerate(years):
        # Year Header
        row_y = padding_top + r_idx * cell_h + cell_h / 2 + 3
        svg_cells.append(f'<text x="{padding_left - 10}" y="{row_y:.1f}" fill="var(--text)" font-size="10" font-weight="600" text-anchor="end" font-family="var(--sans)">{year}</text>')
        
        for c_idx, month in enumerate(months):
            val = heatmap[year].get(month)
            cell_x = padding_left + c_idx * cell_w
            cell_y = padding_top + r_idx * cell_h
            
            if val is None:
                svg_cells.append(f'<rect x="{cell_x + 1:.1f}" y="{cell_y + 1:.1f}" width="{cell_w - 2:.1f}" height="{cell_h - 2:.1f}" fill="rgba(255,255,255,0.02)" stroke="var(--border)" stroke-width="0.5" rx="1"/>')
            else:
                abs_val = abs(val)
                # Cap scaling color at 30% monthly return
                pct_scale = min(1.0, abs_val / 30.0)
                if val >= 0:
                    color = STYLE_TOKENS['colors']['green']
                else:
                    color = STYLE_TOKENS['colors']['red']
                opacity = max(0.08, pct_scale * 0.9)
                text_color = '#ffffff' if pct_scale > 0.4 else 'var(--text)'
                
                # Check if it is the current month
                now = datetime.now()
                is_current = (now.year == int(year) and now.month == int(month))
                border_attr = 'stroke="var(--gold)" stroke-width="1.5"' if is_current else 'stroke="none"'
                star_suffix = '*' if is_current else ''
                
                svg_cells.append(f'''
                <rect x="{cell_x + 1:.1f}" y="{cell_y + 1:.1f}" width="{cell_w - 2:.1f}" height="{cell_h - 2:.1f}" fill="{color}" opacity="{opacity:.3f}" {border_attr} rx="1"/>
                <text x="{cell_x + cell_w/2:.1f}" y="{cell_y + cell_h/2 + 3:.1f}" fill="{text_color}" font-size="8.5" font-family="var(--mono)" font-weight="700" text-anchor="middle">{val:+.1f}%{star_suffix}</text>
                ''')
                
    svg = f'''
    <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
      {''.join(svg_cells)}
    </svg>
    '''
    return svg

def generate_fear_greed_gauge_svg(value, label, width=400, height=240):
    """Generate an SVG speedometer gauge for the Crypto Fear & Greed Index."""
    cx, cy = width / 2, height - 60  # center of the arc
    radius = 110
    inner_radius = 90
    tick_outer = radius + 6
    tick_inner = radius - 3
    label_radius = radius + 22

    # Angle mapped to value (0=180°, 100=0°)
    needle_angle = 180 - (value / 100) * 180

    def polar(angle_deg, r):
        rad = math.radians(angle_deg)
        return cx + r * math.cos(rad), cy - r * math.sin(rad)

    segments = [
        (0, 25, '#ef4444', '#f87171'),     # Extreme Fear
        (25, 45, '#f87171', '#fbbf24'),     # Fear
        (45, 55, '#fbbf24', '#facc15'),     # Neutral
        (55, 75, '#4ade80', '#22c55e'),     # Greed
        (75, 100, '#22c55e', '#10b981'),    # Extreme Greed
    ]

    arc_paths = []
    for seg_start, seg_end, color1, color2 in segments:
        a1 = 180 - (seg_start / 100) * 180
        a2 = 180 - (seg_end / 100) * 180
        x1, y1 = polar(a1, radius)
        x2, y2 = polar(a2, radius)
        x1i, y1i = polar(a1, inner_radius)
        x2i, y2i = polar(a2, inner_radius)
        large = 1 if abs(a1 - a2) > 180 else 0
        arc_paths.append(
            f'<path d="M {x1:.1f},{y1:.1f} A {radius},{radius} 0 {large},1 {x2:.1f},{y2:.1f} '
            f'L {x2i:.1f},{y2i:.1f} A {inner_radius},{inner_radius} 0 {large},0 {x1i:.1f},{y1i:.1f} Z" '
            f'fill="{color1}" opacity="0.8"/>'
        )

    ticks_svg = []
    for i in range(0, 101, 10):
        angle = 180 - (i / 100) * 180
        x1t, y1t = polar(angle, tick_inner)
        x2t, y2t = polar(angle, tick_outer)
        ticks_svg.append(f'<line x1="{x1t:.1f}" y1="{y1t:.1f}" x2="{x2t:.1f}" y2="{y2t:.1f}" stroke="var(--border)" stroke-width="1.5"/>')

    # Needle
    needle_rad = math.radians(needle_angle)
    tip_x = cx + (inner_radius - 8) * math.cos(needle_rad)
    tip_y = cy - (inner_radius - 8) * math.sin(needle_rad)
    base_offset = 6
    perp_rad = needle_rad + math.pi / 2
    b1x = cx + base_offset * math.cos(perp_rad)
    b1y = cy - base_offset * math.sin(perp_rad)
    b2x = cx - base_offset * math.cos(perp_rad)
    b2y = cy + base_offset * math.sin(perp_rad)

    # Needle color based on value
    if value <= 25:
        needle_color = '#ef4444'
    elif value <= 45:
        needle_color = '#f87171'
    elif value <= 55:
        needle_color = '#fbbf24'
    elif value <= 75:
        needle_color = '#4ade80'
    else:
        needle_color = '#10b981'

    needle_svg = (
        f'<polygon points="{tip_x:.1f},{tip_y:.1f} {b1x:.1f},{b1y:.1f} {b2x:.1f},{b2y:.1f}" fill="{needle_color}" opacity="0.95"/>'
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="{needle_color}"/>'
    )

    svg = f'''
    <svg viewBox="0 0 {width} {height}" width="200" height="120" xmlns="http://www.w3.org/2000/svg" style="overflow:visible; display:block; margin:0 auto;">
      {''.join(arc_paths)}
      {''.join(ticks_svg)}
      {needle_svg}
      <text x="{cx}" y="{cy - 10}" text-anchor="middle" fill="var(--text)" font-family="var(--mono)" font-size="34" font-weight="700">{value}</text>
      <text x="{cx}" y="{cy + 15}" text-anchor="middle" fill="var(--dim)" font-family="var(--sans)" font-size="12" font-weight="600" letter-spacing="0.5">{label.upper()}</text>
    </svg>
    '''
    return svg

def generate_coinbase_premium_chart(trend, current, width=600, height=140):
    """Generate the Coinbase Premium SVG bar chart."""
    if not trend:
        return '<div style="color:var(--dim); text-align:center; padding:15px;">No Coinbase Premium data available</div>'

    values = [d['value'] for d in trend]
    min_val = min(values)
    max_val = max(values)
    abs_max = max(abs(min_val), abs(max_val), 0.001)

    padding_top = 10
    padding_bottom = 20
    chart_height = height - padding_top - padding_bottom
    zero_y = padding_top + chart_height / 2

    scale = (chart_height / 2) / abs_max if abs_max > 0 else 1

    n = len(trend)
    bar_gap = 1
    bar_width = max(1, (width - (n - 1) * bar_gap) / n)

    bars_svg = []
    for i, d in enumerate(trend):
        val = d['value']
        x = i * (bar_width + bar_gap)
        bar_h = abs(val) * scale
        bar_h = max(0.5, min(bar_h, chart_height / 2))

        if val >= 0:
            bar_y = zero_y - bar_h
            color = STYLE_TOKENS['colors']['green']
        else:
            bar_y = zero_y
            color = STYLE_TOKENS['colors']['red']

        bars_svg.append(f'<rect x="{x:.1f}" y="{bar_y:.1f}" width="{bar_width:.1f}" height="{bar_h:.1f}" fill="{color}" rx="0.5"/>')

    # X-axis time labels
    time_labels_svg = []
    label_count = min(6, n)
    
    # Auto-detect resolution (daily if time delta between bars > 12 hours)
    is_daily = False
    if len(trend) >= 2:
        diff = (trend[1]['time'] - trend[0]['time']).total_seconds()
        if diff > 12 * 3600:
            is_daily = True
            
    for j in range(label_count):
        idx = int(j * (n - 1) / max(label_count - 1, 1))
        t = trend[idx]['time']
        if is_daily:
            time_str = t.strftime('%d %b') if hasattr(t, 'strftime') else str(t)
        else:
            time_str = t.strftime('%H:%M') if hasattr(t, 'strftime') else str(t)
        lx = idx * (bar_width + bar_gap) + bar_width / 2
        time_labels_svg.append(
            f'<text x="{lx:.0f}" y="{height - 2}" font-size="8" fill="var(--dim)" font-family="var(--mono)" text-anchor="middle">{time_str}</text>'
        )

    # Y-axis labels
    y_labels_svg = [
        f'<text x="{width - 4}" y="{padding_top + 8}" font-size="7.5" fill="var(--dim)" font-family="var(--mono)" text-anchor="end">{abs_max:+.3f}%</text>',
        f'<text x="{width - 4}" y="{zero_y - 2}" font-size="7.5" fill="var(--dim)" font-family="var(--mono)" text-anchor="end">0</text>',
        f'<text x="{width - 4}" y="{height - padding_bottom - 2}" font-size="7.5" fill="var(--dim)" font-family="var(--mono)" text-anchor="end">{-abs_max:+.3f}%</text>',
    ]

    svg = f'''
    <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
      <line x1="0" y1="{zero_y:.0f}" x2="{width}" y2="{zero_y:.0f}" stroke="var(--border)" stroke-width="0.5"/>
      {''.join(bars_svg)}
      {''.join(time_labels_svg)}
      {''.join(y_labels_svg)}
    </svg>
    '''
    return svg

def generate_ytd_comparison_chart(data, width=600, height=200):
    """Draw a YTD performance line chart comparing BTC, NDX, Gold."""
    if not data or not any(data.values()):
        return '<div style="color:var(--dim); text-align:center; padding:20px;">No YTD comparison data available</div>'
        
    padding_left = 50
    padding_right = 20
    padding_top = 20
    padding_bottom = 30
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom
    
    # Calculate min/max value across all series to scale y-axis
    all_vals = []
    for series in data.values():
        if series:
            all_vals.extend([s['value'] for s in series])
            
    if not all_vals:
        return '<div style="color:var(--dim); text-align:center; padding:20px;">No YTD comparison data available</div>'
        
    min_val = min(all_vals)
    max_val = max(all_vals)
    diff = max_val - min_val if max_val != min_val else 1.0
    min_val -= diff * 0.05
    max_val += diff * 0.05
    diff = max_val - min_val
    
    colors = {
        'BTC': STYLE_TOKENS['colors']['gold'],
        'NDX': STYLE_TOKENS['colors']['accent'],
        'GOLD': STYLE_TOKENS['colors']['dim']
    }
    
    lines_svg = []
    legends = []
    
    # Grid ticks
    y_ticks = []
    for k in range(5):
        val = min_val + (k / 4) * diff
        ly = padding_top + chart_h - (k / 4) * chart_h
        y_ticks.append(f'''
        <line x1="{padding_left}" y1="{ly:.1f}" x2="{width - padding_right}" y2="{ly:.1f}" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.3"/>
        <text x="{padding_left - 8}" y="{ly + 3:.1f}" fill="var(--dim)" font-size="9" text-anchor="end" font-family="var(--mono)">{val:+.1f}%</text>
        ''')
        
    # X labels
    x_labels = []
    
    for name, series in data.items():
        if not series or len(series) < 2:
            continue
            
        points = []
        n = len(series)
        for i, item in enumerate(series):
            val = item['value']
            x = padding_left + (i / (n - 1)) * chart_w
            y = padding_top + chart_h - ((val - min_val) / diff) * chart_h
            points.append(f"{x:.1f},{y:.1f}")
            
        path_d = f"M {points[0]} " + " ".join([f"L {p}" for p in points[1:]])
        lines_svg.append(f'<path d="{path_d}" fill="none" stroke="{colors.get(name, "#fff")}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
        
        # Add legend item
        legends.append(f'''
        <span style="display:inline-flex; align-items:center; gap:6px; margin-right:16px; font-size:10px; font-weight:600;">
          <span style="width:10px; height:3px; background:{colors.get(name, "#fff")}; display:inline-block; border-radius:1px;"></span>
          {name} (YTD: {series[-1]["value"]:+.1f}%)
        </span>''')
        
        # Populate x_labels once
        if not x_labels:
            label_indices = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
            for idx in label_indices:
                dt = series[idx]['date']
                try:
                    parsed = datetime.strptime(dt, "%Y-%m-%d")
                    lbl = parsed.strftime("%b")
                except:
                    lbl = dt
                lx = padding_left + (idx / (n - 1)) * chart_w
                x_labels.append(f'<text x="{lx:.1f}" y="{height - 8}" fill="var(--dim)" font-size="9" text-anchor="middle" font-family="var(--sans)">{lbl}</text>')

    svg = f'''
    <div class="sparkline-wrap" style="padding:20px 24px; margin-bottom:24px;">
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
        <div style="font-size:12px; color:var(--text); font-weight:600;">BTC vs NDX vs GOLD (YTD Performance)</div>
        <div style="color:var(--text);">{ ' '.join(legends) }</div>
      </div>
      <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
        {''.join(y_ticks)}
        {''.join(lines_svg)}
        {''.join(x_labels)}
        <line x1="{padding_left}" y1="{padding_top + chart_h}" x2="{width - padding_right}" y2="{padding_top + chart_h}" stroke="var(--border)" stroke-width="1"/>
      </svg>
    </div>
    '''
    return svg

def generate_stablecoin_mcap_share_chart(history, width=600, height=200):
    """Draw a 3-year stablecoin supply (left axis) and USDT vs USDC share (right axis) chart."""
    if not history or len(history) < 2:
        return '<div style="color:var(--dim); text-align:center; padding:20px;">No historical stablecoin data available</div>'
        
    totals = [h['total'] for h in history]
    usdt_shares = [h['usdt_share'] for h in history]
    usdc_shares = [h['usdc_share'] for h in history]
    
    min_tot, max_tot = min(totals), max(totals)
    diff_tot = max_tot - min_tot if max_tot != min_tot else 1.0
    min_tot -= diff_tot * 0.05
    max_tot += diff_tot * 0.05
    diff_tot = max_tot - min_tot
    
    # Share limits (0% to 100%)
    min_sh, max_sh = 0.0, 100.0
    diff_sh = 100.0
    
    padding_left = 50
    padding_right = 50
    padding_top = 20
    padding_bottom = 30
    
    chart_w = width - padding_left - padding_right
    chart_h = height - padding_top - padding_bottom
    
    n = len(history)
    pts_tot = []
    pts_usdt = []
    pts_usdc = []
    
    for i, h in enumerate(history):
        x = padding_left + (i / (n - 1)) * chart_w
        
        y_tot = padding_top + chart_h - ((h['total'] - min_tot) / diff_tot) * chart_h
        y_usdt = padding_top + chart_h - ((h['usdt_share'] - min_sh) / diff_sh) * chart_h
        y_usdc = padding_top + chart_h - ((h['usdc_share'] - min_sh) / diff_sh) * chart_h
        
        pts_tot.append(f"{x:.1f},{y_tot:.1f}")
        pts_usdt.append(f"{x:.1f},{y_usdt:.1f}")
        pts_usdc.append(f"{x:.1f},{y_usdc:.1f}")
        
    path_tot = f"M {pts_tot[0]} " + " ".join([f"L {p}" for p in pts_tot[1:]])
    path_usdt = f"M {pts_usdt[0]} " + " ".join([f"L {p}" for p in pts_usdt[1:]])
    path_usdc = f"M {pts_usdc[0]} " + " ".join([f"L {p}" for p in pts_usdc[1:]])
    
    # Left Y ticks (Total Mcap)
    y_ticks_left = []
    for k in range(4):
        val = min_tot + (k / 3) * diff_tot
        ly = padding_top + chart_h - (k / 3) * chart_h
        y_ticks_left.append(f'''
        <line x1="{padding_left}" y1="{ly:.1f}" x2="{width - padding_right}" y2="{ly:.1f}" stroke="var(--border)" stroke-width="0.5" stroke-dasharray="3,3" opacity="0.2"/>
        <text x="{padding_left - 8}" y="{ly + 3:.1f}" fill="var(--dim)" font-size="8.5" text-anchor="end" font-family="var(--mono)">${val:.1f}B</text>
        ''')
        
    # Right Y ticks (USDT/USDC shares)
    y_ticks_right = []
    for k in range(4):
        val = min_sh + (k / 3) * diff_sh
        ly = padding_top + chart_h - (k / 3) * chart_h
        y_ticks_right.append(f'''
        <text x="{width - padding_right + 8}" y="{ly + 3:.1f}" fill="var(--dim)" font-size="8.5" text-anchor="start" font-family="var(--mono)">{val:.0f}%</text>
        ''')
        
    # X labels
    x_labels = []
    label_indices = [0, n // 4, n // 2, (3 * n) // 4, n - 1]
    for idx in label_indices:
        dt = history[idx]['date']
        try:
            parsed = datetime.strptime(dt, "%Y-%m-%d")
            lbl = parsed.strftime("%b %y")
        except:
            lbl = dt
        lx = padding_left + (idx / (n - 1)) * chart_w
        x_labels.append(f'<text x="{lx:.1f}" y="{height - 8}" fill="var(--dim)" font-size="9" text-anchor="middle" font-family="var(--sans)">{lbl}</text>')

    svg = f'''
    <svg width="100%" viewBox="0 0 {width} {height}" preserveAspectRatio="none" style="display:block; overflow:visible;">
      {''.join(y_ticks_left)}
      {''.join(y_ticks_right)}
      <!-- Total Stablecoin Cap (thick blue line) -->
      <path d="{path_tot}" fill="none" stroke="{STYLE_TOKENS['colors']['accent']}" stroke-width="2.5" stroke-linecap="round"/>
      <!-- USDT Share (green line) -->
      <path d="{path_usdt}" fill="none" stroke="{STYLE_TOKENS['colors']['green']}" stroke-width="1.5" stroke-dasharray="3,2" stroke-linecap="round"/>
      <!-- USDC Share (red/amber line) -->
      <path d="{path_usdc}" fill="none" stroke="{STYLE_TOKENS['colors']['gold']}" stroke-width="1.5" stroke-dasharray="3,2" stroke-linecap="round"/>
      
      {''.join(x_labels)}
      <line x1="{padding_left}" y1="{padding_top + chart_h}" x2="{width - padding_right}" y2="{padding_top + chart_h}" stroke="var(--border)" stroke-width="1"/>
    </svg>
    '''
    return svg

