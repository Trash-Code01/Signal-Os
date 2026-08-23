from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        
        def handle_console(msg):
            if msg.type == 'error':
                print(f"BROWSER ERROR: {msg.text}")
                
        def handle_page_error(err):
            print(f"PAGE ERROR: {err}")
            
        page.on("console", handle_console)
        page.on("pageerror", handle_page_error)
        
        page.goto('http://localhost:3002/campaigns')
        page.wait_for_timeout(3000)
        browser.close()

run()