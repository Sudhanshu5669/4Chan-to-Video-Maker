from playwright.sync_api import sync_playwright

def capture_post(board, thread_id, post_id, output_path):
    url = f"https://boards.4chan.org/{board}/thread/{thread_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        
        # Inject custom CSS for a cleaner, darker look (optional but recommended)
        custom_css = """
        body { background-color: #1d1f21 !important; color: #c5c8c6 !important; font-size: 22px !important; }
        .post { background-color: #282a2e !important; border: 1px solid #373b41 !important; padding: 10px !important; }
        """
        page.add_style_tag(content=custom_css)
        
        # Target the specific post container
        selector = f"#pc{post_id}"
        post_element = page.locator(selector)
        
        # Save screenshot
        post_element.screenshot(path=output_path)
        browser.close()