#!/usr/bin/env python3
"""Rule-based bilingual enrichment for top curated records.

No external LLM/API is used. The generated summaries are concise bilingual
metadata summaries, not translations of private text.
"""
import argparse, json
from common import load_jsonish, save_jsonish

def zh_summary(p):
    name=p.get('name') or p.get('id')
    cats='、'.join(p.get('category') or []) or '生态项目'
    tools='、'.join(p.get('target_tools') or []) or '通用 AI Coding'
    source=p.get('source_type') or 'unknown'
    return f"{name} 是来自 {source} 的 Search in Coding 记录，关联 {tools}，分类为 {cats}。它被用于追踪 AI Coding Agent 生态中的工具、实践或资料。"

def en_summary(p):
    name=p.get('name') or p.get('id')
    cats=', '.join(p.get('category') or []) or 'ecosystem project'
    tools=', '.join(p.get('target_tools') or []) or 'general AI coding'
    source=p.get('source_type') or 'unknown'
    return f"{name} is a Search in Coding record from {source}, related to {tools}, categorized as {cats}. It helps track tools, practices, or resources in the AI coding agent ecosystem."

def enrich(rows, ids):
    changed=0
    for p in rows:
        if p.get('id') not in ids: continue
        i=p.setdefault('i18n',{}); zh=i.setdefault('zh',{}); en=i.setdefault('en',{})
        old=json.dumps(i,ensure_ascii=False,sort_keys=True)
        zh['name']=zh.get('name') or p.get('name') or p.get('id')
        en['name']=en.get('name') or p.get('name') or p.get('id')
        zh['summary']=zh_summary(p)
        en['summary']=en_summary(p)
        p['translation_state']='rule-generated'
        if json.dumps(i,ensure_ascii=False,sort_keys=True)!=old: changed+=1
    return changed

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--limit',type=int,default=60); args=ap.parse_args()
    curated=load_jsonish('data/curated-projects.yaml')[:args.limit]
    ids={p.get('id') for p in curated}
    total=0
    for rel in ['data/projects.yaml','data/curated-projects.yaml']:
        rows=load_jsonish(rel); total+=enrich(rows,ids); save_jsonish(rel,rows)
    print(json.dumps({'curated_target':len(ids),'records_changed':total,'translation_state':'rule-generated'},ensure_ascii=False))
if __name__=='__main__': main()
