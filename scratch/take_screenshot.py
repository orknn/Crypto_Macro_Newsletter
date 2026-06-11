import os
from playwright.sync_api import sync_playwright

def take_screenshot():
    html_path = "/Users/orkunbicen/Sikik_Sikik_Fikirler/Crypto_Macro_Newsletter/daily_bulletin.html"
    output_png = "/Users/orkunbicen/.gemini/antigravity/brain/85370659-7f33-481c-b2d5-e78562c4e198/daily_bulletin_preview.png"
    
    if not os.path.exists(html_path):
        print(f"Error: {html_path} does not exist.")
        return
        
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 720, "height": 1000})
        page.goto(f"file://{os.path.abspath(html_path)}")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Wait for fonts/SVGs to render
        page.screenshot(path=output_png, full_page=True)
        browser.close()
    print(f"Screenshot saved to {output_png}")

if __name__ == "__main__":
    take_screenshot()
