"""Bilingual user-facing instructions. English labels match the application UI."""

SECTIONS = []


def add(en, ar, steps_en, steps_ar, images=(), note_en='', note_ar='', table=None):
    SECTIONS.append(dict(en=en, ar=ar, steps_en=steps_en, steps_ar=steps_ar,
                         images=list(images), note_en=note_en, note_ar=note_ar, table=table))


add('Sign in and find your documents', 'تسجيل الدخول والوصول إلى المستندات', [
    'Open https://en.connect4systems.com and select Login. Enter the account assigned to you, then click Login.',
    'Open the Tender workspace. Alternatively, use the search box at the top and enter the exact document name shown in this guide.',
    'Open a list to review existing records. Select a record to open it, or use Add/New when creating a new document.',
    'Use the tabs to move between Details, Clauses, Taxes and Totals, Contracting and Connections where available.',
    'Save stores a draft. Submit approves a submittable document and may trigger downstream actions. If a Workflow is configured, use its permitted approval actions.',
], [
    'افتح https://en.connect4systems.com ثم اختر Login. أدخل الحساب المخصص لك واضغط Login.',
    'افتح مساحة العمل Tender. ويمكنك استخدام مربع البحث أعلى الصفحة وكتابة اسم المستند بالإنجليزية كما يظهر في هذا الدليل.',
    'افتح القائمة لاستعراض السجلات، ثم اضغط سجلًا لفتحه، أو اختر Add / New لإنشاء مستند جديد.',
    'تنقل بين تبويبات Details وClauses وTaxes and Totals وContracting وConnections بحسب المستند.',
    'يحفظ Save المسودة. أما Submit فيعتمد المستند القابل للاعتماد وقد ينشئ مستندات لاحقة. عند وجود Workflow استخدم إجراءات الموافقة المسموحة لحسابك.',
], ['site-access.png','desk.png'], 'Screenshots show the English interface. Button visibility depends on permissions, document status and the installed site version. Use the English labels to locate the corresponding Arabic interface controls.', 'الصور من الواجهة الإنجليزية. ظهور الأزرار يعتمد على الصلاحيات وحالة المستند وإصدار الموقع. تساعدك الأسماء الإنجليزية على تحديد الحقول المقابلة عند استخدام واجهة عربية.')

add('Prepare master data and Project Abbreviation', 'تجهيز البيانات الأساسية واختصار المشروع', [
    'Ask the administrator to confirm Company, company abbreviation, default currency, Customer, Suppliers, Items and UOMs before starting.',
    'Open Contract Type and check the available values: Arch, Civil, Elec, Mech and Service. CR uses this master, rather than Item Group.',
    'Open Division to review construction divisions. Division has Title and Description; its name comes from Title. Division is not required on CR.',
    'Open Cost Code and review the hierarchy and Cost Type. Cost Type links to Cost Center; it is not a separate custom DocType.',
    'Open the operational Project, enter Project Abbreviation below Project Name, and Save. The technical field is custom_abbreviation. Use a short abbreviation such as TST.',
    'If a field or newly added tab is missing, ask the administrator to check deployment/migration and refresh the browser. Do not create another field with the same purpose.',
], [
    'اطلب من مسؤول النظام تأكيد الشركة واختصارها والعملة الافتراضية والعميل والموردين والأصناف ووحدات القياس قبل البدء.',
    'افتح Contract Type وتحقق من القيم: Arch وCivil وElec وMech وService. يعتمد CR على هذا السجل بدلًا من Item Group.',
    'افتح Division لاستعراض أقسام أعمال البناء. يحتوي على Title وDescription، ويُسمى السجل من Title. حقل Division غير مطلوب في CR.',
    'افتح Cost Code وراجع شجرة الأكواد وCost Type. يرتبط Cost Type بمركز تكلفة Cost Center، وليس نوع مستند مخصصًا مستقلًا.',
    'افتح سجل Project التشغيلي وأدخل Project Abbreviation أسفل Project Name ثم احفظ. الاسم التقني للحقل custom_abbreviation. استخدم اختصارًا قصيرًا مثل TST.',
    'إذا غاب حقل أو تبويب جديد، اطلب مراجعة نشر التحديثات والترحيل ثم حدّث المتصفح. لا تنشئ حقلًا إضافيًا يؤدي الغرض نفسه.',
], ['project.png','contract-type.png','cost-code.png'], 'Cost Type categories use the configured company abbreviation: Equipments, Labour, Material and Subcontractor. The workbook suffix C is not the required company abbreviation.', 'تستخدم فئات Cost Type اختصار الشركة المضبوط في النظام: Equipments وLabour وMaterial وSubcontractor. اللاحقة C في الملف الأصلي ليست اختصارًا إلزاميًا للشركة.')

add('Create a Tender Analysis and its clauses', 'إنشاء تحليل المناقصة وإدخال البنود', [
    'Search for Tender Analysis and choose New. Enter Company, Title, Tender Number, Date, Party Type, Party Name, Currency and the desired Project name.',
    'Open Contractual Clauses. Add a group heading with Is Group selected, then add its detail rows below it.',
    'For each detail, enter Clause Title, a positive Qty and its UOM. Do not use a heading as a payable work item.',
    'Choose Automatic numbering for series such as 1, 1_1 and 1_2. Save to generate the series.',
    'To import instead, download Excel Template, enter literal values in the template, save the tender and select Upload Excel. Review the preview and choose Apply Rows.',
    'Review the completed table, then click Create Contractual Clauses. Each row receives its own linked clause. Repeating the action creates only missing links.',
], [
    'ابحث عن Tender Analysis ثم اختر New. أدخل Company وTitle وTender Number وDate ونوع الطرف Party Type واسمه Party Name والعملة Currency واسم المشروع المطلوب.',
    'افتح Contractual Clauses. أضف عنوان مجموعة مع تحديد Is Group، ثم أضف صفوف التفاصيل تحته.',
    'أدخل لكل بند Clause Title وكمية Qty موجبة ووحدة UOM. عنوان المجموعة ليس بند أعمال مستقلًا للصرف.',
    'اختر Automatic لإنتاج تسلسل مثل 1 ثم 1_1 ثم 1_2، واحفظ لتوليد الأرقام.',
    'للاستيراد، نزّل Excel Template وأدخل قيمًا فعلية في القالب، واحفظ المناقصة ثم اختر Upload Excel. راجع المعاينة واضغط Apply Rows.',
    'راجع الجدول ثم اضغط Create Contractual Clauses لربط كل صف ببند تعاقدي مستقل. تكرار الإجراء ينشئ الروابط الناقصة فقط.',
], ['tender-analysis.png','tender-analysis-clauses.png'], 'Excel import replaces the tender table and is offered before creating Contractual Clauses. Imported numbering uses From Excel. Project at this stage is a name, not an existing operational Project link.', 'استيراد Excel يستبدل جدول المناقصة ويتاح قبل إنشاء Contractual Clauses. يحتفظ وضع From Excel بأرقام الملف. حقل Project في هذه المرحلة اسم نصي، وليس رابط المشروع التشغيلي.')

add('Create the Costing Note', 'إنشاء مذكرة التسعير', [
    'Save the Tender Analysis after generating all Contractual Clauses.',
    'Select Create > Costing Note. Check the source tender, currency, clauses, quantities and units.',
    'Save the new Costing Note as a draft before creating BOQs.',
    'Use the BOQ button on each detail row to open its matching BOQ. Group headings do not need resource pricing.',
    'Return after submitting the BOQs and review each returned unit cost and total cost.',
], [
    'احفظ Tender Analysis بعد توليد جميع Contractual Clauses.',
    'اختر Create > Costing Note وراجع المناقصة المصدر والعملة والبنود والكميات والوحدات.',
    'احفظ Costing Note كمسودة قبل إنشاء مستندات BOQ.',
    'استخدم زر BOQ في كل صف تفصيلي لفتح تحليل موارده. عناوين المجموعات لا تحتاج إلى تسعير موارد مستقل.',
    'عد إلى المذكرة بعد اعتماد مستندات BOQ وراجع تكلفة الوحدة والتكلفة الإجمالية لكل بند.',
], ['costing-note.png'], 'Source rows and quantities follow the tender. If its structure or quantities change, recreate the affected draft Costing Note. Site review reproduced “field item not found” when opening an existing Costing Note; ask the administrator to resolve this compatibility issue before relying on its complete pricing cycle.', 'تتبع صفوف المصدر وكمياتها المناقصة. عند تغيير بنية البنود أو كمياتها أعد إنشاء مذكرة التسعير المسودة المتأثرة. أعادت مراجعة الموقع إظهار الخطأ field item not found عند فتح مذكرة موجودة؛ اطلب من مسؤول النظام حل مشكلة التوافق قبل الاعتماد على دورة التسعير كاملة.')

add('Price BOQ resources for the full Project Quantity', 'تسعير موارد BOQ على إجمالي كمية المشروع', [
    'Open the BOQ from its Costing Note row. Check Clause Title, UOM and Project QTY. Tender-linked Project QTY follows the source row.',
    'In Material, select each resource Item and UOM, enter the quantity required per clause unit and its cost rate.',
    'Repeat for Labour, Contractors and Expenses. Review the calculated Project Quantity and Total Cost of each resource.',
    'For example, Project QTY 100 and a resource coefficient of 2 give resource quantity 200. At rate 5 the resource total is 1,000.',
    'Review Total Project Cost and Cost per Clause Unit. Save and Submit the BOQ to return its unit cost to the correct Costing Note row.',
], [
    'افتح BOQ من صف مذكرة التسعير. راجع Clause Title وUOM وProject QTY. تتبع كمية BOQ المرتبط بالمناقصة كمية الصف المصدر.',
    'في Material اختر Item وUOM لكل مورد، وأدخل كمية المورد اللازمة لوحدة واحدة من بند الأعمال وسعر تكلفته.',
    'كرر ذلك في Labour وContractors وExpenses. راجع كمية المشروع المحسوبة Project Quantity وTotal Cost لكل مورد.',
    'مثال: إذا كانت Project QTY تساوي 100 ومعامل المورد يساوي 2، تصبح كمية المورد 200. وعند تكلفة وحدة 5 تكون تكلفته 1,000.',
    'راجع Total Project Cost وCost per Clause Unit، ثم احفظ واعتمد BOQ لإرجاع تكلفة الوحدة إلى الصف الصحيح في Costing Note.',
], ['boq.png'], 'Resource project quantity = quantity per clause unit × Project QTY. Total cost = resource project quantity × resource cost rate. Unit clause cost = total project cost ÷ Project QTY. Historical submitted BOQs may retain Per Unit basis.', 'كمية المورد للمشروع = كمية المورد لكل وحدة بند × Project QTY. تكلفة المورد = كميته للمشروع × سعر تكلفته. تكلفة وحدة البند = إجمالي تكلفة المشروع ÷ Project QTY. قد تحتفظ مستندات BOQ القديمة المعتمدة بأساس Per Unit.')

add('Add equipment and reuse a Template BOQ', 'إضافة المعدات واستخدام قالب BOQ', [
    'Open the BOQ Equipment tab, located before Expenses in the updated form.',
    'Add an Equipment Costs row. Select the Equipment Item and UOM, then enter quantity per clause unit and the cost rate.',
    'Review the automatically calculated Project Quantity, row Total Cost and Total Equipment Costs.',
    'To reuse a resource breakdown, prepare Template BOQ with resource quantities per clause unit, including Equipment Costs.',
    'On a new/draft BOQ, select BOQ Template. Review every copied resource and rate before saving; applying a template replaces the resource breakdown.',
], [
    'افتح تبويب Equipment في BOQ، ويقع قبل Expenses في النموذج المحدّث.',
    'أضف صفًا في Equipment Costs واختر صنف المعدة Equipment Item ووحدة UOM، ثم أدخل الكمية لكل وحدة بند وسعر التكلفة.',
    'راجع كمية المشروع المحسوبة Project Quantity وتكلفة الصف Total Cost وإجمالي Total Equipment Costs.',
    'لإعادة استخدام تحليل موارد، جهّز Template BOQ بكميات الموارد لكل وحدة بند، بما فيها Equipment Costs.',
    'في BOQ جديد أو مسودة اختر BOQ Template، وراجع الموارد والأسعار المنسوخة قبل الحفظ؛ تطبيق القالب يستبدل تحليل الموارد.',
], ['boq-equipment-entry.png','template-boq.png'], 'Equipment costs feed BOQ cost, Costing Note pricing and Project Budget. Older custom equipment rows are retained. If Equipment is absent on the site, the new metadata/assets need deployment; a screenshot of an older form does not prove the new tab is installed.', 'تدخل تكلفة المعدات في إجمالي BOQ وتسعير Costing Note وموازنة Project Budget. تُحفظ صفوف المعدات المخصصة القديمة. إذا غاب تبويب Equipment عن الموقع، يلزم نشر تعريفاته وملفات الواجهة؛ ظهور نموذج قديم لا يثبت تثبيت التبويب الجديد.')

add('Apply selling margins and complete tender pricing', 'إضافة هامش البيع وإكمال تسعير المناقصة', [
    'Return to the saved Costing Note after submitting all required BOQs.',
    'Enter the required profit margin and review the detail selling values and group summaries.',
    'Check that total cost equals unit cost × clause quantity, and selling amount equals total cost × (1 + margin / 100).',
    'Save, then Submit the Costing Note. Open Tender Analysis and verify the resulting selling rates and amounts.',
    'To reprice an applied clause, first cancel the owning Costing Note and resolve downstream dependencies. Prepare and approve revised costing through the same cycle.',
], [
    'عد إلى Costing Note المحفوظ بعد اعتماد جميع تحليلات BOQ المطلوبة.',
    'أدخل هامش الربح المطلوب وراجع قيم البيع للتفاصيل وملخصات المجموعات.',
    'تحقق من أن إجمالي التكلفة = تكلفة الوحدة × كمية البند، وقيمة البيع = إجمالي التكلفة × (1 + نسبة الهامش ÷ 100).',
    'احفظ ثم اعتمد Costing Note، وافتح Tender Analysis للتحقق من أسعار البيع والمبالغ الناتجة.',
    'لإعادة تسعير بند مطبق، ألغِ أولًا مذكرة التسعير المالكة لأسعاره وعالج المستندات اللاحقة المرتبطة، ثم جهّز واعتمد التسعير الجديد بالدورة نفسها.',
], ['costing-note.png','tender-analysis-clauses.png'], 'One applied Costing Note owns a clause’s pricing at a time. All active Costing Notes must be submitted before creating the commercial offer/contract.', 'لا يملك تسعير البند أكثر من Costing Note مطبق واحد في الوقت نفسه. يجب اعتماد جميع مذكرات التسعير النشطة قبل إنشاء العرض أو العقد التجاري.')

add('Create the Project Offer and Project Contract', 'إنشاء عرض المشروع وعقد المشروع', [
    'Save the fully priced Tender Analysis. Use Create > Project Offer when issuing an offer, or Create > Project Contract for the direct contract route.',
    'Check Customer, Company, Currency, conversion rate, Project name, dates and copied clauses. Complete addresses, payment terms and other commercial terms.',
    'Review agreed quantities and selling rates in Clauses. Complete Taxes and Totals and Contracting as described next.',
    'Save and Submit the Project Offer. To convert it, choose Create > Project Contract and review the copied commercial values.',
    'Save and Submit Project Contract after the agreed checks and workflow approvals. The Project name is used to create/link the operational Project.',
    'Use Open Project or Created Project to open the result. Repeating conversion opens an existing active contract instead of creating another.',
], [
    'احفظ Tender Analysis بعد اكتمال التسعير. اختر Create > Project Offer لإصدار عرض، أو Create > Project Contract لإنشاء العقد مباشرة.',
    'راجع العميل Customer والشركة Company والعملة Currency وسعر التحويل واسم المشروع والتواريخ والبنود المنسوخة، واستكمل العناوين وشروط الدفع والشروط التجارية.',
    'راجع الكميات المتفق عليها وأسعار البيع في Clauses، ثم استكمل Taxes and Totals وContracting كما هو موضح في الخطوة التالية.',
    'احفظ واعتمد Project Offer. لتحويله اختر Create > Project Contract وراجع القيم التجارية المنقولة.',
    'احفظ واعتمد Project Contract بعد المراجعة وموافقات سير العمل. يُستخدم اسم المشروع لإنشاء أو ربط سجل Project التشغيلي.',
    'افتح النتيجة من Open Project أو Created Project. تكرار التحويل يفتح العقد النشط الموجود بدلًا من إنشاء عقد إضافي.',
], ['project-offer.png','project-contract.png'], 'The offer/contract is a commercial document and does not itself post revenue or move stock. The operational Project may require creation permissions. Project Budget is created from a submitted Project Contract.', 'العرض والعقد مستندان تجاريان ولا يثبتان إيرادًا أو حركة مخزون بذاتهما. يلزم امتلاك صلاحية إنشاء المشروع التشغيلي. تُنشأ Project Budget من عقد مشروع معتمد.')

add('Set taxes, discounts and contracting deductions', 'ضبط الضرائب والخصومات والاستقطاعات', [
    'Open Taxes and Totals. On customer documents choose Sales Taxes and Charges Template; on CR/subcontract documents choose Purchase Taxes and Charges Template.',
    'Use a template belonging to the document Company. Review each tax row’s account, charge type, rate and included-in-rate setting.',
    'If needed, choose the additional discount basis and enter the percentage or fixed discount. Check Net Total, tax totals and Grand Total.',
    'Open Contracting. Select Selling Deductions Template for customer documents, or Purchasing Deductions Template for subcontract documents.',
    'Review or edit each deduction Title, Account and Percent. Confirm Total Deductions and Net Payable, then Save.',
], [
    'افتح Taxes and Totals. اختر Sales Taxes and Charges Template لمستندات العميل، أو Purchase Taxes and Charges Template لطلب CR ومستندات مقاول الباطن.',
    'اختر قالبًا تابعًا لشركة المستند. راجع حساب كل ضريبة ونوع احتسابها ونسبتها وما إذا كانت مشمولة في السعر.',
    'عند الحاجة حدد أساس الخصم الإضافي وأدخل نسبته أو قيمته الثابتة، ثم راجع Net Total وإجمالي الضرائب وGrand Total.',
    'افتح Contracting. اختر Selling Deductions Template لمستندات العميل، أو Purchasing Deductions Template لمستندات مقاول الباطن.',
    'راجع أو عدّل Title وAccount وPercent لكل استقطاع، وتحقق من Total Deductions وNet Payable ثم احفظ.',
], ['project-contract-taxes.png','project-contract-contracting.png','cr-taxes.png'], 'Deductions use the document Grand Total; Net Payable = Grand Total − Total Deductions. Templates populate editable draft rows. Later edits do not update the source template. Actual tax amounts and fixed discounts start at zero on a new period certificate and must be entered for that period.', 'تُحسب الاستقطاعات على Grand Total، ويكون Net Payable = Grand Total − Total Deductions. يملأ القالب صفوفًا قابلة للتعديل في المسودة، ولا تُعدّل التغييرات اللاحقة القالب المصدر. تبدأ ضرائب Actual والخصومات الثابتة بصفر في مستخلص الفترة الجديد لتحديد نصيب الفترة.')

add('Create and approve the Project Budget', 'إنشاء موازنة المشروع واعتمادها', [
    'Open the submitted Project Contract and confirm that its operational Project exists.',
    'Choose Create > Project Budget. The system opens a new draft or the existing active budget for that contract.',
    'Check Details: Project Contract, Project, Tender Analysis, Company, Currency and Budget Date.',
    'Open Total Budget and review Total Project Budget, Total Material, Total Labour, Total Subcontractor, Total Other Expenses and Total Equipment.',
    'Open Contract Clauses Budget. Review each contract quantity, BOQ unit cost and total clause budget; expand rows for category amounts and source links.',
    'Save and Submit after review. Source costs and quantities are verified by the server. A submitted budget is a snapshot, and does not post accounting entries.',
], [
    'افتح Project Contract المعتمد وتأكد من وجود سجل Project التشغيلي المرتبط به.',
    'اختر Create > Project Budget. يفتح النظام مسودة جديدة أو الموازنة النشطة الموجودة لهذا العقد.',
    'راجع بيانات Details: العقد والمشروع وتحليل المناقصة والشركة والعملة وتاريخ Budget Date.',
    'افتح Total Budget وراجع Total Project Budget وإجمالي المواد Total Material والعمالة Total Labour ومقاولي الباطن Total Subcontractor والمصروفات الأخرى Total Other Expenses والمعدات Total Equipment.',
    'افتح Contract Clauses Budget وراجع كمية العقد وتكلفة وحدة BOQ وموازنة كل بند، وافتح الصفوف لمراجعة توزيع التكلفة وروابط المصادر.',
    'احفظ واعتمد بعد المراجعة. يتحقق الخادم من تكاليف المصادر وكمياتها. الموازنة المعتمدة لقطة محفوظة للتكلفة ولا تنشئ قيدًا محاسبيًا.',
], ['project-budget.png','project-budget-totals.png','project-budget-clauses-budget.png'], 'The budget is COST based. Clause budget = final contract quantity × normalized BOQ unit cost. Selling profit, taxes and deductions are excluded. Example: BOQ quantity 100 costs 2,300, unit cost 23; final contract quantity 150 produces budget 3,450, regardless of selling rate.', 'الموازنة مبنية على التكلفة. موازنة البند = كمية العقد النهائية × تكلفة وحدة BOQ بعد توحيد أساسها. لا تدخل أرباح البيع أو الضرائب أو الاستقطاعات. مثال: تكلفة كمية BOQ البالغة 100 هي 2,300، فتكون تكلفة الوحدة 23؛ وعند كمية عقد نهائية 150 تصبح الموازنة 3,450 بغض النظر عن سعر البيع.')

add('Monitor Project quantities and progress', 'متابعة كميات المشروع ونسب التنفيذ', [
    'Open the operational Project from its Project Contract or the Project list.',
    'Review Project Name, Company, Customer, dates and Project Abbreviation. Save any permitted changes before using Create actions.',
    'Open Project Clauses and review contractual, executed and remaining quantities for each detail clause.',
    'Review Clause Groups and Progress for group summaries by UOM. Customer progress and subcontractor progress are independent measures.',
    'Use Connections and the linked contract to review commercial values. The Project clause tables show quantities/progress and do not expose contract prices.',
], [
    'افتح سجل Project التشغيلي من عقد المشروع أو من قائمة Project.',
    'راجع اسم المشروع والشركة والعميل والتواريخ واختصار Project Abbreviation. احفظ التعديلات المسموحة قبل استخدام إجراءات Create.',
    'افتح Project Clauses وراجع كمية العقد والمنفذ والمتبقي لكل بند تفصيلي.',
    'راجع Clause Groups and Progress لملخص المجموعات حسب وحدة القياس. تنفيذ العميل وتنفيذ مقاولي الباطن مؤشرات مستقلة.',
    'استخدم Connections ورابط العقد لمراجعة القيم التجارية؛ جداول بنود Project تعرض الكميات ونسب التنفيذ دون أسعار العقد.',
], ['project-progress.png','project.png'], 'Only submitted, noncancelled certificates contribute to progress. Group headings are not payable quantities. Quantities with different UOMs are not added together as one physical quantity.', 'تدخل المستخلصات المعتمدة غير الملغاة فقط في التنفيذ. عناوين المجموعات ليست كميات للصرف. ولا تُجمع وحدات القياس المختلفة في كمية مادية واحدة.')

add('Create a CR and enter contract clauses', 'إنشاء طلب تعاقد CR وإدخال البنود', [
    'Search for CR and choose New. Select the operational Project and Supplier.',
    'Select Contract Type: Arch, Civil, Elec, Mech or Service. Complete Posting Date, End Date, Attach CR and notes.',
    'Check Company, Currency and conversion rate. Enter manual group/detail clauses, import the supplied Excel Template, or use Fetch from Project.',
    'For detail clauses enter Qty, UOM and Rate. Amount is calculated; group amounts summarize their details.',
    'Complete Taxes and Totals and Contracting, then Save. Review all clauses and attachments before the configured approval/submission process.',
], [
    'ابحث عن CR واختر New، ثم حدد المشروع التشغيلي Project والمورد Supplier.',
    'اختر Contract Type من Arch أوCivil أوElec أوMech أوService. استكمل Posting Date وEnd Date وأرفق Attach CR وأدخل الملاحظات.',
    'راجع الشركة والعملة وسعر التحويل. أدخل مجموعات البنود وتفاصيلها يدويًا، أو استورد قالب Excel الخاص بالشاشة، أو استخدم Fetch from Project.',
    'أدخل Qty وUOM وRate للبنود التفصيلية. تُحسب Amount تلقائيًا وتلخص المجموعات مبالغ تفاصيلها.',
    'استكمل Taxes and Totals وContracting ثم احفظ، وراجع البنود والمرفقات قبل إجراءات الموافقة والاعتماد المضبوطة على الموقع.',
], ['cr.png','cr-clauses.png'], 'The Project must have Project Abbreviation for project-based naming. CR does not require Division. Keep source Project references by fetching clauses when they must count toward Project progress.', 'يجب تعبئة Project Abbreviation في المشروع لإتمام التسمية المعتمدة على المشروع. لا يتطلب CR حقل Division. استخدم جلب البنود من المشروع للاحتفاظ بمراجعها عندما يلزم إدراجها في متابعة تنفيذ المشروع.')

add('Fetch Project clauses repeatedly without losing rows', 'جلب بنود المشروع على دفعات دون مسح الجدول', [
    'Save the CR draft with its selected Project, then click Fetch from Project.',
    'Leave All Clauses selected to fetch the complete Project. Group Clause and group-selection controls are hidden in this mode.',
    'For a specific group, clear All Clauses and select Group Clause.',
    'Select Select All Clauses in This Group to fetch the whole group. Clear it to display the clause selection table.',
    'In the table, tick the required clauses and enter their required quantities. You can switch groups to make further selections.',
    'Click Insert Clauses. Review the appended rows, existing edits and quantities, then Save.',
    'Repeat Fetch from Project whenever needed. Existing rows remain; already inserted source clauses are skipped rather than duplicated.',
], [
    'احفظ مسودة CR بعد اختيار Project، ثم اضغط Fetch from Project.',
    'اترك All Clauses محددًا لجلب جميع بنود المشروع؛ تُخفى عندها حقول اختيار المجموعة.',
    'لاختيار مجموعة محددة أزل تحديد All Clauses ثم اختر Group Clause.',
    'حدد Select All Clauses in This Group لجلب المجموعة كاملة، أو أزل تحديده لإظهار جدول اختيار البنود.',
    'حدد البنود المطلوبة في الجدول وأدخل كمياتها. يمكنك الانتقال بين المجموعات لإضافة اختيارات أخرى.',
    'اضغط Insert Clauses وراجع الصفوف المضافة والكميات والتعديلات الموجودة ثم احفظ.',
    'كرر Fetch from Project عند الحاجة. تبقى الصفوف السابقة، ويتجاوز النظام البنود المصدرية المضافة بالفعل بدلًا من تكرارها.',
], ['cr-picker-all.png','cr-picker-group.png','cr-picker-table.png'], 'Picker quantity changes affect the CR, not Project quantities. This additive Project fetch differs from Excel import replacement. Do not use the tender’s Excel replacement action as a way to append CR rows.', 'تؤثر كميات نافذة الاختيار في CR دون تغيير كميات Project. جلب المشروع تراكمي ويختلف عن استيراد Excel الذي يستبدل الصفوف. لا تستخدم استيراد المناقصة بديلًا لإضافة دفعات بنود إلى CR.')

add('Create the Subcontractor Contract', 'إنشاء عقد مقاول الباطن', [
    'Open an approved/submitted CR and choose Create > Subcontractor Contract.',
    'Review the copied Project, Supplier/Contractor, Contract Type, dates, clauses, rates, taxes, deductions and source CR link.',
    'Upload the signed/agreed file to Attach Contract. Complete any remaining mandatory fields.',
    'For a direct contract instead, create Subcontractor Contract from its list, fill the header and add clauses using the same manual, Excel or Project-fetch controls.',
    'Review Taxes and Totals and Contracting. Confirm positive agreed rates for payable detail clauses, then Save and complete approval/Submit.',
    'After submission, use Create > Subcontract Clearnce for the next period certificate. Repeated CR conversion opens its existing active contract.',
], [
    'افتح CR بعد الموافقة عليه واعتماده ثم اختر Create > Subcontractor Contract.',
    'راجع المشروع والمورد أو Contractor ونوع العقد والتواريخ والبنود والأسعار والضرائب والاستقطاعات ورابط CR المنقول.',
    'ارفع ملف العقد المتفق عليه في Attach Contract واستكمل الحقول الإلزامية المتبقية.',
    'لإنشاء عقد مباشر افتح قائمة Subcontractor Contract وأنشئ سجلًا جديدًا، وأكمل بياناته وأضف البنود بالمنطق نفسه: يدويًا أو Excel أو Fetch from Project.',
    'راجع Taxes and Totals وContracting وتأكد من أسعار الاتفاق الموجبة للبنود التفصيلية، ثم احفظ وأكمل الموافقات وSubmit.',
    'بعد الاعتماد استخدم Create > Subcontract Clearnce لإنشاء مستخلص الفترة. تكرار التحويل من CR يفتح العقد النشط الموجود له.',
], ['subcontractor-contract.png','subcontractor-contract-clauses.png','subcontractor-contract-contracting.png'], 'Contract-backed certificates retain the agreed rates and source row identities. Manually entered/imported contract rows use contract quantity limits, but do not create Project progress rows without the original Project links.', 'تحتفظ المستخلصات المرتبطة بالعقد بأسعار الاتفاق ومراجع صفوف المصدر. تستخدم البنود اليدوية أو المستوردة حدود كميات العقد، لكنها لا تنشئ صفوف متابعة تنفيذ في Project دون روابط المشروع الأصلية.')

add('Issue a customer Project Clearnce', 'إعداد مستخلص العميل', [
    'Save the operational Project, then choose Create > Project Clearnce.',
    'Review Customer, Project Contract, currency, Posting Date and Cost Center.',
    'Open Clauses. For each payable detail, review Total Required Qty, Previous Qty and Remaining Qty, then enter Current Qty for this period only.',
    'Alternatively, use Current % of Remaining where appropriate. Do not enter the cumulative executed quantity as Current Qty.',
    'Review contract rates, period amounts, taxes, period fixed charges and contracting deductions. Save the draft and obtain the required review.',
    'Submit when ready to post. The system creates the Sales Invoice and, where applicable, the deduction Journal Entry, and updates Project progress.',
], [
    'احفظ المشروع التشغيلي ثم اختر Create > Project Clearnce.',
    'راجع العميل وعقد المشروع والعملة وتاريخ Posting Date ومركز Cost Center.',
    'افتح Clauses. راجع Total Required Qty وPrevious Qty وRemaining Qty لكل بند، ثم أدخل Current Qty للفترة الحالية فقط.',
    'يمكن استخدام Current % of Remaining عند الحاجة. لا تضع كمية التنفيذ التراكمية في خانة Current Qty.',
    'راجع أسعار العقد ومبالغ الفترة والضرائب والرسوم الثابتة الخاصة بالفترة والاستقطاعات، ثم احفظ المسودة واستكمل المراجعة.',
    'اعتمد عند الاستعداد للترحيل. ينشئ النظام Sales Invoice وقيد استقطاعات Journal Entry عند وجودها، ويحدث تنفيذ المشروع.',
], ['project-clearnce.png','project-clearnce-clauses.png'], 'Submission is an accounting action. Rates come from Project Contract and quantities cannot exceed the contractual balance. A posting failure prevents completion of the certificate submission.', 'اعتماد المستخلص إجراء محاسبي. تأتي الأسعار من Project Contract ولا يجوز تجاوز الرصيد التعاقدي للكميات. يمنع فشل الترحيل إكمال اعتماد المستخلص.')

add('Issue a Subcontract Clearnce from Project', 'إعداد مستخلص مقاول الباطن من المشروع', [
    'Save the Project and choose Create > Subcontract Clearnce.',
    'Select Supplier first. The selector contains suppliers with submitted Subcontractor Contracts for this Project.',
    'Select the required Subcontractor Contract for that Supplier and Project, then click Create Clearance.',
    'Review the mapped document. Current-period quantities start at zero; enter only this period’s Current Qty. The selected contract supplies the agreed rates.',
    'Check Previous Qty, Project Previous Qty and Remaining Qty. Review taxes, period Actual charges, discounts, deductions and Cost Center.',
    'Save and review, then Submit. Open the resulting Purchase Invoice and Deduction Entry if present, and verify updated Project progress.',
], [
    'احفظ Project ثم اختر Create > Subcontract Clearnce.',
    'اختر Supplier أولًا. تعرض القائمة الموردين الذين لديهم Subcontractor Contract معتمد لهذا المشروع.',
    'اختر عقد مقاول الباطن المطلوب لنفس المورد والمشروع، ثم اضغط Create Clearance.',
    'راجع المستند المنقول. تبدأ كميات الفترة بصفر؛ أدخل Current Qty للفترة الحالية فقط. تأتي أسعار الاتفاق من العقد المحدد.',
    'راجع Previous Qty وProject Previous Qty وRemaining Qty، ثم الضرائب ورسوم Actual الخاصة بالفترة والخصومات والاستقطاعات ومركز التكلفة.',
    'احفظ وراجع ثم اعتمد. افتح Purchase Invoice الناتجة وDeduction Entry عند وجوده، وتحقق من تحديث التنفيذ في Project.',
], ['project-subcontract-picker.png','subcontract-clearnce.png','subcontract-clearnce-clauses.png'], 'The system enforces the contract’s cumulative quantity limit. For Project-linked clauses it also enforces the Project-wide subcontract limit across suppliers. Changing Supplier clears the selected contract.', 'يتحقق النظام من حد الكمية التراكمية للعقد. وللبنود المرتبطة بالمشروع يطبق أيضًا الحد الإجمالي لمقاولي الباطن على مستوى المشروع عبر جميع الموردين. تغيير المورد يمسح اختيار العقد السابق.')

add('Review invoices, deductions and payments', 'مراجعة الفواتير والاستقطاعات والسداد', [
    'On a submitted certificate, choose Open Invoice and check the party, Project, currency, net work value, tax amounts and invoice total.',
    'The invoice contains a single non-stock service item for the certified works. The detailed work measurement remains in the certificate clauses.',
    'If deductions exist, open Deduction Entry and check its accounts and value. It settles the deduction against the party balance without posting the same work revenue/expense again.',
    'Example without taxes: certified works 100 and deduction 10 produce invoice 100, deduction settlement 10 and net payable 90.',
    'Record actual collection/payment using standard ERPNext Payment Entry against the appropriate outstanding invoice.',
    'Use General Ledger and Accounts Receivable/Accounts Payable for balance reconciliation. Verify Company, party, date range and submitted transaction status.',
], [
    'من المستخلص المعتمد اضغط Open Invoice وراجع الطرف والمشروع والعملة وصافي الأعمال والضرائب وإجمالي الفاتورة.',
    'تحتوي الفاتورة على صنف خدمي غير مخزني واحد للأعمال المعتمدة، وتبقى تفاصيل القياس في بنود المستخلص.',
    'عند وجود استقطاعات افتح Deduction Entry وراجع الحسابات والقيمة. يسوي القيد الاستقطاع مع رصيد الطرف دون تكرار إثبات إيراد أو مصروف الأعمال.',
    'مثال دون ضرائب: أعمال بقيمة 100 واستقطاع 10 ينتج عنها فاتورة 100 وتسوية استقطاع 10 وصافي مستحق 90.',
    'سجل التحصيل أو الدفع الفعلي باستخدام Payment Entry القياسي في ERPNext مقابل رصيد الفاتورة المعنية.',
    'استخدم General Ledger وتقارير Accounts Receivable وAccounts Payable لمطابقة الأرصدة، مع مراجعة الشركة والطرف والفترة وحالة الاعتماد.',
], ['sales-invoice-selling.png','purchase-invoice-buying.png','journal-entry-selling.png','journal-entry-buying.png'], 'Company defaults, party accounts, income/expense accounts, Cost Center and rounding accounts must be configured before posting. The retained legacy Account Balances source is not a verified operational balance report.', 'يلزم ضبط إعدادات الشركة وحسابات الأطراف والإيراد أو المصروف ومركز التكلفة وحساب فروق التقريب قبل الترحيل. ملف التقرير القديم Account Balances المحتفظ به ليس تقرير أرصدة تشغيليًا متحققًا منه.')

add('Use Purchase Comparison', 'استخدام مقارنة عروض الشراء', [
    'Open Comparison directly. Where the Material Request workflow is configured, an approved/submitted Purchase request exposes Create Purchase Comparison to a Purchase User.',
    'Review Project, Material Request and the requested items. In the comparison matrix, use Add Item for additional rows if needed.',
    'Choose Attach Supplier for each supplier being compared. Enter each supplier rate for each item and review quantity × rate and supplier totals.',
    'Enter technical ratings, attach supplier quotations and record Accepted Supplier, Amount and Notes as required.',
    'Save and use the configured review/submission process. Export Excel downloads a CSV file; review it in Excel.',
], [
    'افتح Comparison مباشرة. وعند ضبط سير عمل Material Request، يظهر Create Purchase Comparison لمستخدم Purchase User على طلب شراء معتمد وحالته Approved.',
    'راجع Project وMaterial Request والأصناف المطلوبة، واستخدم Add Item في مصفوفة المقارنة لإضافة صفوف عند الحاجة.',
    'اختر Attach Supplier لإضافة كل مورد، ثم أدخل سعره لكل صنف وراجع حاصل الكمية × السعر وإجماليات الموردين.',
    'أدخل التقييم الفني وأرفق عروض الموردين وحدد Accepted Supplier وAmount وNotes بحسب الحاجة.',
    'احفظ واتبع إجراءات المراجعة والاعتماد المضبوطة. ينزل Export Excel ملف CSV يمكن مراجعته في Excel.',
], ['comparison.png'], 'The retained comparison feature depends on its site fields and configured Material Request workflow. Do not assume that approving Comparison automatically creates a Purchase Order.', 'تعتمد المقارنة المحتفظ بها على حقول الموقع وسير عمل Material Request المضبوط. لا تفترض أن اعتماد Comparison ينشئ أمر شراء تلقائيًا.')

add('Use Item Coding Request and Subcontractor Custody', 'استخدام طلب تكويد الأصناف وعهدة مقاول الباطن', [
    'For coding, open Item Coding Request, choose New, select Project and Date, and add item names, UOMs, descriptions and attachments in Items.',
    'Save and send through the configured review process. Record the resulting Item Code links when the authorized master-data user has created the Items.',
    'For custody, open Subcontractor Custody. Select Subcontractor, Project and Date, then choose Type Out for issue or Return for return.',
    'Enter Items, positive quantities and correct UOMs; add a note. Check the Project warehouse and destination/source custody warehouse with the stock administrator.',
    'Save and Submit only after stock review. The current custody controller creates and submits a Material Transfer Stock Entry.',
], [
    'للتكويد افتح Item Coding Request واختر New وحدد Project وDate، ثم أضف أسماء الأصناف ووحداتها وأوصافها ومرفقاتها في Items.',
    'احفظ واتبع المراجعة المضبوطة. سجل روابط Item Code الناتجة بعد إنشاء الأصناف بواسطة المسؤول المخول عن البيانات الأساسية.',
    'للعهدة افتح Subcontractor Custody وحدد المقاول والمشروع والتاريخ، ثم اختر Type = Out للصرف أو Return للإرجاع.',
    'أدخل الأصناف والكميات الموجبة ووحدات القياس الصحيحة والملاحظات، وراجع مخزن المشروع ومخزن عهدة المقاول مع مسؤول المخزون.',
    'احفظ واعتمد بعد مراجعة المخزون؛ ينشئ متحكم العهدة الحالي Stock Entry من نوع Material Transfer ويعتمده.',
], ['item-coding-request.png','subcontractor-custody.png'], 'The current custody code uses Project custom_warehouse and the literal warehouse “Subcontractor - C”. Confirm this configuration before use; it is not the dynamic company-abbreviation logic used by Cost Type. Automatic Item creation is not implemented by the basic Item Coding Request controller.', 'يستخدم كود العهدة الحالي custom_warehouse في المشروع واسم المخزن الحرفي Subcontractor - C. تحقق من الإعداد قبل الاستخدام؛ فهو لا يتبع منطق اختصار الشركة المتغير المستخدم في Cost Type. لا ينفذ المتحكم الأساسي لطلب التكويد إنشاء الأصناف تلقائيًا.')

add('Use standard purchasing and project-based names', 'استخدام المشتريات القياسية والتسمية بحسب المشروع', [
    'Create Opportunity, Quotation, Sales Order, Sales Invoice, Purchase Order, Purchase Invoice and Purchase Receipt through their standard ERPNext forms.',
    'For a new Purchase Order, select the native Project field before saving and confirm the linked Project has Project Abbreviation.',
    'Save to receive a name such as PO-TST-0001. Purchase Receipt uses PRE-TST-0001 for the same Project abbreviation.',
    'Use standard ERPNext items, taxes, receipts and invoicing actions. There is no custom Purchase Order Type selector in this app’s current purchasing flow.',
], [
    'أنشئ Opportunity وQuotation وSales Order وSales Invoice وPurchase Order وPurchase Invoice وPurchase Receipt من نماذج ERPNext القياسية.',
    'في أمر شراء جديد اختر حقل Project القياسي قبل الحفظ، وتأكد من تعبئة Project Abbreviation في المشروع المرتبط.',
    'احفظ ليكون الاسم مثل PO-TST-0001. ويستخدم Purchase Receipt اسمًا مثل PRE-TST-0001 للاختصار نفسه.',
    'استخدم أصناف ERPNext وضرائبه وإجراءات الاستلام والفوترة القياسية. لا يوجد محدد Purchase Order Type مخصص في دورة المشتريات الحالية للتطبيق.',
], ['cost-code.png'], 'Naming is the retained Purchase Order/Purchase Receipt exception. Company abbreviation on Cost Centers and Project Abbreviation on document names are separate settings.', 'التسمية هي الاستثناء المحتفظ به لأمر الشراء وإيصال الاستلام. اختصار الشركة في مراكز التكلفة واختصار المشروع في أسماء المستندات إعدادان مختلفان.')

add('Correct, cancel and amend documents', 'تصحيح المستندات وإلغاؤها وتعديلها', [
    'Edit and Save drafts before submitting. Review the document status and linked documents in Connections.',
    'To correct a submitted document, follow the configured Cancel/Amend permissions and resolve downstream links first.',
    'Before cancelling a certificate, reconcile any payments or downstream documents blocking its invoice. Certificate cancellation reverses its generated deduction entry/invoice through the application flow.',
    'Cancel/delete active certificates before cancelling their Subcontractor Contract, then resolve linked contracts before cancelling CR.',
    'For Project Contract cancellation, resolve active budgets and other downstream links and set the related Project status as required. Do not alter source database references manually.',
    'After permitted cancellation, verify recalculated quantities and financial balances. Create an amendment or replacement through the normal document actions.',
], [
    'عدّل المسودات واحفظها قبل الاعتماد، وراجع حالة المستند وروابطه من Connections.',
    'لتصحيح مستند معتمد اتبع صلاحيات Cancel وAmend المضبوطة، وعالج المستندات اللاحقة المرتبطة أولًا.',
    'قبل إلغاء مستخلص عالج المدفوعات أو الروابط التي تمنع إلغاء فاتورته. يعكس إلغاء المستخلص قيد استقطاعاته وفاتورته من خلال دورة التطبيق.',
    'ألغِ أو احذف المستخلصات النشطة قبل إلغاء عقد مقاول الباطن، ثم عالج العقود المرتبطة قبل إلغاء CR.',
    'لإلغاء Project Contract عالج الموازنات النشطة والروابط اللاحقة وحالة المشروع المرتبط وفق المتطلبات. لا تعدّل مراجع قاعدة البيانات يدويًا.',
    'بعد الإلغاء المسموح راجع الكميات المعاد احتسابها والأرصدة المالية، ثم أنشئ تعديلًا أو بديلًا من الإجراءات المعتادة.',
], [], 'Historical Legacy Record certificates retain their older behavior. Do not use them as examples of the new clause-based accounting cycle.', 'تحتفظ المستخلصات التاريخية الموسومة Legacy Record بسلوكها السابق. لا تستخدمها نموذجًا للدورة الجديدة القائمة على البنود.')

add('Troubleshooting and daily checks', 'حل المشكلات والمراجعة اليومية', [
    'Missing Project Abbreviation: open the linked operational Project, fill the abbreviation and Save. If the field itself is missing, ask for the migration/metadata repair.',
    'Missing creation button: Save the source, check submitted status, complete source pricing and confirm create/read permissions. A draft Costing Note blocks offer/contract creation.',
    'No picker table: clear All Clauses, choose a group and clear Select All Clauses in This Group. Confirm that the group contains detail clauses.',
    'No Supplier/Contract in the Project clearance dialog: confirm there is a submitted contract for that exact Project/Supplier and that your account can read it.',
    'Budget creation blocked: check exact submitted BOQ/Costing Note links, UOM, currency and active-budget uniqueness. Do not substitute another clause with the same title.',
    'Posting failure: ask Accounts to check party, income/expense, deduction and tax accounts, Company, Cost Center and rounding defaults. Keep the failed certificate in draft until resolved.',
    'At day end, compare submitted certificates, invoices, deduction entries, Project progress and party outstanding balances.',
], [
    'رسالة نقص Project Abbreviation: افتح المشروع التشغيلي المرتبط وأدخل الاختصار واحفظ. إذا غاب الحقل نفسه، اطلب تنفيذ الترحيل أو إصلاح تعريفه.',
    'غياب زر الإنشاء: احفظ المصدر وراجع حالة الاعتماد واكتمال التسعير وصلاحيات القراءة والإنشاء. وجود Costing Note مسودة يمنع إنشاء العرض أو العقد.',
    'غياب جدول الاختيار: أزل All Clauses واختر مجموعة وأزل Select All Clauses in This Group، وتأكد أن المجموعة تحتوي على بنود تفاصيل.',
    'غياب المورد أو العقد من نافذة المستخلص: تحقق من وجود عقد معتمد لنفس المشروع والمورد ومن صلاحية قراءة حسابك له.',
    'توقف إنشاء الموازنة: راجع روابط BOQ وCosting Note المعتمدة ووحدة القياس والعملة وعدم وجود موازنة نشطة أخرى. لا تستبدل بندًا بآخر له العنوان نفسه.',
    'فشل الترحيل: اطلب من الحسابات مراجعة حساب الطرف والإيراد أو المصروف والاستقطاعات والضرائب والشركة ومركز التكلفة والتقريب. اترك المستخلص مسودة حتى حل السبب.',
    'طابق في نهاية اليوم المستخلصات المعتمدة وفواتيرها وقيود الاستقطاع وتنفيذ المشروع والأرصدة المستحقة للأطراف.',
], [])
