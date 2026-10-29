# Site review / تقرير مراجعة الموقع

**Site:** https://en.connect4systems.com  
**Date:** 29 October 2026  
**Scope:** authenticated UI review, isolated draft clause-fetch tests, unsaved BOQ
arithmetic and reconciliation of existing submitted records.

## Results / النتائج

| Check | Result |
| --- | --- |
| Authorized login and Tender workspace | Passed |
| Open 20 application/master document types | 20 opened |
| BOQ Equipment tab installed | Confirmed |
| Unsaved BOQ equipment: Project QTY 100, coefficient 2, cost 5 | Qty 200; total 1,000; clause unit cost 10 |
| Project Budget tabs installed | Confirmed |
| Existing Project Budget reconciliation | Total 72,000 equals categories and detail rows, excluding heading double count |
| CR All Clauses hides group controls | Passed |
| CR selected group shows clause/quantity selection table | Passed |
| Select All Clauses in This Group hides details | Passed |
| Repeated fetch keeps existing source row/quantity and skips duplicates | Passed using temporary draft |
| Temporary CR draft cleanup | Passed |
| Project Supplier then Subcontractor Contract dialog | Passed with existing submitted contract |
| Existing customer certificate → submitted invoice and deduction reconciliation | Passed for PCLE-2026-00016 |
| Existing subcontract certificate → submitted invoice and deduction reconciliation | Passed for SCLE-2026-00017 |
| Local automated regression suite | 172 tests passed |

## Observations / الملاحظات

A JavaScript error, **`field item not found`**, was reproduced when opening
`Costing Note / COS-Note-2026-00001` in a fresh page.
The Costing Note client source still references legacy child fields such as `item`
which are absent from the current Costing Note Items definition. This requires a
separate compatibility review. Opening a form successfully does not establish that
every action on that form works. The guides retain this verification limitation.

لوحظ خطأ JavaScript بالنص **field item not found** خلال مراجعة النماذج.
يشير ملف واجهة Costing Note إلى حقول قديمة، منها `item`، غير موجودة في
التعريف الحالي لجدول Costing Note Items. تحتاج هذه النقطة إلى مراجعة توافق
مستقلة. فتح النموذج لا يعني نجاح جميع إجراءاته.

The retained Subcontractor Custody controller uses the literal warehouse name
`Subcontractor - C`. Confirm warehouse/company configuration before operating it.
The retained Account Balances source is not a verified operational report; use
standard General Ledger and Receivable/Payable reports for reconciliation.

يستخدم متحكم عهدة مقاول الباطن الحالي اسم المخزن الحرفي `Subcontractor - C`؛
يلزم التحقق من ضبط المخزن والشركة قبل التشغيل. ملف Account Balances القديم
ليس تقرير أرصدة تشغيليًا متحققًا منه؛ استخدم تقارير الأستاذ والمدينين والدائنين
القياسية للمطابقة.

## Limits and data handling / حدود الاختبار والتعامل مع البيانات

- Existing business documents were read, not edited.
- Temporary CR drafts were created for picker/fetch testing and deleted afterwards.
  Their creation can advance the naming series; no attempt was made to reset it.
- Browser-only equipment examples were not saved.
- No new financial invoices, certificates or stock movements were submitted.
- Existing invoice and journal links/totals were inspected; ledger-level posting,
  payment allocation, cancellation/amendment, concurrency and nonadministrator
  permission coverage still require a dedicated staging acceptance test.
- Local tests mock parts of Frappe and do not replace native site accounting tests.
- Credentials and authenticated browser storage are excluded from the guide package.

تمت قراءة المستندات الأصلية دون تعديلها. أُنشئت مسودات CR مؤقتة لاختبار
الاختيار والجلب ثم حُذفت؛ وقد تقدم تسلسل التسمية نتيجة إنشائها. لم يُحفظ مثال
المعدات في المتصفح، ولم تُعتمد فواتير أو مستخلصات مالية أو حركات مخزون جديدة.
تبقى اختبارات الترحيل الكامل والسداد والإلغاء والتعديل والتزامن وصلاحيات
المستخدمين العاديين مطلوبة على نسخة تجريبية مخصصة.

Machine-readable evidence is held locally in `site-review.json` and
`interaction-review.json`. Screenshots are in `assets/`. The downloadable package
contains the user guides, screenshots and this report, not authentication data.
