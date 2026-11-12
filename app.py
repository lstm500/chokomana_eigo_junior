# -*- coding: utf-8 -*-
"""Chokomana English: alphabet -> picture-word matching -> 4-choice checks.
Run: streamlit run app.py. A single file has the complete frontend embedded.
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

APP_VERSION='1.6.3'
SOURCE_APP='english'
LEVELS={'beginner':('はじめて',1)}
GROUPS={'animals':'どうぶつ','colors':'いろ','foods':'たべもの','transport':'のりもの','nature':'しぜん','numbers':'かず'}
WORD_DATA={
 'animals':'cat|ねこ|🐱;dog|いぬ|🐶;bird|とり|🐦;fish|さかな|🐟',
 'colors':'red|あか|🔴;blue|あお|🔵;yellow|きいろ|🟡;green|みどり|🟢',
 'foods':'apple|りんご|🍎;banana|バナナ|🍌;bread|パン|🍞;milk|ぎゅうにゅう|🥛',
 'transport':'train|でんしゃ|🚃;car|くるま|🚗;bus|バス|🚌;bike|じてんしゃ|🚲',
 'nature':'sun|たいよう|☀️;moon|つき|🌙;star|ほし|⭐;rain|あめ|🌧️',
 'numbers':'one|いち|1️⃣;two|に|2️⃣;three|さん|3️⃣;four|よん|4️⃣'}
W=[]
for group,raw in WORD_DATA.items():
 for token in raw.split(';'):
  en,ja,picture=token.split('|');W.append(dict(key=en,en=en,ja=ja,emoji=picture,group=group))
LETTERS=['ABCDEF','GHIJKL','MNOPQR','STUVWX','YZ']
CAT={}
for i,letters in enumerate(LETTERS):
 key='alphabet_'+str(i+1)
 CAT[key]=(f'アルファベット {letters[0]}〜{letters[-1]}','おとを きいて、おおもじと こもじを みよう','🔤','字','じ',len(letters),len(letters)*24)
for group,label in GROUPS.items():
 CAT['matching_'+group]=(f'{label}の えと ことば','えと えいごを せんで つなごう','🧩','結','けつ',4,230)
 CAT['quiz_'+group]=(f'{label}の 4たく','おぼえた ことばを 4たくで たしかめよう','✅','確','かく',8,220)

def choices(options,right,seed):
 d={x['id']:x for x in options}
 if right not in d:raise ValueError('missing correct choice')
 out=list(d.values());out.sort(key=lambda x:hashlib.sha256((seed+x['id']).encode()).hexdigest())
 return out

def question(kind,key,prompt,cue,speech,options,correct,hint,explanation,family,skill,assessment='automatic',stage='quiz',exposure_before=False):
 return dict(question_id=f'english.{kind}.beginner.{key}',category_id=kind,difficulty_id='beginner',
  skill_ids=[skill],question_family_id=family,related_material_id='english.material.'+key,
  passage_id=None,speech_text=speech,prompt=prompt,cue=cue,options=options,correct_option_id=correct,
  hint=hint,explanation=explanation,assessment_method=assessment,learning_stage=stage,
  answer_hidden_before_response=not exposure_before)

QUESTIONS=[]
for i,letters in enumerate(LETTERS):
 for letter in letters:
  QUESTIONS.append(question('alphabet_'+str(i+1),letter.lower(),
   'おとを きいて、もじを みよう。',dict(mode='letter',text=letter,small=letter.lower()),
   letter,[dict(id='seen',text='おとを きいたよ')],None,
   'おおもじ と こもじ を みくらべよう。',f'{letter} と {letter.lower()} は おなじ もじだよ。',
   'alphabet:letter','english.alphabet.letter','guided_exposure','alphabet',True))
for group,label in GROUPS.items():
 words=[w for w in W if w['group']==group]
 for index,w in enumerate(words):
  pair=words[(index//2)*2:(index//2+1)*2]
  opts=[dict(id=x['key'],text=x['en'],speak=x['en']) for x in pair]
  QUESTIONS.append(question('matching_'+group,w['key'],
    'えと ことばを せんで つなごう。',dict(mode='picture',emoji=w['emoji'],label=''),w['en'],opts,w['key'],
    'えと おとを もういちど たしかめよう。',f'{w["emoji"]} は {w["en"]} だよ。',
    'matching:'+group,'english.matching.'+group,'automatic','matching',True))
  sound_opts=choices([dict(id=x['key'],text=x['ja'],emoji=x['emoji']) for x in words],w['key'],'sound:'+w['key'])
  QUESTIONS.append(question('quiz_'+group,w['key']+'_sound',
    'えいごを きいて、あう えを えらぼう。',dict(mode='audio',text='おとを きこう'),w['en'],sound_opts,w['key'],
    'もういちど ゆっくり きいてみよう。',f'{w["en"]} は {w["ja"]} だよ。',
    'quiz:listen:'+group,'english.quiz.listening.'+group,'automatic','quiz',False))
  word_opts=choices([dict(id=x['key'],text=x['en'],speak=x['en']) for x in words],w['key'],'picture:'+w['key'])
  QUESTIONS.append(question('quiz_'+group,w['key']+'_picture',
    'この えを えいごで なんていう？',dict(mode='picture',emoji=w['emoji'],label=''),'',word_opts,w['key'],
    'おぼえた えいごを おもいだそう。',f'{w["emoji"]} は {w["en"]} だよ。',
    'quiz:picture:'+group,'english.quiz.vocabulary.'+group,'automatic','quiz',False))

QUESTION_BY_ID={q['question_id']:q for q in QUESTIONS}
assert len(QUESTIONS)==len(QUESTION_BY_ID)==98
MENUS=[]
for kind,(label,description,emoji,stamp,reading,count,seconds) in CAT.items():
 pool=[q for q in QUESTIONS if q['category_id']==kind]
 assert len(pool)==count
 stage=kind.split('_')[0]
 if stage=='alphabet':
  idx=int(kind.split('_')[1]);suggested_prior=[f'english.alphabet_{idx-1}.beginner'] if idx>1 else [];depends=[];prerequisite_skills=[]
 elif stage=='matching':
  depends=[];prerequisite_skills=[];suggested_prior=['english.alphabet_5.beginner']
 else:
  group=kind.split('_',1)[1];depends=['english.matching_'+group+'.beginner'];prerequisite_skills=['english.matching.'+group];suggested_prior=depends
 next_ids=([f'english.alphabet_{idx+1}.beginner'] if idx<5 else [f'english.matching_{g}.beginner' for g in GROUPS]) if stage=='alphabet' else ([f'english.quiz_{kind.split("_",1)[1]}.beginner'] if stage=='matching' else [])
 MENUS.append(dict(menu_id=f'english.{kind}.beginner',label=label,category_id=kind,category_label=label,
  description=description,emoji=emoji,stamp_char=stamp,reading=reading,difficulty_id='beginner',difficulty_order=1,
  learning_stage=stage,progression_group_id=f'english.{stage}',skill_ids=sorted({s for q in pool for s in q['skill_ids']}),
  prerequisite_skill_ids=prerequisite_skills,requires_menu_ids=depends,recommended_previous_menu_ids=suggested_prior,
  selection_policy='learner_choice',planned_question_count=count,question_count=count,
  estimated_duration_ms=seconds*1000,duration_basis='provisional',duration_rationale='学習開始時の仮の時間。実施履歴によって後で調整する。',
  next_menu_ids=next_ids,age_min=None,age_max=None,age_basis=None,launch_url=None,supports_direct_launch=False,
  selection_instructions=['英語アプリを開く',label+'を選ぶ','開始する'],is_active=True))
MENU_BY_ID={m['menu_id']:m for m in MENUS}
CONTENT_VERSION='english-'+hashlib.sha256(json.dumps(dict(menus=MENUS,questions=QUESTIONS),ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]
# Integration metadata does not change the curriculum identity or reset existing progress.
for m in MENUS:
 m.update(supports_direct_launch=True,mode_options=['learn'] if m['learning_stage'] in ('alphabet','matching') else ['challenge'],question_count_default=m['planned_question_count'])
CATALOG_ROWS=[]
for m in MENUS:
 CATALOG_ROWS.append(dict(schema_version=1,source_app=SOURCE_APP,entry_type='menu',entry_id=m['menu_id'],content_version=CONTENT_VERSION,payload=m))
for skill in sorted({s for q in QUESTIONS for s in q['skill_ids']}):
 CATALOG_ROWS.append(dict(schema_version=1,source_app=SOURCE_APP,entry_type='skill',entry_id=skill,content_version=CONTENT_VERSION,
  payload=dict(skill_id=skill,label=skill.split('.')[-1],progression_group_id='english.'+skill.split('.')[1])))
for q in QUESTIONS:
 CATALOG_ROWS.append(dict(schema_version=1,source_app=SOURCE_APP,entry_type='question',entry_id=q['question_id'],content_version=CONTENT_VERSION,
  payload=dict(question_id=q['question_id'],question_family_id=q['question_family_id'],related_material_id=q['related_material_id'],
   passage_id=None,skill_ids=q['skill_ids'],assessment_method=q['assessment_method'],choice_ids=[c['id'] for c in q['options']],
   correct_answer_spec=dict(choice_id=q['correct_option_id']),category_id=q['category_id'],difficulty_id=q['difficulty_id'],learning_stage=q['learning_stage'])))

def now():return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z')
def valid_uuid(x):return str(uuid.UUID(str(x)))
def device_hash(x):
 if not isinstance(x,str) or not re.fullmatch('[a-f0-9]{64}',x):raise ValueError('端末IDが不正です')
 return hashlib.sha256(('english:'+x).encode()).hexdigest()
def https(x):
 p=urlparse(x)
 return bool(p.scheme=='https' and p.netloc and not p.username and not p.password)
def server_client(url,key):
 from supabase import create_client
 return create_client(url,key)
def claim_identity(client,device,ticket=None):
 dh=device_hash(device)
 if ticket:
  if not isinstance(ticket,str) or not 24<=len(ticket)<=256:raise PermissionError('起動チケットが不正です')
  result=client.rpc('english_claim_launch_v1',dict(p_device_hash=dh,p_ticket_hash=hashlib.sha256(ticket.encode()).hexdigest())).execute().data
  return valid_uuid(result),True
 rows=client.table('english_device_links').select('profile_id').eq('device_hash',dh).limit(1).execute().data
 if not rows:
  client.table('english_device_links').upsert(dict(device_hash=dh,profile_id=str(uuid.uuid4())),on_conflict='device_hash',ignore_duplicates=True).execute()
  rows=client.table('english_device_links').select('profile_id').eq('device_hash',dh).limit(1).execute().data
 if not rows:raise RuntimeError('端末の紐づけを確認できません')
 return valid_uuid(rows[0]['profile_id']),True

def verified_plan_launch(client,ticket,profile):
 rows=client.table('chokomana_launch_tickets').select('profile_id,source_app,used_at,plan_item_id,menu_id,content_version,launch_mode').eq('ticket_hash',hashlib.sha256(ticket.encode()).hexdigest()).limit(1).execute().data or []
 if len(rows)!=1 or str(rows[0]['profile_id'])!=str(profile) or rows[0]['source_app']!=SOURCE_APP or not rows[0].get('used_at'):
  raise PermissionError('起動情報を確認できません')
 row=rows[0]
 if not row.get('plan_item_id'):return None
 if row.get('menu_id') not in MENU_BY_ID or row.get('content_version')!=CONTENT_VERSION:
  raise ValueError('教材が更新されています。ちょこまなで学習記録を更新してください')
 return dict(plan_item_id=valid_uuid(row['plan_item_id']),menu_id=row['menu_id'],content_version=row['content_version'],nonce=hashlib.sha256(ticket.encode()).hexdigest())


def publish_catalog(client,url=None):
 for start in range(0,len(CATALOG_ROWS),150):
  batch=[]
  for original in CATALOG_ROWS[start:start+150]:
   row=dict(original)
   if row['entry_type']=='menu':row['payload']=dict(row['payload'],launch_url=url if url and https(url) else None)
   batch.append(row)
  client.table('chokomana_learning_catalog').upsert(batch,on_conflict='source_app,entry_type,entry_id,content_version').execute()

def list_history(client,profile):
 result=[];offset=0
 while offset<2000:
  rows=client.table('english_attempts').select('payload').eq('profile_id',profile).order('started_at',desc=True).range(offset,offset+199).execute().data or []
  result.extend(x['payload'] for x in rows)
  if len(rows)<200:break
  offset+=len(rows)
 return result

def calculate_summary(raw):
 if not isinstance(raw,dict):raise ValueError('記録が不正です')
 menu=MENU_BY_ID.get(raw.get('menu_id'))
 if not menu:raise ValueError('メニューが存在しません')
 attempt=valid_uuid(raw['attempt_id']);response=raw.get('responses')
 if not isinstance(response,list) or len(response)>menu['planned_question_count']:raise ValueError('回答数が不正です')
 seen=set();clean=[];correct=0;objective=0;spoken=0
 for a in response:
  q=QUESTION_BY_ID.get(a.get('question_id'))
  if not q or f"english.{q['category_id']}.{q['difficulty_id']}"!=menu['menu_id'] or q['question_id'] in seen:raise ValueError('問題が一致しません')
  seen.add(q['question_id']);selected=a.get('selected')
  if selected not in {c['id'] for c in q['options']}:raise ValueError('選択肢が不正です')
  first=None
  if q['assessment_method']=='automatic':
   objective+=1;first=(selected==q['correct_option_id']);correct+=int(first)
  else:spoken+=int(selected=='seen')
  clean.append(dict(question_id=q['question_id'],selected=selected,first_is_correct=first,
   skill_ids=q['skill_ids'],family_id=q['question_family_id'],support_before_response=a.get('support_before_response') or {},
   answer_latency_ms=a.get('answer_latency_ms'),reanswers=a.get('reanswers') or []))
 status=raw.get('status')
 if status not in ('completed','in_progress','abandoned','interrupted'):raise ValueError('実施状況が不正です')
 if status=='completed' and len(clean)!=menu['planned_question_count']:raise ValueError('完了の回答数が不正です')
 grade='white'
 if status=='completed' and objective==len(clean) and objective:
  r=correct/objective
  grade='gold' if r==1 else 'silver' if r>=.8 else 'bronze' if r>=.6 else 'white'
 return dict(attempt_id=attempt,menu_id=menu['menu_id'],category_id=menu['category_id'],difficulty_id=menu['difficulty_id'],
  content_version=CONTENT_VERSION,status=status,started_at=raw['started_at'],finished_at=raw.get('finished_at'),
  responses=clean,first_correct_count=correct,objective_count=objective,self_report_success_count=spoken,
  answered_count=len(clean),planned_question_count=menu['planned_question_count'],grade=grade,
  duration_ms=max(0,int(raw.get('duration_ms') or 0)),timing_quality=raw.get('timing_quality') or 'unknown')

def normalize_events(events,profile,content_version=CONTENT_VERSION,app_version=APP_VERSION):
 if not isinstance(events,list) or len(events)>100 or len(json.dumps(events,ensure_ascii=False).encode())>262144:raise ValueError('送信イベントが不正です')
 allowed={'session_started','item_presented','response_submitted','support_used','time_interval_closed','session_paused','session_resumed','session_ended','learning_activity'}
 out=[]
 for raw in events:
  p=raw.get('payload')
  if raw.get('event_type') not in allowed or not isinstance(p,dict):raise ValueError('イベントが不正です')
  q=QUESTION_BY_ID.get(raw['question_id']) if raw.get('question_id') else None
  if raw.get('question_id') and not q:raise ValueError('問題が教材にありません')
  event_type=raw['event_type'];p=dict(p)
  if event_type=='session_started':
   m=MENU_BY_ID.get(p.get('menu_id'))
   if not m or p.get('category_id')!=m['category_id'] or p.get('difficulty_id')!=m['difficulty_id'] or p.get('planned_question_count')!=m['planned_question_count']:
    raise ValueError('メニューの記録が一致しません')
  if event_type in ('item_presented','response_submitted') and (not q or not raw.get('occurrence_id')):raise ValueError('出題記録が不正です')
  if event_type=='item_presented':
   if sorted(p.get('choice_order') or [])!=sorted(c['id'] for c in q['options']):raise ValueError('選択肢が一致しません')
   p.update(skill_ids=q['skill_ids'],question_family_id=q['question_family_id'],related_material_id=q['related_material_id'],passage_id=None)
  if event_type=='response_submitted':
   chosen=(p.get('response_value') or {}).get('choice_id')
   if chosen not in [c['id'] for c in q['options']]:raise ValueError('回答が不正です')
   if p.get('response_index') not in (1,2,3):raise ValueError('再回答回数が不正です')
   is_auto=q['assessment_method']=='automatic'
   p.update(is_correct=(chosen==q['correct_option_id'] if is_auto else None),assessment_method=q['assessment_method'],
     correctness_basis='catalog_exact_choice_v1' if is_auto else 'self_or_parent_confirmation',
     input_method=('tap_to_connect' if q['learning_stage']=='matching' else 'choice') if is_auto else 'guided_exposure',response_status='answered',
     self_report_success=chosen=='seen' if not is_auto else None)
  if event_type=='time_interval_closed' and p.get('timing_quality')=='complete':
   ex=p.get('excluded_ms') or {};elapsed=p.get('elapsed_ms');active=p.get('active_ms')
   if type(elapsed) is not int or type(active) is not int or active<0 or active+sum(ex.get(k,0) for k in ('hidden','explicit_pause','blocking_wait'))!=elapsed:
    raise ValueError('時間が一致しません')
  if event_type=='session_ended' and p.get('status') not in ('completed','abandoned','interrupted'):raise ValueError('終了状態が不正です')
  occurred=raw['occurred_at']
  if not isinstance(occurred,str) or not occurred.endswith('Z'):raise ValueError('UTC日時が不正です')
  parsed=datetime.fromisoformat(occurred.replace('Z','+00:00'))
  if abs((datetime.now(timezone.utc)-parsed).total_seconds())>86400*7:raise ValueError('端末時刻を確認してください')
  record=dict(schema_version=1,event_id=valid_uuid(raw['event_id']),profile_id=profile,source_app=SOURCE_APP,
   app_version=app_version,content_version=content_version,attempt_id=valid_uuid(raw['attempt_id']),
   occurrence_id=valid_uuid(raw['occurrence_id']) if raw.get('occurrence_id') else None,
   question_id=raw.get('question_id'),segment_id=valid_uuid(raw['segment_id']),
   sequence=int(raw['sequence']),occurred_at=occurred,event_type=event_type,payload=p)
  record['event_hash']=hashlib.sha256(json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()
  out.append(record)
 if len({r['event_id'] for r in out})!=len(out):raise ValueError('イベントIDが重複しています')
 return out

def validated_completion(client,profile,summary):
 rows=client.table('chokomana_learning_events').select('event_type,question_id,occurrence_id,payload').eq('profile_id',profile).eq('source_app',SOURCE_APP).eq('attempt_id',summary['attempt_id']).execute().data or []
 menu=MENU_BY_ID[summary['menu_id']]
 starts=[r for r in rows if r['event_type']=='session_started' and r['payload'].get('menu_id')==menu['menu_id']]
 ends=[r for r in rows if r['event_type']=='session_ended' and r['payload'].get('status')=='completed']
 if not ends:return False
 if len(starts)!=1 or len(ends)!=1 or ends[0]['payload'].get('answered_count')!=menu['planned_question_count']:
  raise ValueError('完了ログが一致しません')
 presents=[r for r in rows if r['event_type']=='item_presented' and r['payload'].get('parent_occurrence_id') is None]
 roots={r['occurrence_id']:r for r in presents}
 if len(roots)!=menu['planned_question_count'] or len({r['payload'].get('position') for r in presents})!=len(roots):raise ValueError('出題が不足しています')
 firsts=[r for r in rows if r['event_type']=='response_submitted' and r['payload'].get('response_index')==1]
 if len(firsts)!=len(roots) or len({r['occurrence_id'] for r in firsts})!=len(roots):raise ValueError('初回回答が不足しています')
 expected={x['question_id']:x['selected'] for x in summary['responses']}
 if len(expected)!=len(firsts):raise ValueError('回答問題の重複があります')
 points=0
 for x in firsts:
  root=roots.get(x['occurrence_id'])
  if not root or root['question_id']!=x['question_id'] or expected.get(x['question_id'])!=(x['payload'].get('response_value') or {}).get('choice_id'):
   raise ValueError('初回回答が一致しません')
  points+=int(x['payload'].get('is_correct') is True)
 if points!=summary['first_correct_count']:raise ValueError('正答数が一致しません')
 return True

def save_records(client,profile,device,events,raw_summary,plan_launch=None):
 if claim_identity(client,device)[0]!=profile:raise PermissionError('学習者が一致しません')
 summary=calculate_summary(raw_summary)
 # Older interrupted lessons may have already written part of their event stream.
 # Use that original immutable event version for the rest of the same attempt.
 previous=(client.table('chokomana_learning_events').select('content_version,app_version,event_id,event_type,payload')
  .eq('profile_id',profile).eq('source_app',SOURCE_APP).eq('attempt_id',summary['attempt_id'])
  .limit(20).execute().data or [])
 versions={(x['content_version'],x['app_version']) for x in previous}
 if len(versions)>1:raise ValueError('同じ学習内で教材の版が一致しません')
 prior_content,prior_app=next(iter(versions)) if versions else (CONTENT_VERSION,APP_VERSION)
 summary['content_version']=prior_content
 # Assignment comes only from the consumed server-side ticket, bound to this menu/version.
 safe_events=[]
 for event in events:
  event={**event,'payload':dict(event.get('payload') or {})}
  if event.get('event_type')=='session_started':
   raw_plan_id=event['payload'].pop('plan_item_id',None)
   existing=next((r for r in previous if r.get('event_id')==event.get('event_id')),None)
   if existing and (existing.get('payload') or {}).get('plan_item_id'):
    event['payload']['plan_item_id']=existing['payload']['plan_item_id']
   elif plan_launch and raw_plan_id==plan_launch.get('plan_item_id') and event['payload'].get('menu_id')==plan_launch.get('menu_id') and prior_content==plan_launch.get('content_version'):
    event['payload']['plan_item_id']=plan_launch['plan_item_id']
  safe_events.append(event)
 validated=normalize_events(safe_events,profile,prior_content,prior_app)
 if any(x['attempt_id']!=summary['attempt_id'] for x in validated):raise ValueError('実施IDが不一致です')
 if validated:
  olds=client.table('chokomana_learning_events').select('event_id,event_hash').in_('event_id',[x['event_id'] for x in validated]).execute().data or []
  lookup={x['event_id']:x['event_hash'] for x in olds}
  if any(lookup.get(x['event_id'],x['event_hash'])!=x['event_hash'] for x in validated):raise ValueError('イベントIDの内容が異なります')
  client.table('chokomana_learning_events').upsert(validated,on_conflict='event_id',ignore_duplicates=True).execute()
 completed=validated_completion(client,profile,summary) if summary['status']=='completed' else False
 state=dict(summary,status=summary['status'] if summary['status']!='completed' or completed else 'in_progress')
 old=client.table('english_attempts').select('status').eq('attempt_id',summary['attempt_id']).limit(1).execute().data
 if not(old and old[0]['status']=='completed' and state['status']!='completed'):
  row=dict(attempt_id=summary['attempt_id'],profile_id=profile,menu_id=summary['menu_id'],
   category_id=summary['category_id'],difficulty_id=summary['difficulty_id'],content_version=summary['content_version'],
   started_at=summary['started_at'],finished_at=summary['finished_at'] if state['status']=='completed' else None,
   status=state['status'],duration_ms=state['duration_ms'],payload=state)
  client.table('english_attempts').upsert(row,on_conflict='attempt_id').execute()
 stamped=False
 if completed:
  m=MENU_BY_ID[summary['menu_id']]
  medal=dict(profile_id=profile,source_app=SOURCE_APP,attempt_id=summary['attempt_id'],
   category_key=m['category_id'],category_label=m['category_label'],stamp_char=m['stamp_char'],reading=m['reading'],
   difficulty=m['difficulty_id'],correct_count=summary['first_correct_count'],total_count=m['planned_question_count'],
   grade=summary['grade'],finished_at=summary['finished_at'] or now())
  client.table('chokomana_stamps').upsert(medal,on_conflict='profile_id,source_app,attempt_id',ignore_duplicates=True).execute()
  rows=client.table('chokomana_stamps').select('attempt_id').eq('profile_id',profile).eq('source_app',SOURCE_APP).eq('attempt_id',summary['attempt_id']).limit(1).execute().data
  stamped=bool(rows)
  if not stamped:raise RuntimeError('メダルの保存を確認できません')
 return dict(event_ids=[e['event_id'] for e in validated],summary=summary,medal_saved=stamped)


def component():
 import streamlit.components.v1 as components
 root=Path(tempfile.gettempdir())/('cm_english_'+hashlib.sha256(FRONTEND.encode()).hexdigest()[:12]);root.mkdir(exist_ok=True,parents=True)
 target=root/'index.html'
 if not target.exists():target.write_text(FRONTEND,encoding='utf-8')
 return components.declare_component('cm_english_'+hashlib.sha256(FRONTEND.encode()).hexdigest()[:12],path=str(root))

from base64 import b64decode as _frontend_b64decode
from zlib import decompress as _frontend_decompress
# Embedded HTML frontend. No separate frontend.html file is required.
_FRONTEND_B64 = (
    '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'
    'd+F/A7scvfU='
)
FRONTEND = _frontend_decompress(_frontend_b64decode(_FRONTEND_B64)).decode('utf-8')

def main():
 import streamlit as st
 st.set_page_config(page_title='ちょこまな（英語）',page_icon='🔤',layout='wide',initial_sidebar_state='collapsed')
 st.markdown('<style>.stApp{background:#f7f5ef}.block-container{padding:.3rem!important;max-width:1180px!important}header[data-testid="stHeader"]{display:none}</style>',unsafe_allow_html=True)
 def secret(k):
  try:return str(st.secrets.get(k,'')).strip()
  except Exception:return ''
 url=secret('SUPABASE_URL');key=secret('SUPABASE_SERVICE_ROLE_KEY') or secret('SUPABASE_SECRET_KEY')
 hub=secret('CHOKOMANA_HUB_URL') or 'https://chokomana-hkgx4uyxxezjtr2sj35jwj.streamlit.app/'
 app_url=secret('ENGLISH_APP_URL') or 'https://chokomanaeigojunior-wuyqysc66uknyiyvpdvaw2.streamlit.app/'
 client=None;err=None
 def diagnose(stage,exc):
  # Log only the stage and exception class; never include URLs, credentials or child data.
  import logging
  logging.getLogger('chokomana_english').warning('operation=%s error_type=%s',stage,type(exc).__name__)
  return f'{stage}（{type(exc).__name__}）'
 if not url or not key:
  missing=', '.join(x for x,found in [('SUPABASE_URL',bool(url)),('SUPABASE_SERVICE_ROLE_KEY または SUPABASE_SECRET_KEY',bool(key))] if not found)
  err=f'Streamlit Secretsの設定が不足しています：{missing}'
 elif not https(url):
  err='SUPABASE_URLが有効なHTTPS URLではありません。'
 else:
  try:client=server_client(url,key)
  except Exception as e:err='Supabase初期化に失敗：'+diagnose('client_init',e)
 if st.query_params.get('cm_launch'):
  ticket=str(st.query_params['cm_launch'])
  fingerprint=hashlib.sha256(ticket.encode()).hexdigest()
  if fingerprint!=st.session_state.get('launch_instance'):
   for name in ('identity','last_hello','last_seq','ack','device','plan_launch'):
    st.session_state.pop(name,None)
   st.session_state['launch_instance']=fingerprint
   st.session_state['pending_launch']=ticket
 ctx=st.session_state.get('identity')
 args=dict(menus=MENUS,questions=QUESTIONS,version=CONTENT_VERSION,hub_url=hub if https(hub) else '',identity_ready=bool(ctx),linked=False)
 if ctx:args.update(ctx)
 if st.session_state.get('plan_launch'):args['plan_launch']=st.session_state['plan_launch']
 if st.session_state.get('ack'):args['ack']=st.session_state['ack']
 event=component()(**args,key='cm_english_board_v162_'+st.session_state.get('launch_instance','standalone')[:16],default=None)
 if not isinstance(event,dict):return
 if event.get('action')=='hello':
  if event.get('hello_id')==st.session_state.get('last_hello'):return
  st.session_state['last_hello']=event.get('hello_id');device=event.get('device')
  try:proof=device_hash(device)
  except ValueError:return
  profile='local:'+proof[:32];linked=False;history=[];message=err
  if client:
   ticket=st.session_state.get('pending_launch')
   try:
    profile,linked=claim_identity(client,device,ticket)
    if ticket:
     st.session_state['plan_launch']=verified_plan_launch(client,ticket,profile)
     st.session_state.pop('pending_launch',None)
     if 'cm_launch' in st.query_params:del st.query_params['cm_launch']
   except Exception as e:
    message='Supabaseの学習者識別に失敗：'+diagnose('claim_identity',e)
    profile='local:'+proof[:32];linked=False
   if linked:
    # A metadata read or publication failure must not undo a verified learner identity.
    warnings=[]
    try:history=list_history(client,profile)
    except Exception as e:warnings.append('学習履歴取得：'+diagnose('list_history',e))
    try:publish_catalog(client,app_url)
    except Exception as e:warnings.append('教材一覧更新：'+diagnose('publish_catalog',e))
    message=('Supabaseとの識別は成功しました。一部の処理を確認できません：'+'、'.join(warnings)) if warnings else None
  st.session_state['device']=device
  st.session_state['identity']=dict(profile_id=profile,linked=linked,history=history,
   link_message=(message or ('Supabaseに保存できます' if linked else '端末内のみ保存・ちょこまな未連携')))
  st.session_state['ack']=None;st.rerun()
 if event.get('action')=='sync' and ctx:
  seq=event.get('seq')
  if type(seq) is not int or seq<=st.session_state.get('last_seq',0):return
  st.session_state['last_seq']=seq
  ack=dict(seq=seq,profile_id=ctx['profile_id'],success=False)
  if ctx['linked'] and client and event.get('device')==st.session_state.get('device'):
   try:
    result=save_records(client,ctx['profile_id'],event['device'],event.get('events') or [],event.get('summary'),st.session_state.get('plan_launch'))
    ack.update(success=True,**result)
   except Exception as e:ack['message']='DB保存に失敗：'+diagnose('save_records',e)+'。端末の未送信記録を保持します。'
  else:ack['message']='端末内保存のみ。ちょこまな未連携です。'
  st.session_state['ack']=ack;st.rerun()

if __name__=='__main__':
 if '--catalog-count' in sys.argv:
  print(json.dumps(dict(menus=len(MENUS),questions=len(QUESTIONS),skills=sum(r['entry_type']=='skill' for r in CATALOG_ROWS),content_version=CONTENT_VERSION),ensure_ascii=False))
 else:main()
