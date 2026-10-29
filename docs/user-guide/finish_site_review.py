"""Capture the Project selector in a fresh page and review existing accounting links."""
import json
import tempfile
from pathlib import Path
from urllib.parse import quote
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parent
SITE='https://en.connect4systems.com'


def main():
    result=json.loads((ROOT/'interaction-review.json').read_text(encoding='utf-8'))
    result['checks']=[x for x in result['checks'] if x['check']!='Project supplier-contract picker']
    with sync_playwright() as p:
        b=p.chromium.launch(executable_path=r'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',headless=True)
        c=b.new_context(storage_state=str(Path(tempfile.gettempdir())/'contractor-guide-session.json'),viewport={'width':1440,'height':1050})
        page=c.new_page()
        errors=[]
        page.on('pageerror',lambda e:errors.append({'url':page.url,'error':str(e),'stack':e.stack[:1000]}))
        page.goto(SITE+'/app/project/PROJ-0001',wait_until='domcontentloaded',timeout=60000)
        page.wait_for_function("window.cur_frm && cur_frm.doctype==='Project' && typeof cur_frm.events.create_subcontract_clearance==='function'",timeout=45000)
        page.wait_for_timeout(1500)

        def call(method,args):
            return page.evaluate('async a=>(await frappe.call({method:a.m,args:a.a})).message',{'m':method,'a':args})

        try:
            opts=call('contractor.subcontracting.project_contract_options',{'project':'PROJ-0001'})
            if not opts['suppliers']: raise ValueError('No eligible Supplier for PROJ-0001')
            page.evaluate('()=>cur_frm.events.create_subcontract_clearance(cur_frm)')
            dialog=page.locator('.modal:visible');dialog.wait_for(state='visible')
            supplier=opts['suppliers'][0]['name']
            inp=dialog.locator('div.frappe-control[data-fieldname="supplier"] input')
            inp.fill(supplier);inp.press('Tab')
            control=dialog.locator('div.frappe-control[data-fieldname="subcontractor_contract"]')
            control.wait_for(state='visible',timeout=10000)
            contracts=[x for x in opts['contracts'] if x['supplier']==supplier]
            cinp=control.locator('input')
            cinp.fill(contracts[0]['name']);cinp.press('Tab')
            page.wait_for_timeout(600)
            page.screenshot(path=str(ROOT/'assets/project-subcontract-picker.png'))
            result['checks'].append({'check':'Project Supplier/Contract selection dialog','passed':True,'note':'Existing submitted contract selected; Create Clearance not pressed.'})
            dialog.locator('.btn-modal-close').click()
        except Exception as e: result['checks'].append({'check':'Project Supplier/Contract selection dialog','error':str(e)[:500]})

        for dt in ['Project Clearnce','Subcontract Clearnce']:
            try:
                rows=call('frappe.client.get_list',{'doctype':dt,'fields':['name'],'filters':{'docstatus':1},'limit_page_length':10})
                for row in rows:
                    cert=call('frappe.client.get',{'doctype':dt,'name':row['name']})
                    if cert.get('legacy_record') or not cert.get('invoice'): continue
                    invoice_type='Sales Invoice' if dt=='Project Clearnce' else 'Purchase Invoice'
                    inv=call('frappe.client.get',{'doctype':invoice_type,'name':cert['invoice']})
                    ok=inv['docstatus']==1 and len(inv.get('items',[]))==1 and abs(inv['grand_total']-cert['grand_total'])<.01
                    if cert.get('deduction_entry'):
                        je=call('frappe.client.get',{'doctype':'Journal Entry','name':cert['deduction_entry']})
                        ok=ok and je['docstatus']==1 and abs(je['total_debit']-je['total_credit'])<.01
                    result['checks'].append({'check':dt+' existing invoice/deduction reconciliation','passed':ok,'certificate':row['name']})
                    for target,name in [(invoice_type,inv['name']),('Journal Entry',cert.get('deduction_entry'))]:
                        if not name:continue
                        page.goto(SITE+'/app/'+target.lower().replace(' ','-')+'/'+quote(name,safe=''),wait_until='domcontentloaded')
                        page.wait_for_function('dt=>window.cur_frm && cur_frm.doctype===dt',arg=target,timeout=30000)
                        page.wait_for_timeout(1000)
                        page.screenshot(path=str(ROOT/'assets'/(target.lower().replace(' ','-')+('-buying' if dt=='Subcontract Clearnce' else '-selling')+'.png')))
                    break
                else: result['checks'].append({'check':dt+' existing accounting reconciliation','status':'no submitted nonlegacy certificate with invoice available'})
            except Exception as e:result['checks'].append({'check':dt+' existing accounting reconciliation','error':str(e)[:400]})
        notes=call('frappe.client.get_list',{'doctype':'Costing Note','fields':['name'],'limit_page_length':1})
        if notes:
            page.goto(SITE+'/app/costing-note/'+quote(notes[0]['name'],safe=''),wait_until='domcontentloaded')
            page.wait_for_function("window.cur_frm && cur_frm.doctype==='Costing Note'",timeout=30000)
            page.wait_for_timeout(1200)
        result['additional_browser_errors']=errors
        b.close()
    result['checks']=list({x['check']:x for x in result['checks']}.values())
    (ROOT/'interaction-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    for x in result['checks']:print(x['check'],x.get('passed',x.get('error',x.get('status',''))),flush=True)


if __name__=='__main__':main()
