import os
from playwright.sync_api import sync_playwright

# ── Injected CSS: clean card design with high-contrast, readable text ─────────
CARD_CSS = """
* { box-sizing: border-box; margin: 0; padding: 0; }

body {
    background: #000 !important; 
    padding: 20px !important;
    margin: 0 !important;
    font-family: 'Segoe UI', system-ui, -apple-system, sans-serif !important;
}

/* Hide UI clutter */
.navLinks, .boardBanner, #header-bar, .bottomCtrl, #ctrl-top, #globalMessage,
.sideArrows, .mobileHeader, #post-moderation-fields, .navLinksBot, #blotter, hr { 
    display: none !important; 
}

/* The card itself */
.highlight-card {
    display: block !important;
    width: 460px;
    background: #111 !important; 
    border: 1px solid #333 !important; 
    border-radius: 16px !important;
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0,0,0,0.8) !important;
    padding: 0 !important;
    margin: 0 auto !important; 
}

/* Top bar mimicking an app header */
.highlight-card::before {
    content: '';
    display: block;
    height: 4px;
    background: linear-gradient(90deg, #ff6b35, #f7c59f);
    border-radius: 16px 16px 0 0;
}

/* --- STRIP 4CHAN'S NATIVE REPLY STYLING --- */
.highlight-card .post {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    margin: 0 !important;
    padding: 0 !important;
    display: block !important; 
}

.highlight-card .postInfo {
    display: flex !important;
    align-items: center;
    gap: 8px;
    padding: 14px 18px 6px !important;
    font-size: 13px !important;
    color: #eee !important; 
    border-bottom: 1px solid #252525;
}

.highlight-card .nameBlock { color: #fff !important; }
.highlight-card .dateTime  { color: #ddd !important; font-size: 12px !important; }

/* Hide file info text (e.g., 'image.jpg 50KB'), but KEEP the actual image */
.highlight-card .fileInfo,
.highlight-card .postMenu,
.highlight-card .backlink,
.highlight-card .mobilePostControls,
.highlight-card a.quotelink { display: none !important; }

/* --- NEW: Style the Image for Modern Cards --- */
.highlight-card .file {
    display: block !important;
    margin: 15px 18px 0 18px !important;
}
.highlight-card .fileThumb {
    display: block !important;
    float: none !important; /* Stops the text from wrapping around the image */
    text-align: center !important;
    margin: 0 auto !important;
}
.highlight-card .fileThumb img {
    max-width: 100% !important;
    height: auto !important;
    border-radius: 8px !important; /* Nice rounded corners for the meme */
}

/* The actual post text */
.highlight-card .postMessage,
.highlight-card blockquote {
    display: block !important;
    padding: 14px 18px 18px !important;
    font-size: 19px !important;
    line-height: 1.55 !important;
    color: #fff !important; 
    word-break: break-word;
    white-space: pre-wrap;
}

/* Greentext */
.highlight-card .quote { color: #8fef8f !important; }
"""


def _do_capture(page, post_id, replacement_text, output_path, hide_image=False):
    """Internal: isolate and screenshot a single post on an already-loaded page."""
    selector = f"#pc{post_id}"

    # Isolate the target post and force it visible regardless of page CSS
    page.evaluate(f"""
        const el = document.querySelector('{selector}');
        if (el) {{
            el.classList.add('highlight-card');
            el.style.cssText += '; display:block !important; visibility:visible !important; opacity:1 !important;';
            document.querySelectorAll('.postContainer').forEach(p => {{
                if (p !== el) p.style.display = 'none';
            }});
            if ({'true' if hide_image else 'false'}) {{
                const fileEl = el.querySelector('.file');
                if (fileEl) fileEl.style.display = 'none';
            }}
        }}
    """)

    # Inject censored text
    if replacement_text:
        safe = (
            replacement_text
            .replace("\\", "\\\\")
            .replace("'", "\\'")
            .replace("\n", "<br>")
        )
        page.evaluate(f"""
            const msg = document.querySelector('{selector} .postMessage')
                     || document.querySelector('{selector} blockquote');
            if (msg) msg.innerHTML = '{safe}';
        """)

    # Let the layout settle after our DOM surgery and image loading
    page.wait_for_timeout(800)

    # Get bounding box via JS — bypasses all playwright visibility checks
    bbox = page.evaluate("""
        (() => {
            const el = document.querySelector('""" + selector + """');
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { x: r.left, y: r.top, width: r.width, height: r.height };
        })()
    """)

    if not bbox or bbox["width"] == 0 or bbox["height"] == 0:
        return False

    # Expand viewport so the element is never clipped
    page.set_viewport_size({
        "width":  max(500, int(bbox["x"] + bbox["width"])  + 20),
        "height": max(200, int(bbox["y"] + bbox["height"]) + 20),
    })

    page.screenshot(
        path=output_path,
        clip={
            "x":      bbox["x"],
            "y":      bbox["y"],
            "width":  bbox["width"],
            "height": bbox["height"],
        },
        scale="device",
    )
    return True


def capture_post(board: str, thread_id: int, post_id: int,
                 output_path: str, replacement_text: str | None = None, hide_image: bool = False):
    """
    Navigates to the thread, isolates a single post as a styled card,
    injects censored text if provided, and screenshots it.
    Launches its own browser — use capture_posts_batch() for multiple posts.
    """
    url = f"https://boards.4chan.org/{board}/thread/{thread_id}"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 500, "height": 900},
            device_scale_factor=2,
        )
        page = context.new_page()

        # We ONLY block ads now. Images are allowed to load!
        page.route("**/ads/**", lambda r: r.abort())

        # Changed to "load" to ensure images finish downloading before screenshotting
        page.goto(url, wait_until="load", timeout=30_000)
        page.add_style_tag(content=CARD_CSS)

        success = _do_capture(page, post_id, replacement_text, output_path, hide_image)
        if not success:
            raise RuntimeError(
                f"Could not get bounding box for post {post_id} — element may not exist in thread."
            )

        browser.close()


def capture_posts_batch(board: str, thread_id: int, posts: list,
                        output_dir: str = "temp", progress_callback=None):
    """
    Captures screenshots of multiple posts using a SINGLE browser instance.
    Significantly faster than calling capture_post() for each post individually,
    as the Chromium process is only launched once.

    Args:
        board: 4chan board name (e.g. 'g')
        thread_id: thread number
        posts: list of dicts with 'id' and optional 'text' keys
        output_dir: directory to save screenshots
        progress_callback: optional fn(completed: int, total: int) for progress

    Returns:
        list of (index, img_path) tuples for successful captures
    """
    url = f"https://boards.4chan.org/{board}/thread/{thread_id}"
    os.makedirs(output_dir, exist_ok=True)
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        for idx, post in enumerate(posts):
            post_id = post["id"]
            replacement_text = post.get("text")
            hide_image = post.get("hide_image", False)
            img_path = os.path.join(output_dir, f"post_{post_id}.png")

            try:
                context = browser.new_context(
                    viewport={"width": 500, "height": 900},
                    device_scale_factor=2,
                )
                page = context.new_page()
                page.route("**/ads/**", lambda r: r.abort())
                page.goto(url, wait_until="load", timeout=30_000)
                page.add_style_tag(content=CARD_CSS)

                success = _do_capture(page, post_id, replacement_text, img_path, hide_image)
                if success:
                    results.append((idx, img_path))
                else:
                    print(f"  [Screenshot] Warning: Could not capture post {post_id}")

                context.close()

            except Exception as e:
                print(f"  [Screenshot] Error capturing post {post_id}: {e}")
                try:
                    context.close()
                except Exception:
                    pass

            if progress_callback:
                progress_callback(idx + 1, len(posts))

        browser.close()

    return results