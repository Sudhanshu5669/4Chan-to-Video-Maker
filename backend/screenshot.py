from playwright.sync_api import sync_playwright

def capture_post(board, thread_id, post_id, output_path, replacement_text=None):
    url = f"https://boards.4chan.org/{board}/thread/{thread_id}"
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Emulate a mobile phone screen for better text wrapping
        context = browser.new_context(
            viewport={'width': 400, 'height': 800},
            device_scale_factor=2, # Makes the screenshot high-resolution
            is_mobile=True
        )
        
        page = context.new_page()
        page.goto(url)
        
        # Inject CSS to remove clutter, bump font size, and force dark mode
        custom_css = """
        body { background-color: #1d1f21 !important; color: #c5c8c6 !important; font-size: 26px !important; }
        .post { background-color: #282a2e !important; border: 1px solid #373b41 !important; padding: 15px !important; width: 100% !important; box-sizing: border-box !important;}
        .postInfo { font-size: 22px !important; }
        .backlink { display: none !important; }
        """
        page.add_style_tag(content=custom_css)
        
        selector = f"#pc{post_id}"
        
        # --- THE DOM INJECTION (CENSOR FEATURE) ---
        # If the LLM provided censored text, replace the HTML content of the post
        if replacement_text:
            # Escape single quotes and newlines so the JavaScript doesn't break
            safe_text = replacement_text.replace("'", "\\'").replace('\n', '<br>')
            js_code = f"""
            var el = document.querySelector('{selector} .blockquote');
            if(el) {{ el.innerHTML = '{safe_text}'; }}
            """
            page.evaluate(js_code)
        
        post_element = page.locator(selector)
        post_element.screenshot(path=output_path)
        
        browser.close()