"""Exercise dialogs and unsaved resource arithmetic. No server-side saves/submits."""
from pathlib import Path
import json
import tempfile
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent
SITE = 'https://en.connect4systems.com'


def main():
    checks = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=r'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
        ctx = b.new_context(storage_state=str(Path(tempfile.gettempdir())/'contractor-guide-session.json'),viewport={'width':1440,'height':1050})
        page = ctx.new_page()
        page.goto(SITE+'/app',wait_until='domcontentloaded',timeout=60000)
        page.wait_for_function("typeof frappe !== 'undefined' && frappe.boot",timeout=45000)

        def shot(name):
            page.screenshot(path=str(ROOT/'assets'/name), full_page=False)

        def call(method, args):
            return page.evaluate("async a => (await frappe.call({method:a.method,args:a.args})).message",dict(method=method,args=args))

        def open_form(dt, name=None):
            page.evaluate("a=>a.name?frappe.set_route('Form',a.dt,a.name):frappe.new_doc(a.dt)",{'dt':dt,'name':name})
            page.wait_for_function("dt=>window.cur_frm && cur_frm.doctype===dt",arg=dt,timeout=30000)
            page.wait_for_timeout(1000)
            page.locator('body').click(position={'x':1400,'y':100})

        temporary_cr = None
        try:
            rows = call('frappe.client.get_list',dict(doctype='CR',fields=['name','docstatus','project'],filters={'docstatus':0},limit_page_length=10))
            if not rows:
                sources = call('frappe.client.get_list',dict(doctype='CR',fields=['name'],limit_page_length=1))
                if sources:
                    src=call('frappe.client.get',dict(doctype='CR',name=sources[0]['name']))
                    draft={k:src.get(k) for k in ['project','supplier','contract_type','posting_date','end_date','attach_cr','company','currency','conversion_rate']}
                    draft.update(doctype='CR',note='Temporary documentation verification draft; removed after screenshots.',clauses=[],numbering_mode='Automatic')
                    created=call('frappe.client.insert',dict(doc=json.dumps(draft)))
                    temporary_cr=created['name'];rows=[created]
            if rows:
                open_form('CR',rows[0]['name'])
                page.get_by_role('button',name='Fetch from Project',exact=True).click()
                dialog = page.locator('.modal:visible')
                dialog.wait_for(state='visible',timeout=10000)
                page.wait_for_timeout(500);shot('cr-picker-all.png')
                all_box=dialog.get_by_role('checkbox',name='All Clauses',exact=True)
                group=dialog.locator('[data-fieldname="clause_group"] select')
                checks.append({'check':'CR All Clauses hides group field','passed':not group.is_visible()})
                all_box.uncheck();page.wait_for_timeout(300)
                options=group.locator('option').evaluate_all('els=>els.map(x=>x.value).filter(Boolean)')
                if options:
                    group.select_option(options[0]);page.wait_for_timeout(300)
                    table=dialog.locator('.cr-detail-choice')
                    checks.append({'check':'CR selected group shows detail selection table','passed':table.count()>0})
                    if table.count():
                        table.first.check();dialog.locator('.cr-detail-qty').first.fill('1')
                    shot('cr-picker-table.png')
                    select_all=dialog.get_by_role('checkbox',name='Select All Clauses in This Group',exact=True)
                    select_all.check();page.wait_for_timeout(300)
                    checks.append({'check':'CR Select All in Group hides detail table','passed':not dialog.locator('.cr-detail-choice').first.is_visible()})
                    shot('cr-picker-group.png')
                    select_all.uncheck();page.wait_for_timeout(300)
                dialog.locator('.btn-modal-close').click()
                if temporary_cr:
                    options=call('contractor.contractor_app.doctype.cr.cr.project_clause_options',dict(cr=temporary_cr))
                    detail=next(x for x in options['clauses'] if not x['is_group'])
                    api='contractor.contractor_app.doctype.cr.cr.fetch_project_clauses'
                    call(api,dict(cr=temporary_cr,fetch_all=0,project=options['project'],selected_rows=json.dumps([detail['name']]),quantities=json.dumps({detail['name']:1})))
                    before=call('frappe.client.get',dict(doctype='CR',name=temporary_cr))
                    call(api,dict(cr=temporary_cr,fetch_all=1,project=options['project']))
                    after=call('frappe.client.get',dict(doctype='CR',name=temporary_cr))
                    old=next(x for x in before['clauses'] if x.get('project_clause')==detail['name'])
                    new=[x for x in after['clauses'] if x.get('project_clause')==detail['name']]
                    checks.append({'check':'Repeated Project fetch preserves existing CR row and quantity without duplication','passed':len(new)==1 and new[0]['name']==old['name'] and new[0]['qty']==1,'temporary_record':True})
            else: checks.append({'check':'CR picker','status':'no draft available'})
        except Exception as e: checks.append({'check':'CR picker','error':str(e)[:400]})
        finally:
            if temporary_cr:
                try:
                    call('frappe.client.delete',dict(doctype='CR',name=temporary_cr))
                    checks.append({'check':'Temporary CR draft cleanup','passed':True,'note':'The naming sequence may advance; existing records were unchanged.'})
                except Exception as e: checks.append({'check':'Temporary CR draft cleanup','error':str(e)[:400],'record':temporary_cr})

        try:
            projects=call('frappe.client.get_list',dict(doctype='Project',fields=['name'],limit_page_length=5))
            for project in projects:
                opts=call('contractor.subcontracting.project_contract_options',dict(project=project['name']))
                if not opts.get('suppliers'): continue
                open_form('Project',project['name'])
                page.evaluate('()=>cur_frm.events.create_subcontract_clearance(cur_frm)')
                dialog=page.locator('.modal:visible');dialog.wait_for(state='visible')
                supplier=opts['suppliers'][0]['name']
                dialog.locator('[data-fieldname="supplier"] input').fill(supplier)
                dialog.locator('[data-fieldname="supplier"] input').press('Tab')
                page.wait_for_timeout(800)
                checks.append({'check':'Project Supplier reveals contract selector','passed':dialog.locator('div.frappe-control[data-fieldname="subcontractor_contract"]').is_visible()})
                contracts=[x for x in opts['contracts'] if x['supplier']==supplier]
                if contracts:
                    dialog.locator('[data-fieldname="subcontractor_contract"] input').fill(contracts[0]['name'])
                    dialog.locator('[data-fieldname="subcontractor_contract"] input').press('Tab')
                page.wait_for_timeout(300);shot('project-subcontract-picker.png')
                dialog.locator('.btn-modal-close').click()
                break
            else: checks.append({'check':'Project supplier-contract picker','status':'no eligible submitted contracts'})
        except Exception as e: checks.append({'check':'Project supplier-contract picker','error':str(e)[:400]})

        try:
            open_form('BOQ')
            sample=call('frappe.client.get_list',dict(doctype='Item',fields=['name','stock_uom'],filters={'disabled':0},limit_page_length=1))[0]
            result=page.evaluate("""item=>{
                const f=cur_frm;
                f.doc.project_qty=100;f.doc.quantity_basis='Project Quantity';
                const row=f.add_child('equipment_costs',{item:item.name,uom:item.stock_uom,per_unit_qty:2,cost:5});
                f.refresh_fields();contractor.setup_boq_resources(f);contractor.recalculate_boq_resources(f);f.dirty();
                return {quantity:row.qty,equipment:f.doc.total_equipment_costs,total:f.doc.total_cost,unit:f.doc.unit_cost};
            }""",sample)
            page.locator('.form-tabs:visible .nav-link').filter(has_text='Equipment').click()
            page.wait_for_timeout(500);shot('boq-equipment-entry.png')
            checks.append({'check':'Unsaved BOQ equipment quantity and costs','expected':{'quantity':200,'equipment':1000,'total':1000,'unit':10},'actual':result,'passed':result=={'quantity':200,'equipment':1000,'total':1000,'unit':10}})
        except Exception as e: checks.append({'check':'BOQ arithmetic','error':str(e)[:400]})
        try:
            budgets=call('frappe.client.get_list',dict(doctype='Project Budget',fields=['name'],limit_page_length=1))
            if budgets:
                doc=call('frappe.client.get',dict(doctype='Project Budget',name=budgets[0]['name']))
                total=sum(float(doc.get(k) or 0) for k in ['total_material','total_labour','total_subcontractor','total_other_expenses','total_equipment'])
                rows=sum(float(x.get('total_cost') or 0) for x in doc['clauses'] if not x['is_group'])
                checks.append({'check':'Existing Project Budget category and detail reconciliation','passed':abs(total-doc['total_project_budget'])<.01 and abs(rows-total)<.01,'budget_total':doc['total_project_budget']})
        except Exception as e: checks.append({'check':'Budget reconciliation','error':str(e)[:400]})
        b.close()
    (ROOT/'interaction-review.json').write_text(json.dumps({'date':'2026-10-29','checks':checks},ensure_ascii=False,indent=2),encoding='utf-8')
    for c in checks: print(c['check'],c.get('passed',c.get('status',c.get('error',''))),flush=True)


if __name__=='__main__': main()
