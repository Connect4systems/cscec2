"""Read-only guide capture. Uses a temporary session; never stores credentials here."""
import json
import tempfile
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SITE = "https://en.connect4systems.com"
DOCTYPES = ["Tender Analysis", "Costing Note", "BOQ", "Template BOQ", "Project Offer",
            "Project Contract", "Project", "Project Budget", "CR", "Subcontractor Contract",
            "Project Clearnce", "Subcontract Clearnce", "Division", "Cost Code", "Contract Type",
            "Selling Deductions Template", "Purchasing Deductions Template", "Comparison",
            "Item Coding Request", "Subcontractor Custody"]


def main():
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=r"C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe", headless=True)
        ctx = browser.new_context(storage_state=str(Path(tempfile.gettempdir()) / "contractor-guide-session.json"), viewport={"width": 1440, "height": 1050})
        page = ctx.new_page()
        errors = []
        page.on("pageerror", lambda e: errors.append(str(e)[:300]))
        page.goto(SITE + "/app", wait_until="domcontentloaded", timeout=60000)
        page.wait_for_function("typeof frappe !== 'undefined' && frappe.boot && frappe.session.user !== 'Guest'", timeout=45000)
        for dt in DOCTYPES:
            entry = {"doctype": dt}
            try:
                response = page.evaluate("""async dt => {
                    const r = await frappe.call({method:'frappe.client.get_list',args:{doctype:dt,fields:['name'],limit_page_length:5,order_by:'modified desc'}});
                    return r.message || [];
                }""", dt)
                entry["sample_names"] = [row["name"] for row in response]
                name = response[0]["name"] if response else None
                page.evaluate("args => args.name ? frappe.set_route('Form',args.dt,args.name) : frappe.new_doc(args.dt)", {"dt": dt, "name": name})
                page.wait_for_function("dt => window.cur_frm && cur_frm.doctype === dt && cur_frm.fields_dict", arg=dt, timeout=30000)
                page.wait_for_timeout(1300)
                page.locator('.modal:visible .btn-modal-close').first.click(timeout=500) if page.locator('.modal:visible .btn-modal-close').count() else None
                slug = dt.lower().replace(' ', '-')
                file = ROOT / 'assets' / (slug + '.png')
                page.screenshot(path=str(file), full_page=False)
                entry.update({"screenshot": 'assets/' + file.name, "url": page.url, "status": "opened", "existing_record": bool(name)})
                entry['tabs'] = page.locator('.form-tabs:visible .nav-link').all_text_contents()
                for label, suffix in [("Clauses", "clauses"), ("Taxes and Totals", "taxes"), ("Contracting", "contracting"), ("Equipment", "equipment"), ("Total Budget", "totals"), ("Contract Clauses Budget", "clauses-budget"), ("Project Clauses", "progress")]:
                    loc = page.locator('.form-tabs:visible .nav-link').filter(has_text=label)
                    if loc.count() == 1:
                        loc.click(timeout=3000); page.wait_for_timeout(500)
                        tabfile = ROOT / 'assets' / (slug + '-' + suffix + '.png')
                        page.screenshot(path=str(tabfile), full_page=False)
                entry['visible_text'] = page.locator('body').inner_text()[-1400:]
            except Exception as e:
                entry.update({"status": "error", "error": str(e)[:400]})
            results.append(entry)
            (ROOT / 'site-review.json').write_text(json.dumps({'date':'2026-10-29','method':'Authenticated read-only navigation; no saved/submitted transactions','results':results,'browser_errors':errors}, ensure_ascii=False, indent=2), encoding='utf-8')
            print(dt, entry['status'], flush=True)
        browser.close()


if __name__ == '__main__':
    main()
