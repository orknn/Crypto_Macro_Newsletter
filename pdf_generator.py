import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, HRFlowable
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import urllib.request

# ── Theme Colors (Vivid Navy) ──
NAVY_BG = colors.HexColor('#1a2980')         # Vivid navy blue page bg
CARD_BG = colors.HexColor('#1e3a8a')         # Slightly lighter navy for cards
TEXT_WHITE = colors.HexColor('#f0f0f0')      # Bright white text
TEXT_MUTED = colors.HexColor('#b0c4de')      # Light steel blue for muted text
ACCENT_GOLD = colors.HexColor('#f0b90b')     # Gold accents
ACCENT_BLUE = colors.HexColor('#60a5fa')     # Light blue accents
TABLE_HEADER_BG = colors.HexColor('#0f1d5e') # Deep navy for table header
TABLE_ROW_EVEN = colors.HexColor('#162670')  # Navy for even rows
TABLE_ROW_ODD = colors.HexColor('#1e3a8a')   # Slightly lighter for odd rows
DIVIDER_COLOR = colors.HexColor('#3b5bdb')   # Medium blue divider
GREEN = colors.HexColor('#16c784')
RED = colors.HexColor('#ea3943')

def setup_fonts():
    font_path = "Roboto-Regular.ttf"
    bold_font_path = "Roboto-Bold.ttf"
    try:
        if not os.path.exists(font_path):
            urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf", font_path)
        if not os.path.exists(bold_font_path):
            urllib.request.urlretrieve("https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf", bold_font_path)
        
        pdfmetrics.registerFont(TTFont('Roboto', font_path))
        pdfmetrics.registerFont(TTFont('Roboto-Bold', bold_font_path))
        pdfmetrics.registerFontFamily('Roboto', normal='Roboto', bold='Roboto-Bold', italic='Roboto', boldItalic='Roboto-Bold')
        return True
    except Exception as e:
        print(f"Failed to setup fonts: {e}")
        return False

def _draw_navy_background(canvas, doc):
    """Draw navy blue background on every page."""
    canvas.saveState()
    canvas.setFillColor(NAVY_BG)
    canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
    canvas.restoreState()

def _section_divider():
    """Return a styled horizontal rule."""
    return HRFlowable(width="100%", thickness=1, color=DIVIDER_COLOR, spaceAfter=10, spaceBefore=5)

def _color_pct(val, font_name_bold):
    """Return colored percentage string for tables."""
    if val is None:
        return '0.00%'
    color = '#16c784' if val >= 0 else '#ea3943'
    sign = '+' if val >= 0 else ''
    return f'<font color="{color}"><b>{sign}{val:.2f}%</b></font>'


def generate_newsletter_pdf(data, chart_paths, output_filename='sample_newsletter.pdf'):
    """
    Generate the daily crypto & macro newsletter PDF with navy blue theme.
    """
    fonts_ready = setup_fonts()
    font_name = 'Roboto' if fonts_ready else 'Helvetica'
    font_name_bold = 'Roboto-Bold' if fonts_ready else 'Helvetica-Bold'

    doc = SimpleDocTemplate(
        output_filename, pagesize=A4,
        rightMargin=35, leftMargin=35, topMargin=35, bottomMargin=35
    )
    styles = getSampleStyleSheet()
    
    # ── Custom Styles ──
    brand_style = ParagraphStyle(
        name='BrandStyle', parent=styles['Heading1'],
        fontName=font_name_bold, fontSize=22, spaceAfter=2,
        alignment=1, textColor=ACCENT_GOLD
    )
    title_style = ParagraphStyle(
        name='TitleStyle', parent=styles['Heading1'],
        fontName=font_name_bold, fontSize=14, spaceAfter=4,
        alignment=1, textColor=TEXT_WHITE
    )
    subtitle_style = ParagraphStyle(
        name='SubtitleStyle', parent=styles['Normal'],
        fontName=font_name, fontSize=10, spaceAfter=12,
        alignment=1, textColor=TEXT_MUTED
    )
    header_style = ParagraphStyle(
        name='HeaderStyle', parent=styles['Heading2'],
        fontName=font_name_bold, fontSize=13, spaceAfter=8,
        spaceBefore=4, textColor=ACCENT_BLUE
    )
    subheader_style = ParagraphStyle(
        name='SubHeaderStyle', parent=styles['Heading3'],
        fontName=font_name_bold, fontSize=11, spaceAfter=6,
        spaceBefore=4, textColor=ACCENT_GOLD
    )
    body_style = ParagraphStyle(
        name='BodyStyle', parent=styles['Normal'],
        fontName=font_name, fontSize=10, spaceAfter=6, leading=14,
        textColor=TEXT_WHITE
    )
    bullet_style = ParagraphStyle(
        name='BulletStyle', parent=styles['Normal'],
        fontName=font_name, fontSize=9.5, spaceAfter=4, leading=13,
        textColor=TEXT_WHITE, leftIndent=15
    )
    
    story = []
    
    # ═══════════════════════════════════════════
    # HEADER: Brand + Title
    # ═══════════════════════════════════════════
    current_date = datetime.now().strftime("%d %B %Y")
    story.append(Spacer(1, 5))
    story.append(Paragraph("Orkun Biçen", brand_style))
    story.append(Paragraph("Daily Finance Bulletin", title_style))
    story.append(Paragraph(f"Tarih: {current_date}", subtitle_style))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 1: Genel Değerlendirme (Macro Overview)
    # ═══════════════════════════════════════════
    story.append(Paragraph("1. Genel Değerlendirme", header_style))
    macro_data = data.get('macro_indicators', {})
    crypto_overview = data.get('crypto_market_overview', {})
    
    macro_narrative = (
        f"Güncel makroekonomik göstergelere bakıldığında, <b>VIX</b> endeksi {macro_data.get('VIX', 0):.2f} seviyesinde, "
        f"<b>DXY</b> (Dolar Endeksi) {macro_data.get('DXY', 0):.2f} noktasında işlem görmektedir. "
        f"<b>ABD 10 Yıllık Tahvil Getirisi</b> {macro_data.get('US 10-Year Treasury Yield', 0):.2f}% seviyesindedir. "
        f"Kripto piyasalarında toplam <b>market cap</b> ${crypto_overview.get('total_market_cap', 0)/1e12:.2f} Trilyon, "
        f"<b>BTC Dominance</b> %{crypto_overview.get('btc_dominance', 0):.1f} seviyesindedir."
    )
    story.append(Paragraph(macro_narrative, body_style))
    
    # Macro bar chart
    macro_chart = chart_paths.get('macro_bar')
    if macro_chart and os.path.exists(macro_chart):
        story.append(Spacer(1, 5))
        story.append(Image(macro_chart, width=450, height=210))
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 2: Haftalık Ekonomik Takvim (Weekly Economic Calendar)
    # ═══════════════════════════════════════════
    story.append(Paragraph("2. Haftalık Ekonomik Takvim", header_style))
    story.append(Paragraph(
        "Bu haftanın en önemli (★★★) ekonomik verileri:", body_style
    ))
    
    econ_calendar = data.get('economic_calendar', [])
    if econ_calendar:
        cal_table_data = [['Tarih', 'Saat', 'Ülke', 'Event', 'Önceki', 'Tahmin']]
        for ev in econ_calendar:
            cal_table_data.append([
                ev.get('date', ''),
                ev.get('time', ''),
                ev.get('country', ''),
                ev.get('event', ''),
                ev.get('previous', '—'),
                ev.get('forecast', '—'),
            ])
        
        cal_table = Table(cal_table_data, colWidths=[70, 40, 35, 180, 55, 55])
        cal_style = [
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GOLD),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, DIVIDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (3, 1), (3, -1), 'LEFT'),  # Event column left-aligned
        ]
        for i in range(1, len(cal_table_data)):
            bg = TABLE_ROW_EVEN if i % 2 == 0 else TABLE_ROW_ODD
            cal_style.append(('BACKGROUND', (0, i), (-1, i), bg))
        cal_table.setStyle(TableStyle(cal_style))
        story.append(cal_table)
    
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 3: Günün Öne Çıkan Verileri (Daily News & Events)
    # ═══════════════════════════════════════════
    story.append(Paragraph("3. Günün Öne Çıkan Verileri", header_style))
    news_data = data.get('macro_news', {})
    
    story.append(Paragraph("<b>Top Macro News:</b>", body_style))
    for news in news_data.get('news', []):
        story.append(Paragraph(f"▸ {news}", bullet_style))
         
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>Daily Economic Calendar:</b>", body_style))
    for event in news_data.get('events', [])[:3]:
        story.append(Paragraph(f"▸ {event['time']} — {event['event']}", bullet_style))
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 4: Piyasa Grafikleri (Market Charts)
    # ═══════════════════════════════════════════
    story.append(Paragraph("4. Piyasa Grafikleri", header_style))
    
    # Crypto market overview chart (Total, Total3, BTC Dom, Stablecoin Dom)
    crypto_chart = chart_paths.get('crypto_market')
    if crypto_chart and os.path.exists(crypto_chart):
        story.append(Image(crypto_chart, width=480, height=130))
        story.append(Spacer(1, 8))
    
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 5: Varlık Özeti (Categorized Asset Summary)
    # ═══════════════════════════════════════════
    story.append(Paragraph("5. Varlık Özeti", header_style))
    
    # ── 5a. Magnificent 7 ──
    story.append(Paragraph("Magnificent 7 (NASDAQ)", subheader_style))
    mag7 = data.get('magnificent_7', [])
    if mag7:
        mag7_table_data = [['Symbol', 'Company', 'Price (USD)', 'Change %']]
        for stock in mag7:
            pct = stock.get('Change %', 0)
            pct_color = '#16c784' if pct >= 0 else '#ea3943'
            sign = '+' if pct >= 0 else ''
            mag7_table_data.append([
                stock['Symbol'],
                stock['Name'],
                f"${stock['Price']:,.2f}",
                f"{sign}{pct:.2f}%",
            ])
        
        mag7_t = Table(mag7_table_data, colWidths=[55, 120, 100, 75])
        mag7_style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GOLD),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, DIVIDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(1, len(mag7_table_data)):
            bg = TABLE_ROW_EVEN if i % 2 == 0 else TABLE_ROW_ODD
            mag7_style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
            # Color the change column
            pct_val = mag7[i-1].get('Change %', 0)
            pct_color = GREEN if pct_val >= 0 else RED
            mag7_style_cmds.append(('TEXTCOLOR', (3, i), (3, i), pct_color))
        mag7_t.setStyle(TableStyle(mag7_style_cmds))
        story.append(mag7_t)
    
    story.append(Spacer(1, 8))
    
    # ── 5b. Emtialar (Commodities) ──
    story.append(Paragraph("Emtialar (Commodities)", subheader_style))
    commodities = data.get('commodities', [])
    if commodities:
        com_table_data = [['Emtia', 'Price (USD)', 'Change %']]
        for com in commodities:
            pct = com.get('Change %', 0)
            sign = '+' if pct >= 0 else ''
            com_table_data.append([
                com['Name'],
                f"${com['Price']:,.2f}",
                f"{sign}{pct:.2f}%",
            ])
        
        com_t = Table(com_table_data, colWidths=[120, 130, 100])
        com_style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GOLD),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, DIVIDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(1, len(com_table_data)):
            bg = TABLE_ROW_EVEN if i % 2 == 0 else TABLE_ROW_ODD
            com_style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
            pct_val = commodities[i-1].get('Change %', 0)
            pct_color = GREEN if pct_val >= 0 else RED
            com_style_cmds.append(('TEXTCOLOR', (2, i), (2, i), pct_color))
        com_t.setStyle(TableStyle(com_style_cmds))
        story.append(com_t)
    
    story.append(Spacer(1, 8))
    
    # ── 5c. Crypto Sentiment Indicators ──
    story.append(Paragraph("Crypto Sentiment", subheader_style))
    fng = data.get('fear_and_greed', {})
    cb_premium = data.get('coinbase_premium', {})
    
    sentiment_text = (
        f"<b>Fear &amp; Greed Index:</b> {fng.get('value', 0)} — "
        f"<i>{fng.get('classification', 'N/A')}</i> &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Coinbase Premium:</b> {cb_premium.get('current_value', 0):.4f}%"
    )
    story.append(Paragraph(sentiment_text, body_style))
    
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 6: Market Sentiment & Derivatives (+ gauge chart)
    # ═══════════════════════════════════════════
    story.append(Paragraph("6. Market Sentiment &amp; Derivatives", header_style))
    fng = data.get('fear_and_greed', {})
    funding = data.get('funding_rates', {})
    crypto_ov = data.get('crypto_market_overview', {})
    
    sentiment_narrative = (
        f"Kripto piyasalarındaki güncel duygu durumu (<b>Crypto Fear &amp; Greed Index</b>) "
        f"{fng.get('value', 0)} puan ile '<b>{fng.get('classification', 'N/A')}</b>' bölgesinde bulunmaktadır. "
        f"<b>BTC Dominance</b> {crypto_ov.get('btc_dominance', 0):.1f}%, "
        f"<b>ETH Dominance</b> {crypto_ov.get('eth_dominance', 0):.1f}% seviyesindedir. "
        f"Toplam kripto piyasa değeri ${crypto_ov.get('total_market_cap', 0)/1e12:.2f} Trilyon USD olarak kaydedilmiştir."
    )
    story.append(Paragraph(sentiment_narrative, body_style))
    
    # Fear & Greed gauge
    fg_chart = chart_paths.get('fear_greed')
    if fg_chart and os.path.exists(fg_chart):
        story.append(Spacer(1, 5))
        story.append(Image(fg_chart, width=320, height=200))
    
    story.append(Spacer(1, 5))
    funding_text = (
        f"Türev piyasalarındaki başlıca varlıkların <b>funding rates</b> verileri: "
        f"BTC <b>{funding.get('BTC', 0):.4f}%</b>, ETH <b>{funding.get('ETH', 0):.4f}%</b>, "
        f"SOL <b>{funding.get('SOL', 0):.4f}%</b>. <b>Market volatility</b> yakından izlenmelidir."
    )
    story.append(Paragraph(funding_text, body_style))
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 7: Bitcoin Status & Coinbase Premium (+ chart)
    # ═══════════════════════════════════════════
    story.append(Paragraph("7. Bitcoin Status &amp; Coinbase Premium Index", header_style))
    btc_data = data.get('coinbase_premium', {})
    narrative_btc = (
        f"Bitcoin'in mevcut görünümüne baktığımızda, <b>support level</b> "
        f"{btc_data.get('btc_support_level', 0):,.2f} USD seviyesinde izlenirken, "
        f"<b>resistance level</b> {btc_data.get('btc_resistance_level', 0):,.2f} USD bölgesinde zorlanmaktadır. "
        f"Kurumsal Amerikan talebini yansıtan Coinbase Premium Index şu an "
        f"{btc_data.get('current_value', 0):.4f}% seviyesindedir."
    )
    story.append(Paragraph(narrative_btc, body_style))
    
    cb_chart = chart_paths.get('coinbase_premium')
    if cb_chart and os.path.exists(cb_chart):
        story.append(Spacer(1, 5))
        story.append(Image(cb_chart, width=450, height=190))
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 8: Crypto ETF Inflows / Outflows
    # ═══════════════════════════════════════════
    story.append(Paragraph("8. Crypto ETF Inflows / Outflows", header_style))
    etf_data = data.get('etf_flows', {})
    
    net_flow = etf_data.get('net_flow', 0)
    flow_color = '#16c784' if net_flow >= 0 else '#ea3943'
    flow_sign = '+' if net_flow >= 0 else ''
    
    narrative_etf = (
        f"Dün gerçekleşen ETF hareketlerinde toplam <b>net inflow</b> "
        f"{etf_data.get('total_net_inflow', 0):.2f}M USD, "
        f"toplam <b>net outflow</b> {abs(etf_data.get('total_net_outflow', 0)):.2f}M USD. "
        f"<font color=\"{flow_color}\"><b>Net: {flow_sign}{net_flow:.2f}M USD</b></font>"
    )
    story.append(Paragraph(narrative_etf, body_style))
    
    # ETF breakdown table
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>Bitcoin ETF Breakdown:</b>", body_style))
    btc_etfs = etf_data.get('btc_etfs', [])
    if btc_etfs:
        etf_table_data = [['ETF', 'Flow (M USD)']]
        for etf in btc_etfs:
            flow = etf['flow_m']
            sign = '+' if flow >= 0 else ''
            etf_table_data.append([
                etf['name'],
                f"{sign}{flow:.2f}M",
            ])
        etf_t = Table(etf_table_data, colWidths=[200, 150])
        etf_style = [
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GOLD),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, DIVIDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(1, len(etf_table_data)):
            bg = TABLE_ROW_EVEN if i % 2 == 0 else TABLE_ROW_ODD
            etf_style.append(('BACKGROUND', (0, i), (-1, i), bg))
            flow_val = btc_etfs[i-1]['flow_m']
            fc = GREEN if flow_val >= 0 else RED
            etf_style.append(('TEXTCOLOR', (1, i), (1, i), fc))
        etf_t.setStyle(TableStyle(etf_style))
        story.append(etf_t)
    
    story.append(Spacer(1, 5))
    story.append(Paragraph("<b>Ethereum ETF Breakdown:</b>", body_style))
    eth_etfs = etf_data.get('eth_etfs', [])
    if eth_etfs:
        eth_etf_table_data = [['ETF', 'Flow (M USD)']]
        for etf in eth_etfs:
            flow = etf['flow_m']
            sign = '+' if flow >= 0 else ''
            eth_etf_table_data.append([
                etf['name'],
                f"{sign}{flow:.2f}M",
            ])
        eth_t = Table(eth_etf_table_data, colWidths=[200, 150])
        eth_style = [
            ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
            ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GOLD),
            ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_WHITE),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
            ('FONTNAME', (0, 1), (-1, -1), font_name),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8.5),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
            ('TOPPADDING', (0, 1), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
            ('GRID', (0, 0), (-1, -1), 0.5, DIVIDER_COLOR),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        for i in range(1, len(eth_etf_table_data)):
            bg = TABLE_ROW_EVEN if i % 2 == 0 else TABLE_ROW_ODD
            eth_style.append(('BACKGROUND', (0, i), (-1, i), bg))
            flow_val = eth_etfs[i-1]['flow_m']
            fc = GREEN if flow_val >= 0 else RED
            eth_style.append(('TEXTCOLOR', (1, i), (1, i), fc))
        eth_t.setStyle(TableStyle(eth_style))
        story.append(eth_t)
    
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 9: Altcoin Watchlist
    # ═══════════════════════════════════════════
    story.append(Paragraph("9. Altcoin Watchlist", header_style))
    crypto_prices = data.get('crypto_prices', [])
    
    table_data = [['Symbol', 'Price (USD)', '24h %', '7d %']]
    for token in crypto_prices:
        price = token.get('Current Price USD')
        # Format price based on magnitude
        if price is not None:
            if price >= 100:
                price_str = f"${price:,.2f}"
            elif price >= 1:
                price_str = f"${price:,.4f}"
            else:
                price_str = f"${price:,.6f}"
        else:
            price_str = "$0.00"
        
        pct_24h = token.get('24h %', 0) or 0
        pct_7d = token.get('7d %', 0) or 0
        
        sign_24h = '+' if pct_24h >= 0 else ''
        sign_7d = '+' if pct_7d >= 0 else ''

        table_data.append([
            token['Symbol'],
            price_str,
            f"{sign_24h}{pct_24h:.2f}%",
            f"{sign_7d}{pct_7d:.2f}%",
        ])
    
    t = Table(table_data, colWidths=[65, 130, 80, 80])
    
    # Build row-alternating style
    table_style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), TABLE_HEADER_BG),
        ('TEXTCOLOR', (0, 0), (-1, 0), ACCENT_GOLD),
        ('TEXTCOLOR', (0, 1), (-1, -1), TEXT_WHITE),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), font_name_bold),
        ('FONTNAME', (0, 1), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
        ('GRID', (0, 0), (-1, -1), 0.5, DIVIDER_COLOR),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]
    # Alternating row backgrounds + colored percentages
    for i in range(1, len(table_data)):
        bg = TABLE_ROW_EVEN if i % 2 == 0 else TABLE_ROW_ODD
        table_style_cmds.append(('BACKGROUND', (0, i), (-1, i), bg))
        
        # Color 24h% column
        pct_24h = crypto_prices[i-1].get('24h %', 0) or 0
        color_24h = GREEN if pct_24h >= 0 else RED
        table_style_cmds.append(('TEXTCOLOR', (2, i), (2, i), color_24h))
        
        # Color 7d% column
        pct_7d = crypto_prices[i-1].get('7d %', 0) or 0
        color_7d = GREEN if pct_7d >= 0 else RED
        table_style_cmds.append(('TEXTCOLOR', (3, i), (3, i), color_7d))
    
    t.setStyle(TableStyle(table_style_cmds))
    story.append(t)
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ═══════════════════════════════════════════
    # SECTION 10: Token Unlocks & Burns
    # ═══════════════════════════════════════════
    story.append(Paragraph("10. Token Unlocks &amp; Token Burns", header_style))
    unlocks_data = data.get('token_unlocks', [])
    if not unlocks_data:
        story.append(Paragraph(
            "Bu hafta için izleme listesindeki varlıklarda önemli bir <b>token unlock</b> "
            "veya <b>token burn</b> beklenmiyor.", body_style))
    else:
        for ev in unlocks_data:
            story.append(Paragraph(
                f"▸ <b>{ev['symbol']}</b>: Yaklaşan <b>{ev['event']}</b> tarihi {ev['date']}. "
                f"Yaklaşık değer: {ev['amount_usd_m']:.2f}M USD.", bullet_style))
    story.append(Spacer(1, 8))
    story.append(_section_divider())
    
    # ── Footer ──
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=DIVIDER_COLOR, spaceAfter=5))
    footer_style = ParagraphStyle(
        name='FooterStyle', parent=styles['Normal'],
        fontName=font_name, fontSize=8, alignment=1,
        textColor=TEXT_MUTED
    )
    story.append(Paragraph(
        "Bu bülten otomatik olarak oluşturulmuştur. Yatırım tavsiyesi niteliği taşımamaktadır.",
        footer_style
    ))
    
    # Build with navy background on every page
    doc.build(story, onFirstPage=_draw_navy_background, onLaterPages=_draw_navy_background)
    return output_filename
