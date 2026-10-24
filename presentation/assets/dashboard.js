"use strict";
(() => {
  const D = window.BOUSLA_DATA;
  const $ = id => document.getElementById(id);
  const f = (n, digits=0) => new Intl.NumberFormat('en-US',{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(n);
  const esc = value => String(value).replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  const sum = (rows,key) => rows.reduce((t,r)=>t+(Number(r[key])||0),0);
  const state = {view:'overview',region:'all',type:'all',group:'all',sort:'count'};
  const titles = {
    overview:['الحضور المسجل للقطاع الأهلي','المناطق والتخصصات في قراءة واحدة، مع سياق يوضح ما تعنيه الأرقام.'],
    focus:['الخدمات الاجتماعية في سياق السكان','مقارنة وصفية لسجلات الجمعيات مع خط أساس سكاني لعام 2022.'],
    quality:['الوضوح يبدأ من جودة البيانات','مصادر وتواريخ وفحوص تساعدك على قراءة النتائج في نطاقها الصحيح.'],
    article:['القطاع غير الربحي وخدمة المجتمع','مقال يربط دور الجمعيات والشركات غير الربحية بقيمة البيانات في التخطيط.']
  };
  function selectedRegions(){return D.regions.filter(r=>state.region==='all'||r.region===state.region);}
  function filtered(){return D.cells.filter(r=>(state.region==='all'||r.region===state.region)&&(state.type==='all'||r.type===state.type)&&(state.group==='all'||r.group===state.group));}
  function kpi(label,value,note,icon='▦',color=''){return `<div class="kpi ${color}"><div class="label"><span class="kpi-icon">${icon}</span>${label}</div><div class="number">${value}</div><small>${note}</small></div>`;}
  function empty(){return '<div class="empty"><strong>لا توجد سجلات مطابقة</strong>غيّر المرشحات أو اضغط إعادة التعيين لعرض البيانات.</div>';}
  function bars(rows,key,{rate=false,click=true}={}){
    const max=Math.max(1,...rows.map(r=>r[key]));
    return `<div class="bar-list">${rows.map(r=>`<${click?'button':'div'} class="bar-row" ${click?`data-region="${esc(r.region)}" aria-label="عرض منطقة ${esc(r.region)}"`:''} title="${esc(r.region)}: ${f(r[key],rate?2:0)}${rate?' لكل 100 ألف من سكان 2022':' سجل'}"><span class="bar-label">${esc(r.region)}${r.missing?' *':''}</span><span class="bar-track"><span class="bar-fill" style="display:block;width:${r[key]/max*100}%"></span></span><span class="bar-value">${f(r[key],rate?2:0)}</span></${click?'button':'div'}>`).join('')}</div><div class="axis-label"><span>0</span><span>${f(max,rate?1:0)}</span></div>`;
  }
  function scope(){
    if(state.view==='quality') return 'كامل لقطة المصادر · الفحوص على جميع السجلات';
    return [state.region==='all'?'جميع المناطق':state.region,state.type==='all'?'جميع الأنواع':state.type,state.group==='all'?'جميع التخصصات':D.groups.find(g=>g.code===state.group)?.name].filter(Boolean).join(' · ');
  }
  function overview(){
    const rows=filtered(),total=sum(rows,'count'),associations=sum(rows.filter(r=>r.type===D.associationType),'count'),foundations=sum(rows.filter(r=>r.type===D.foundationType),'count');
    const regions=selectedRegions().map(r=>({...r,count:sum(rows.filter(c=>c.region===r.region),'count'),missing:sum(rows.filter(c=>c.region===r.region),'missing'),review:sum(rows.filter(c=>c.region===r.region),'review')}));
    regions.sort(state.sort==='alpha'?(a,b)=>a.region.localeCompare(b.region,'ar'):(a,b)=>b.count-a.count);
    const groups=D.groups.map(g=>({...g,count:sum(rows.filter(r=>r.group===g.code),'count')})).filter(g=>g.count).sort((a,b)=>b.count-a.count);
    const pct=total?associations/total*100:0;
    const groupChart=groups.length?`<div class="group-list">${groups.slice(0,7).map(g=>`<button class="group-row" data-group="${g.code}" title="${esc(g.name)}: ${f(g.count)} سجل؛ ${f(g.count/total*100,2)}% من العرض"><div class="group-top"><span>${esc(g.name)}</span><strong>${f(g.count)}</strong></div><div class="group-track"><div class="group-fill" style="width:${g.count/groups[0].count*100}%"></div></div></button>`).join('')}</div>`:empty();
    const missing=sum(rows,'missing');
    $('overview-view').innerHTML=`
      <div class="kpis">${kpi('سجلات الجهات',f(total),'عدد الصفوف المطابقة للمرشحات','▦')}${kpi('جمعيات أهلية',f(associations),'سجلات الجمعيات في العرض الحالي','◉','blue')}${kpi('مؤسسات أهلية',f(foundations),'سجلات المؤسسات في العرض الحالي','◇','purple')}${kpi('ملفات المناطق المشمولة',`${selectedRegions().length}<span style="font-size:17px;color:#a8b2bd"> / 13</span>`,'تغطية الملفات، وليست اكتمال السجل','⌖','gold')}</div>
      <div class="panel-grid"><section class="panel"><div class="panel-head"><div><h2 class="panel-title">توزيع السجلات حسب المنطقة</h2><p class="panel-subtitle">انقر على المنطقة لتخصيص العرض · وحدة القياس: سجل جهة</p></div><select id="region-sort" class="small-control" aria-label="ترتيب المناطق"><option value="count" ${state.sort==='count'?'selected':''}>الأعلى عدداً</option><option value="alpha" ${state.sort==='alpha'?'selected':''}>الاسم أبجدياً</option></select></div>${total?bars(regions,'count'):empty()}<p class="panel-footnote">المنطقة حسب مجموعة المصدر. * الجوف: المعرّفات غير منشورة. الصفر مع المرشحات يعني عدم وجود سجل مطابق في الملفات المتاحة.</p></section>
      <section class="panel"><div class="panel-head"><div><h2 class="panel-title">التخصصات الرئيسية</h2><p class="panel-subtitle">أكبر ${Math.min(groups.length,7)} تخصصات في العرض الحالي · انقر للتصفية</p></div><span class="panel-icon">⋯</span></div>${groupChart}<div class="divider"></div><div class="panel-head" style="margin-bottom:8px"><h2 class="panel-title">تركيب أنواع الكيانات</h2><span class="legend-inline">${f(total)} سجل</span></div><div class="donut-zone"><div class="donut" style="background:${total?`conic-gradient(var(--teal) 0 ${pct}%,#7c97be ${pct}% 100%)`:'#eef2f6'}"><div class="donut-text"><strong>${f(pct,1)}<span style="font-size:12px;display:inline">%</span></strong><span>حصة الجمعيات من العرض</span></div></div></div><div class="legend-list"><div class="legend-item"><span><i class="swatch" style="background:var(--teal)"></i>جمعيات أهلية</span><strong>${f(associations)}</strong><span class="percentage">${f(pct,1)}%</span></div><div class="legend-item"><span><i class="swatch" style="background:#7c97be"></i>مؤسسات أهلية</span><strong>${f(foundations)}</strong><span class="percentage">${f(total?foundations/total*100:0,1)}%</span></div></div></section></div>
      <div class="insight"><span class="spark">✧</span><p>${groups.length?`<strong>${esc(groups[0].name)}</strong> تتصدر العرض الحالي بـ<strong>${f(groups[0].count)}</strong> سجل، تمثل <strong>${f(groups[0].count/total*100,2)}%</strong> من السجلات المطابقة. `:''}الأعداد تصف الحضور المسجل؛ وللمقارنة النسبية انتقل إلى <button class="table-row-button" data-switch="focus">الخدمات الاجتماعية والسكان ←</button>.</p></div>
      <section class="panel"><div class="panel-head"><div><h2 class="panel-title">تفاصيل المناطق ومؤشرات المراجعة</h2><p class="panel-subtitle">كل صف منطقة من مناطق المصدر، والأعداد تتأثر بالمرشحات المختارة.</p></div><span class="legend-inline"><span class="status-dot"></span> ${f(total)} سجل في العرض</span></div><div class="table-wrap"><table><thead><tr><th>منطقة المصدر</th><th>السجلات</th><th>الحصة من العرض</th><th>معرّف وطني غير منشور</th><th>سجلات عليها علامة مراجعة</th><th>حالة المعرّفات</th></tr></thead><tbody>${regions.map(r=>`<tr><td><button class="table-row-button" data-region="${esc(r.region)}">${esc(r.region)}</button></td><td class="numeric">${f(r.count)}</td><td>${f(total?r.count/total*100:0,2)}%</td><td>${f(r.missing)}</td><td>${f(r.review)}</td><td><span class="quality-pill ${r.count===0?'muted':r.missing?'review':''}">${r.count===0?'لا سجلات مطابقة':r.missing?'معرّفات غير منشورة':'المعرّفات منشورة'}</span></td></tr>`).join('')}</tbody></table></div><div class="table-tail"><span>علامة المراجعة قد تخص حقلاً لا يدخل في العد؛ لا تعني إلغاء السجل.</span><span>${missing?`${f(missing)} سجلاً بلا معرّف منشور`:'لا معرّفات ناقصة ضمن العرض'}</span></div></section>`;
    $('region-sort')?.addEventListener('change',e=>{state.sort=e.target.value;render();});
  }
  function focus(){
    const rows=D.focus.filter(r=>state.region==='all'||r.region===state.region).sort((a,b)=>b.rate-a.rate);
    const count=sum(rows,'associations'),population=sum(rows,'population'),rate=population?count/population*100000:0;
    const missing=sum(rows,'missing'),foundations=sum(rows,'foundations');
    const compare=D.focus.filter(r=>['القصيم','الشرقية'].includes(r.region));
    const compareCards=compare.map(r=>`<div class="comparison-card"><div class="region-name">${esc(r.region)}</div><div class="rate">${f(r.rate,2)}</div><small>لكل 100 ألف من سكان 2022</small><div class="count">${f(r.associations)} سجل جمعية</div><small>${f(r.population)} نسمة في المقام</small></div>`).join('');
    $('focus-view').innerHTML=`<div class="focus-banner"><b>مقارنة متجانسة</b><span>المؤشر مخصص لجمعيات الخدمات الاجتماعية G04؛ ثبتنا النوع والتخصص. المؤسسات معروضة منفصلة.</span></div><div class="kpis">${kpi('سجلات جمعيات الخدمات الاجتماعية',f(count),'البسط الأساسي للمعدل','◈')}${kpi('سكان 2022 في المناطق المختارة',f(population),'السعوديون وغير السعوديين والجنسين','◉','blue')}${kpi('سجل جمعية لكل 100 ألف نسمة',f(rate,2),'مجموع البسط ÷ مجموع المقام × 100,000','⌁','purple')}${kpi('مؤسسات خدمات اجتماعية',f(foundations),'للسياق، خارج بسط المقارنة','◇','gold')}</div>
    <div class="focus-grid"><section class="panel"><div class="panel-head"><div><h2 class="panel-title">الحضور المسجل نسبةً إلى سكان 2022</h2><p class="panel-subtitle">جمعيات G04 لكل 100 ألف نسمة · المقارنة مع خط أساس سكاني</p></div><span class="legend-inline">${rows.length} منطقة</span></div>${bars(rows,'rate',{rate:true})}<p class="panel-footnote">* الجوف: جمعياتها الثلاثون بلا أرقام وطنية منشورة. اختلاف تواريخ منشورات الجهات باقٍ.</p></section><section class="panel"><div class="panel-head"><div><h2 class="panel-title">عدد متقارب، سياق سكاني مختلف</h2><p class="panel-subtitle">مثال مرجعي ثابت: القصيم والشرقية</p></div><span class="panel-icon">↗</span></div><div class="compare-cards">${compareCards}</div><p class="focus-explanation">عدد سجلات الجمعيات متقارب، بينما يختلف عدد السكان. لذلك يختلف المعدل بنحو أربعة أضعاف؛ ولا يثبت أي من المعدلين كفاية الخدمة أو نقصها.</p><div class="divider"></div><h3 class="panel-title">ما الذي نحتاجه قبل قرار التوسع؟</h3><div class="check-list" style="margin-top:18px"><div class="check"><span class="tick">1</span><div><strong>نطاق الخدمة الفعلي</strong>أين تصل خدمات الجهة، وما الفئة المستهدفة؟</div></div><div class="check"><span class="tick">2</span><div><strong>الحجم والطاقة التشغيلية</strong>المستفيدون والميزانية وحجم البرامج.</div></div><div class="check"><span class="tick">3</span><div><strong>مؤشر احتياج مناسب</strong>بيانات محلية متوافقة مع سؤال الدراسة.</div></div></div></section></div>
    <div class="insight"><span class="spark">✧</span><p><strong>سنة المقام واضحة:</strong> 2022 أحدث سنة تغطي المناطق الـ13 في مجموعة السكان المفحوصة؛ 2023 و2024 فيها إجماليان وطنيان فقط. هذه مقارنة مع خط أساس، وليست كثافة حالية لعام 2026.</p></div>
    <section class="panel"><div class="panel-head"><div><h2 class="panel-title">جدول البسط والمقام</h2><p class="panel-subtitle">المعدلات تقريب للعرض؛ الحساب والتصدير يحفظان الدقة الكاملة.</p></div><span class="legend-inline">${f(missing)} سجل جمعية بلا معرّف منشور</span></div><div class="table-wrap"><table><thead><tr><th>المنطقة</th><th>سجلات الجمعيات</th><th>سجلات المؤسسات</th><th>سكان 2022</th><th>لكل 100 ألف</th><th>جمعيات بلا معرّف</th></tr></thead><tbody>${rows.map(r=>`<tr><td>${esc(r.region)}</td><td class="numeric">${f(r.associations)}</td><td>${f(r.foundations)}</td><td class="numeric">${f(r.population)}</td><td class="numeric">${f(r.rate,2)}</td><td><span class="quality-pill ${r.missing?'review':''}">${f(r.missing)}</span></td></tr>`).join('')}</tbody></table></div><p class="panel-footnote">الإسناد: منشورات المركز الوطني لتنمية القطاع غير الربحي؛ السكان: الهيئة العامة للإحصاء عبر بيانات السعودية. المعالجة والحساب من إعداد المشروع.</p></section>`;
  }
  function quality(){
    const q=D.quality;
    $('quality-view').innerHTML=`<div class="kpis">${kpi('ملفات مناطق مقروءة','13 / 13','تغطية المنشورات الإقليمية','⌖')}${kpi('معرّفات وطنية منشورة فريدة',f(6341),'من أصل 6,403 سجلات جهات','✓','blue')}${kpi('سجلات دون معرّف منشور','62','مصدر الجوف لا يتضمن حقل الرقم الوطني','!','gold')}${kpi('سجلات لها علامة مراجعة',f(q.entities_with_review_issues),'عدد السجلات، وقد تتعدد أسباب المراجعة','≡','purple')}</div>
    <div class="quality-layout"><section class="panel"><div class="panel-head"><h2 class="panel-title">ما الذي تحققنا منه؟</h2><span class="quality-pill">فحوص قابلة لإعادة التشغيل</span></div><div class="check-list"><div class="check"><span class="tick">✓</span><div><strong>حفظ المصادر والخلايا الأصلية</strong>فحوص البصمات وعدد الصفوف والمعرّفات والمجاميع.</div></div><div class="check"><span class="tick">✓</span><div><strong>توافق نسختي CSV وExcel</strong>مقارنة كل الخلايا في ملفي عسير والجوف المرفقين.</div></div><div class="check"><span class="tick">✓</span><div><strong>المقام السكاني وربط المناطق</strong>ربط 1:1 وفصل الإجمالي الوطني ومنع جمع الإجماليات مع مكوناتها.</div></div><div class="check review"><span class="tick">!</span><div><strong>التكرار الوطني غير محسوم بالكامل</strong>62 سجلاً للجوف بلا معرّفات؛ لم نربطها بالأسماء أو نخترع أرقاماً.</div></div></div></section>
    <section class="panel"><div class="panel-head"><h2 class="panel-title">منهجية واضحة في أربع خطوات</h2></div><div class="method-list"><div class="method-step"><h3>قراءة وتوثيق</h3><p>تسجيل مصدر كل ملف وتاريخه وبصمته وترميزه ورخصته.</p></div><div class="method-step"><h3>توحيد مضبوط</h3><p>قواعد أسماء صريحة، مع حفظ الأصل وسجل التغييرات.</p></div><div class="method-step"><h3>تحليل وصفي</h3><p>عدّ سجلات المنطقة والتخصص، وفصل أنواع الكيانات.</p></div><div class="method-step"><h3>مقارنة بسياق</h3><p>مقام سكان 2022 مع توضيح اختلاف سنوات المنشورات.</p></div></div></section></div>
    <div class="insight"><span class="spark">ⓘ</span><p><strong>حقل للمراجعة، لا حكم على الجهة:</strong> يتطابق التصنيف الفرعي الأول والثاني في مصدر مكة؛ استبعدنا المستوى الأول من مقارنته فقط. توجد أيضاً مواقع غير محددة وأوصاف متعارضة وتصنيفات غير قياسية، وحُفظت علامات مراجعتها.</p></div>
    <section class="panel"><div class="panel-head"><div><h2 class="panel-title">مصادر الجهات وتواريخ المنشورات</h2><p class="panel-subtitle">الفترة وصف للمجموعة، وليست تاريخ ملاحظة مثبتاً لكل جهة.</p></div><span class="legend-inline">13 مجموعة إقليمية</span></div><div class="table-wrap"><table><thead><tr><th>المنطقة</th><th>السجلات</th><th>الفترة كما نشرت</th><th>تحديث المصدر</th><th>المعرّفات</th><th>الإسناد</th></tr></thead><tbody>${D.sources.map(s=>`<tr><td>${esc(s.region)}</td><td class="numeric">${f(s.records)}</td><td><span class="source-date">${esc(s.period)}</span></td><td><span class="source-date">${esc(s.updated)}</span></td><td><span class="quality-pill ${s.region==='الجوف'?'review':''}">${s.region==='الجوف'?'غير منشورة':'منشورة'}</span></td><td><a class="source-link" href="${esc(s.url)}" target="_blank" rel="noopener">بطاقة المصدر ↗</a></td></tr>`).join('')}</tbody></table></div><div class="callout-rule">مصادر الجهات مرخصة وفق رخصة البيانات المفتوحة. بيانات السكان لها إسناد وسياسة ناشر مستقلان. <a href="https://open.data.gov.sa/ar/pages/policies/license" target="_blank" rel="noopener">رخصة البيانات</a> · <a href="https://www.stats.gov.sa/ar/use-policy" target="_blank" rel="noopener">سياسة الهيئة العامة للإحصاء</a></div></section>`;
  }
  function articleHTML(){
    const a=D.article;
    return `<div class="article-category">القطاع غير الربحي · قراءة تنموية</div><h2 class="article-title">${esc(a.title)}</h2><div class="article-deck">${esc(a.subtitle)}</div><div class="article-meta"><span>${esc(a.author)}</span><span>${esc(a.date)}</span><span>مقال موثق · 7 محاور</span></div><p class="article-intro">${esc(a.intro)}</p>${a.sections.map((s,i)=>`<section id="section-${i}"><h3>${esc(s.title)}</h3>${s.paragraphs.map((p,j)=>`<p>${esc(p)}${j===s.paragraphs.length-1?s.refs.map(id=>`<a class="article-ref" href="#source-${id}" aria-label="المصدر ${id}">[${id}]</a>`).join(''):''}</p>`).join('')}</section>`).join('')}<div class="article-sources"><h3>المصادر والإسناد</h3><ol>${a.sources.map(s=>`<li id="source-${s.id}"><a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)} ↗</a><small>${esc(s.note)}</small></li>`).join('')}</ol></div>`;
  }
  function article(){ $('article-view').innerHTML=`<div class="article-layout"><article class="panel article-card">${articleHTML()}</article><aside class="panel article-aside"><h3>في هذا المقال</h3><div class="article-toc">${D.article.sections.map((s,i)=>`<a href="#section-${i}">${esc(s.title)}</a>`).join('')}</div><div class="divider"></div><a class="button secondary" href="article.html" target="_blank" rel="noopener">نسخة مستقلة للقراءة ↗</a><p class="panel-footnote">التعريف العام يشمل الشركات غير الربحية، بينما بيانات اللوحة للجمعيات والمؤسسات الأهلية.</p></aside></div>`; }
  function render(){
    for(const v of ['overview','focus','quality','article']) $(v+'-view').hidden=v!==state.view;
    document.querySelectorAll('[data-view]').forEach(b=>{b.classList.toggle('active',b.dataset.view===state.view);b.setAttribute('aria-current',b.dataset.view===state.view?'page':'false');});
    $('page-title').textContent=titles[state.view][0];$('page-description').textContent=titles[state.view][1];
    $('filters').hidden=!['overview','focus'].includes(state.view);
    $('filters').style.display=['overview','focus'].includes(state.view)?'flex':'none';
    document.querySelector('.scope-line').style.display=state.view==='article'?'none':'flex';
    $('active-scope').textContent=scope();
    $('type-filter').disabled=state.view==='focus';$('group-filter').disabled=state.view==='focus';
    $('region-filter').value=state.region;$('type-filter').value=state.type;$('group-filter').value=state.group;
    $('export-button').disabled=state.view==='article';
    ({overview,focus,quality,article}[state.view])();
    $('live-status').textContent='تم تحديث العرض: '+scope();
    document.querySelectorAll('[data-region]').forEach(b=>b.addEventListener('click',()=>{state.region=b.dataset.region;render();}));
    document.querySelectorAll('[data-group]').forEach(b=>b.addEventListener('click',()=>{state.group=b.dataset.group;render();}));
    document.querySelectorAll('[data-switch]').forEach(b=>b.addEventListener('click',()=>switchView(b.dataset.switch)));
  }
  function switchView(view){
    if(!titles[view]) return;
    const wasFocus=state.view==='focus';state.view=view;
    if(view==='focus'){state.type=D.associationType;state.group='G04';}
    else if(wasFocus){state.type='all';state.group='all';}
    history.replaceState(null,'','#'+view);render();window.scrollTo({top:0,behavior:'auto'});
  }
  function exportCSV(){
    let headers,rows;
    if(state.view==='focus'){
      headers=['region','association_records','foundation_records','population_2022','associations_per_100k_population_2022','association_records_without_id'];
      rows=D.focus.filter(r=>state.region==='all'||r.region===state.region).map(r=>[r.region,r.associations,r.foundations,r.population,r.rate,r.missing]);
    }else if(state.view==='quality'){
      headers=['region','source_records','reference_period','updated_at','source_url'];rows=D.sources.map(s=>[s.region,s.records,s.period,s.updated,s.url]);
    }else{
      const data=filtered(),total=sum(data,'count');headers=['region','matching_source_records','share_percent','missing_published_ids','review_flagged_records'];
      rows=selectedRegions().map(r=>{const selected=data.filter(c=>c.region===r.region),n=sum(selected,'count');return[r.region,n,total?n/total*100:0,sum(selected,'missing'),sum(selected,'review')];});
    }
    const csv='\ufeff'+[headers,...rows].map(row=>row.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(',')).join('\r\n');
    const url=URL.createObjectURL(new Blob([csv],{type:'text/csv;charset=utf-8;'}));
    const a=document.createElement('a');a.href=url;a.download='bouslat-alataa-'+state.view+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
    $('live-status').textContent='تم تجهيز تصدير CSV للعرض الحالي.';
  }
  D.regions.forEach(r=>$('region-filter').add(new Option(r.region,r.region)));
  [D.associationType,D.foundationType].forEach(t=>$('type-filter').add(new Option(t,t)));
  D.groups.forEach(g=>$('group-filter').add(new Option(g.name,g.code)));
  $('region-filter').addEventListener('change',e=>{state.region=e.target.value;render();});
  $('type-filter').addEventListener('change',e=>{state.type=e.target.value;render();});
  $('group-filter').addEventListener('change',e=>{state.group=e.target.value;render();});
  $('reset-button').addEventListener('click',()=>{state.region='all';state.type=state.view==='focus'?D.associationType:'all';state.group=state.view==='focus'?'G04':'all';state.sort='count';render();});
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>switchView(b.dataset.view)));
  document.querySelector('.brand').addEventListener('click',e=>{e.preventDefault();switchView('overview');});
  $('export-button').addEventListener('click',exportCSV);$('print-button').addEventListener('click',()=>window.print());
  window.addEventListener('hashchange',()=>{const hash=location.hash.slice(1);if(titles[hash])switchView(hash);});
  switchView(titles[location.hash.slice(1)]?location.hash.slice(1):'overview');
})();
