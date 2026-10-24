"""Build the offline BI-style dashboard and article from verified local outputs."""
from pathlib import Path
import hashlib
import html
import json
import shutil
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"outputs/showcase"


def article_body(article):
    esc=html.escape
    out=[f'<div class="article-category">القطاع غير الربحي · قراءة تنموية</div><h1 class="article-title">{esc(article["title"])}</h1>',f'<div class="article-deck">{esc(article["subtitle"])}</div><div class="article-meta"><span>{esc(article["author"])}</span><span>{esc(article["date"])}</span></div>',f'<p class="article-intro">{esc(article["intro"])}</p>']
    for i,section in enumerate(article["sections"]):
        out.append(f'<section id="section-{i}"><h3>{esc(section["title"])}</h3>')
        for j,p in enumerate(section["paragraphs"]):
            refs=''.join(f'<a class="article-ref" href="#source-{ref}">[{ref}]</a>' for ref in section['refs']) if j==len(section['paragraphs'])-1 else ''
            out.append(f'<p>{esc(p)}{refs}</p>')
        out.append('</section>')
    out.append('<div class="article-sources"><h3>المصادر والإسناد</h3><ol>')
    for source in article["sources"]:
        out.append(f'<li id="source-{source["id"]}"><a href="{esc(source["url"])}" target="_blank" rel="noopener">{esc(source["title"])}</a><small>{esc(source["note"])}</small></li>')
    out.append('</ol></div>')
    return '\n'.join(out)


def build():
    data_path=ROOT/"data_clean/national_entities_available.csv"
    df=pd.read_csv(data_path,dtype=str,encoding="utf-8-sig",keep_default_na=False)
    pop_meta=json.loads((ROOT/"research/population_sources.json").read_text(encoding="utf-8"))
    assert hashlib.sha256(data_path.read_bytes()).hexdigest()==pop_meta['entity_input_sha256']
    assert len(df)==6403 and df.record_key.is_unique
    df["missing"]=df.entity_id.eq("").astype(int)
    df["review"]=df.needs_review.eq("True").astype(int)
    cells=df.groupby(["region","entity_type","main_group_code"],sort=False).agg(count=("record_key","size"),missing=("missing","sum"),review=("review","sum")).reset_index().rename(columns={"entity_type":"type","main_group_code":"group"})
    groups=df[["main_group_code","main_group_name"]].drop_duplicates().sort_values('main_group_code').rename(columns={"main_group_code":"code","main_group_name":"name"})
    regions=df.groupby("region").size().reset_index(name="count")
    summary=pd.read_csv(ROOT/"outputs/national/focus/social_services_population_comparison.csv",encoding="utf-8-sig")
    focus=summary[["region","association_records","foundation_records","population_2022","associations_per_100k_population_2022","association_records_without_id"]].rename(columns={"association_records":"associations","foundation_records":"foundations","population_2022":"population","associations_per_100k_population_2022":"rate","association_records_without_id":"missing"})
    assert len(focus)==13 and focus.associations.sum()==1546 and focus.foundations.sum()==61
    for row in focus.itertuples():
        assert abs(row.rate-row.associations/row.population*100000)<1e-10
    manifest=json.loads((ROOT/"research/national_sources.json").read_text(encoding="utf-8"))
    source_counts=df.region.value_counts().to_dict()
    sources=[dict(region=s['region'],records=int(source_counts[s['region']]),period=s['reference_period_as_displayed'],updated=s['updated_at_as_displayed'],url=s['dataset_url']) for s in manifest['sources']]
    article=json.loads((ROOT/"presentation/article_content.json").read_text(encoding="utf-8"))
    quality=json.loads((ROOT/"outputs/national/quality/quality_report.json").read_text(encoding="utf-8"))
    payload={"created_on":"2026-10-24","data_collected_on":"2026-10-23","associationType":"جمعية أهلية","foundationType":"مؤسسة أهلية","cells":cells.to_dict('records'),"groups":groups.to_dict('records'),"regions":regions.to_dict('records'),"focus":focus.to_dict('records'),"sources":sources,"quality":{"entities_with_review_issues":quality['entities_with_review_issues'],"issue_counts":quality['issue_counts']},"article":article}
    (DEST/'assets').mkdir(parents=True,exist_ok=True)
    for path in [ROOT/'presentation/index.html',*list((ROOT/'presentation/assets').glob('*'))]:
        if path.is_file():shutil.copy2(path,DEST/path.relative_to(ROOT/'presentation'))
    (DEST/'assets/data.js').write_text('window.BOUSLA_DATA = '+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    # Content-based asset versions prevent an old stylesheet surviving a rebuild.
    index=(DEST/'index.html').read_text(encoding='utf-8')
    for asset in ['dashboard.css','dashboard.js','data.js']:
        version=hashlib.sha256((DEST/'assets'/asset).read_bytes()).hexdigest()[:12]
        index=index.replace('assets/'+asset,'assets/'+asset+'?v='+version)
    (DEST/'index.html').write_text(index,encoding='utf-8')
    article_html=f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(article['title'])}</title><link rel="stylesheet" href="assets/dashboard.css"></head><body><main class="standalone-article"><div class="article-nav"><a href="index.html#article">← بوصلة العطاء</a><button class="button primary" onclick="window.print()">طباعة المقال</button></div><article class="panel article-card">{article_body(article)}</article></main></body></html>'''
    css_version=hashlib.sha256((DEST/'assets/dashboard.css').read_bytes()).hexdigest()[:12]
    article_html=article_html.replace('assets/dashboard.css','assets/dashboard.css?v='+css_version)
    (DEST/'article.html').write_text(article_html,encoding='utf-8')
    docs=ROOT/'docs';docs.mkdir(exist_ok=True)
    md=[f'# {article["title"]}',article['subtitle'],f'{article["author"]} | {article["date"]}',article['intro']]
    for s in article['sections']:
        md.extend(['## '+s['title'],*s['paragraphs']])
        if s['refs']:md.append('المراجع: '+', '.join(f'[{i}]({next(src["url"] for src in article["sources"] if src["id"]==i)})' for i in s['refs']))
    md.append('## المصادر والإسناد')
    md.extend(f'{s["id"]}. [{s["title"]}]({s["url"]}) - {s["note"]}' for s in article['sources'])
    (docs/'article.ar.md').write_text('\n\n'.join(md)+'\n',encoding='utf-8')
    verification={"status":"SHOWCASE_DATA_OK","records":int(cells['count'].sum()),"regions":len(regions),"associations":int(cells.loc[cells.type.eq('جمعية أهلية'),'count'].sum()),"foundations":int(cells.loc[cells.type.eq('مؤسسة أهلية'),'count'].sum()),"missing_ids":int(cells.missing.sum()),"review_records":int(cells.review.sum()),"social_associations":int(focus.associations.sum()),"population_2022":int(focus.population.sum()),"source_sha256":hashlib.sha256(data_path.read_bytes()).hexdigest(),"no_names_or_national_ids_in_browser_payload":True}
    (DEST/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(verification,ensure_ascii=False,indent=2))
    print('ARTICLE_WORDS',len(' '.join([article['intro'],*[p for s in article['sections'] for p in s['paragraphs']]]).split()))


if __name__=='__main__':build()
