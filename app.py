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

APP_VERSION='1.6.2'
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
    'eNrVvXufI0eVKPh/f4rstqlU0imVpJJUKqlVdY2xwffa2Ou2mZ3tW1OdklKldEtKtVLq7kKl36+r2+MxYA8MMBgYLoYLw3jw2gwz'
    'O1weXvxdKGzMX8xH2POIiIzIh6q67dn9LY8uZWY8T5w4rzjnxJWLn3328Rf+8rknrOF8PNq9gv9aI29y2Ln0kncJnn2vv3tl7M89'
    'qzf0ZpE/71x68YUni81L4u3EG/udS7cC//Y0nM0vWb1wMvcnUOp20J8PO33/VtDzi/TgBpNgHnijYtTzRn6n4spaxUEw7/TCW/7M'
    'bHU+9Md+sReOwpnW8COD7UHdH0DReTAf+bunJz86vfc3pyffPD353enJz/783qsfffUXH/3sB39+78tXNrnIhSvR/Aj/tmZhOF8W'
    'i93DlmimXSzO/Tvz1iPVWnWrgo/jxdzvtx7ZrjX6jSo8j4KJ33qk7/e3ex48TrxbR61Htir1QbMBj1OYSusRvz+oDfDr4cz3J61H'
    '6uXtXqMOz7e92Ri6Ggx2fJ9KT/0ZPa8ufHrZDe8Uo+BLweSw1Q1nfX9WhDcrXIJl1JuFo1Gx6w+9W0E4a0VjGPhw1Q37R8uxNzsM'
    'Jq1yu+v1bhzOwsWk37rlzQo4LadN4BLPODOnPQDIFQfeOBgdtaKjaO6Pi4vALXrT6cgv8gvX/nww86DV0LrqTSLbtf9yYX0Oegx6'
    'thvBm2Lkz4JBG2FRHPrB4XDeqpQaqwvdxXweTtzIH/m9OSzwdDFfYn+tYDKEGvMVF1j2FrMIhjUNA1jFWXseLnrDotebB+GkNfYm'
    'wXQx8vChzYDAyTFEZl4/WEStSnV6hydym3vfrpfb42AiB1NrwPep1+8jMCvl6R2rUoc3GoQe8Xf8Wt9Lw0cMsdUPIq878vvLcOr1'
    'gvlRq1RrtsW4J+G86I1G4W2/L4sPwt4iKt4KogAquV7imQFivlyGizkh0xYMLwpHQd96pFtv9mu1tvhSDAcD2GItmOzqwtgLJrDW'
    'd3jztHaqMKu2WHtvMQ/j6VbFdK2tJlQszcMpIOkS5jMdeUetwci/0/ZGweGkGMBSR62eT2vw0iKaB4OjothYrQim7QPGzW8DCrcP'
    'vWmriTCH2sXbM3jCf2T/NeisbGm9Wd5ShzUguFzJiposwxzn6SRXt6Kt3g7OBpdbXyncdQKTYcf4rcpWBj7gchb7fi+cES7Bqk38'
    'Vak78yb9IuBKsNQrNKEC9yA388ifA1yKCAccR6lc9cerUjT35otoqXWdHBsRDKd9FrwRonWEGLdolfpAigT6IqR5mfGXCZx6+VOq'
    '7WBCaNIdhb0bBnL3drxeY0u2XeqNwkWfe9BL1fxms1FbXRhWlgQrGqUcXzzD3sgbTwtVGIpbv3Xb3YIVcdLQ2fLHEh0qjA9bOLsR'
    'cIy1rWNhCfnGoOE1KrKZMrRR2cFGgHaExsgFgU3h1CPdnd6g302AjLaK2h5NRKidePMg7hg9WcOqtr76PsMR1VWxqSS9uNfKOVOq'
    'NxqN7Yaogesxm4tqRdgqRJtWF0pTb+KPlikCTvzBeZCtY0xVHzqvyYp7Wj9DxGhVcEtH9e24oNGcgkST39IWWCa2Z3qPrEoDmIJe'
    'rhIDrtlt1re7QFC8w2UmvieYj0ncfX+nP1gHG1x0BH47sZMNIlJWNKGxUx/Ut2g00P3CN7GxPigPtk3ywUWJ/5tlm4MtvyvL1hrb'
    'lXodEGDk3/JHkUmkJc1FSWgAzMYk81XG2jJvMqi9xEqtCrFBwSNqJs+7PQQKpLCpVM/EJypE+9oHiklU3sRs0V0J2fUtP420TJt5'
    'gnqPxRQBh3n3vFk/nvbhLOi38R9gxWN4MydxbzGeRK2ZP/W9eaHqwvSACxbKbmUwcxwCEiPsOOz7y3jy5XPN/JH+Tr/aayQZUFMn'
    'GA1EFcRgjYyN/MHcJPHEGfvBzGcphsdNw8OqmmxSqdfkcIEgHI274UjfjI34I4q9+u5oJvATeZa5C7bqsm7fj3rZXOqR7S0QZbeM'
    'lurlZEv1NqOTbK8bgpgzNhF0vciQw/Oa5p7TdjzQ/kZ90Naoo4JFaQCLv5gBUcnlAkWTe5MwPfT6sG2CCQhRVpn+izRU7VBsuSXQ'
    'eA5iQTQIQTynX4h7f1mA0o4UakvTWQBDOzoHwoOQMZ8UD4dhZPBbEwkzN196i1BTUTiYZ808pzhqGUn5a9tvqvXvNSrVDIHsEWDV'
    '215zVYIN5C95F1XK5U+tSjNECsm2EPWJFK1KLLFnkC2mrFmyInM9YqKi9u6n05SrwiUEvc/tBnEpA83MjoHKgLwOaucyY8a1ftXr'
    'pzUnhGBKKq3pRIGE7JqJy7jRk1xJst8yc8abi8A3l3JQHzQGW1mrUfHrfT9L8VGDqEjZ2BwEzHgehqOuN/uY+zWxgghyTQQgGJRX'
    'si8UKqQUAYLBLATmF0W6SJuYSjmpkdX6g349ZnfDoN/3J3FTuzDeiZpRWugVO18CHzC3TXs5IIJMiGWVKo0IV8GP8GUR7RmfgGbE'
    'a5CJ7kw3BYvqwUChRVPxKJeTkgNMeDydn0cmBwRwayWSyssolSe5g1ypHRYWiPH0QHpJN22g5M6gOagll2tbraCBpX2StBRK1hP4'
    'gYSCN4rOAnG07QeFu46UmYy2IaZnlVDKTgIL2a5bqQCsmgQrc6fWRM3bMMNltu5DcK5Vs+Cc1hXrqCxSi9GiS2anpSS/3na94aeE'
    'Km/RD8LlQ8JEEsOYaLdNsV20b0W3DiVlx/Jy+k1Vogi00l+vsOmiRG+70ejLBW8QPQChbhgCuf34Yl2F1pMaW05DsY9nPpqGbvlt'
    'XdTTcGtnJ0mmY9JDQnOGCpXk0Z84ZtZSnKHWTsNYUj6mIt7k6DZojb4EgVXyx+FLgYacW9VUs1txaf5LRq0UQqNM626VtgGhq1kI'
    'rVqJxt5olKehec3qdiMpR8qqQOxmCAlTbvEGdb+fkNjqftNvdFW927NwcpgUX8qpWl1/u9noy1ppc10lhkSEzRR5KgqPvC4gAqih'
    'bRRIkGqRkIM4nLADZWh6JmVsprVIXUlrEEMe+H4fWzKU/1qaKdZSmkcjySZZ9tN6bKTQYHulOiyFNzKWQPve9fpJaG/5O3EBK5rT'
    'ipgGA+17yb8DuyWYLHOMOtV6v15PifXDYGJYQpopi+1WYuJkNs8y+gAHani9XBOxRmQJB4ogIy91Y3E5LcbJkTSFhAUrCCLIYjQv'
    'ki0qtXdX+ueEeYVYv/g8WYy7UgDgPbyTUOp2UqoY7Omx3/dGSiRvaJSbHvIthJ8IBUvyc7kEqEb3wwVsO+sRWKitnqevF47GGxUP'
    '8S+0XugFsx6U9ObWVvlTVqX5KZeIrfuI3/P9QdnaLn/KfaS309/q950s9a0ulsJCRGi6ZUvuDuuRSrkyqHYrXQEoq8T8eC2Y63lg'
    'tmCtPFz85TrTENJIKl46DEfGBsqfd7UO867DLHECvS78rfUrDZgZvutVmn5120lSuUqzW62prVSrNcpylqUoGAHDOGfXZe5agLzv'
    '+Vt+nzve2fF2us1kxztA3btKZdzy61uNpuy4C/TgS/6DdYxzrvR7sNo1z29WuWuv12jWyqk5l7f7dWVOa1S2+tWq7JrGLyWpeq1R'
    'aQxAAbkdflxZoykt8SYp3AbdrJokLAlTkNg6inZtscjBzUniaWotSeLQD26Byj1bJk+7iElodK7pb/V7ajsKY+s8GPuIyefTwtO0'
    'ANRsPAOkJtS5IystWte+3wRl1CDQ5fYnozlpA2iNvGhe7A0D3FLGWPjwRhVMMyUm8HGBtBG6QmQciMkcplCchbc/Cc2vljiqUmuX'
    'B8OVPoL0fMVEtTIWHx4uZS/bUul/0BO1lJibAN6F0jjozc7WQYSqtZaHxNYXbhSPPvLMkagP9UCeCEOk2WtVD0363PF3tps9Xawg'
    'seTCNTYb7KtpIEAvBmP0LPAm89WF/wKUJPCsQnyWWifleUknrMaxI4J2q6xOQ9THyraST1I6sjit0hXilTBzK0JDpmqDYNDMdA25'
    'Vs+3A2sm4qSZV1eZdKUoZTaqxQXzVAWejWkrUWq2NDAJYrTNtCg26ZmnEGvkH7RXyUUpTGf+wJ9FxZnfX/T8fnEcCp0PH51lpi8E'
    'myJNI5Fm96H9tLqAG58GV2RlPPv4q8pngTW1Zhabn5Fq664AIM8aMvXA7/o1OsYhOwCaWPTF3BGnNPgxSilj+NWt1kAXq7B1wZRL'
    'Kinx8Ixz6grZHkRvFsFDMsytbX8Hj5sAzuhtU5x6wew8rBMYpQX/10i2bAGhZPLMxqA5aGRI6f26X0+dyZHuco5zlPwD9Bita5Lx'
    '6mNL2oK2y6kSaf2mnioj/FZSdtaxN0fPFZAYMywU5wCsIYpYxhNNkDFkq46mqypiSINsVxJdURyu8m7WqUd1u6yNjvtangPKa6xL'
    'ZLH7UjGY9MWpEDU9D2ArSUzVCKJmaIF173dBasn2BzGsiw+ptGhGL01tU9PHMSaxoFFPqsz6jMgIyHNLWQLL0guinGk20Rphtu0r'
    'QWaNVaExqAw8ozL9TNWt+zs7Db+dUOdrvi9JQqVXB2bW1mwgcZuZJhL+jJCIMkwjcr3LbVLC4K/w2Cr6twD2ERNXSbw1hlolhqrv'
    'DsShKjM/HSmJoDTi1wZClZvmh+Qq8kHqut2OuwWJ/+anLVCVSqDktaxeOIb5z61hOAYNZdK3FpNgEIA2NAF+ckiuQq6FVB9AZYUT'
    'QONZ2PUmdmSBniHGTd+jkvXpzWwfwtixL+0iKBwIQdHtNVcXdJYmsDd2DCH/voTdsJ52BWuUU7YTVIurNXEURP5fmoNH06QWWw1D'
    'TeBDf1WxOBLasG5vPY+IKMwm0iGsNFx0ERSmHFs2h1Krpm1pGQ4JGX585kbxK30onjhXuZDy/YrtPelOlKvXeocIVioQl844TOp6'
    'Ealpsdqgew9Zgp+ohqxhJeEVkBALqsplJ+WXkDfi2PQhe2J7WLTo5snm7PWaNJRcKE2wS2CcwdQl0Q7bwidd7NluPARNzzlcy3Ld'
    '8Oq9cr/WzvcIkLylnjozrSU8nraUhU9NxESofq2706wmmVjTb66MWlbJP/K7qFoqL6ZGrbotAdb3514wikyQ7YL2n7+5zhaHqAQ5'
    'ljG4aCpyGHl2B9p40gmp2uiDJnWGZ0liDkJqMqeSoZVvp48o6nkHHaIHgAUwn5xDh+1qo4c+ixIDYdqJMQhRTXcmSFKZpNJO+HC2'
    '4xPoEHN/WpwDf3wAe9NWjr3JQECz+Y97DKjPbduce72atqpnO0Y1eoNeNcuoHtv1e/Va+2xCGs8rw2cs9tfJEJLEE/nHcyNCf/xY'
    'kiJKzdJ+XlUn99FwFkxupDzNt5OnLz4wnMo6r0FNQ6v369u1fhoAljGZ5GokuRZXjrVW/Xw/JhsrLkcuBsm9o/TW7Wo74XtA7XuH'
    'Wdzrgd1FNITeEfgsWzaPRDJOrLb02hkgNVubrudXijOmadjIj6JwUsQd+3H3MM9RNEh68LnEonKGJ2HOWfZ2OozBYIa1hB/j9lla'
    'VuyHKwJczAkAIQXpeOyD0J+ntpzpVmcOoQoicTfRSdKY0kgMu4x7TFGZRn2A1pa4X9Y5Mlq05DvhVGmqWH61rxrdbjT8hoYN0gvT'
    'oAMfi8bQeZOUr3fO4fvkgQqYcCHWjwkqKX01MXhpeko5lBIHTp18mTajYqnc9Mdxk6R3fDwxRDq9SqwW3qRGFxniQj2DMORKC0ZT'
    'saOC9EWIIzq2y41mfZA0JOcSh4j8H9eKA5r41Og2vMaWgAXI+AMGBWyi/M1lGV1lrHoGgSbHHDmhCgVKrJ1QrW44H1ZYFpCSPx9P'
    'pFwrz2sD1CMLWIEpZ7esi2NS/NrK8lgEJSQVpqTE/3xm09Tc4LmJDKxqCvG+h3YdEWuRtk9ySN8ZFNSgyHW93Z43xRmfjzPJMAtV'
    '+wEZUu4hpmoQgfUJHHBtr+VA2uHWVr/fr2WJiwZAuwMPyJwuthgD1rQK7R1tbVOTSbu9p1tJWmszGs3RMZA91PSjpVqyehqrt5oG'
    'xduu5QjDm5+2nva92QQA6mIU6wRJ6uSQLFFomgLSHKDVqYehI6BmDb2Zr9mghPXKtUYwOr/IkZNz/D2HV0fhYk5WqczzGZLK5Jfd'
    'jI2ZddTViHf6tn6+qW0IWEPzlMj0fRU2efJpzbSnbpFnZXVbs2yTmi729YVS8jxFJz9N5WRaTaAq+V/mHcnUtoX0ln0mgwZ0t9JE'
    'izu266zzK8WiO1Cy0aRwAeHJmReN2hT6ZtYx3XYzfs/HhTu6p9VSd2s0/OkrhkNWHgGUxD5VU7PT6qcIKWdeOhnTziVqBKUyQons'
    '4ckjh3XW3Z1qWiqqnsPemzi8ktwocSKla8CNs6zE9fOcCaWdwGILbKNRznB7Nvz41jmIJbCZIycvrD8yNVzCmppG26ym98Yav6iK'
    'aivT76mc8pnQzbflDNt/g7yrlxcs4zi9KYy9Fju86FrYQ/I5SzO6GmHIRBzU3skzqNbVx0wbaIW7yDdzmt79idP77a2MAOaVZj2S'
    'LhQZQQIXrNgMpMM6EUVWa4pZ1lMW85VhXRA2ME0fqeykQrDyjAdlHpCu466bphzTtrbGQiERalFNU4sS0TPNVKV8naZujCtHl6hp'
    'DSZ1hHh6hiQef9vhHnTpLFcsXpmipW5qTrHTrbP4kgB5mmA269mnZ/V8Ci4cD/Ipao2mmbGLt7brdIKXDnenFrMPUipxAgB1aqQ5'
    'jOScAzXS2KjvAaFM5mAo7fEMu3QSWTRzcdI1ZXWBzwdBY2pZ4cTHbCMokIlUGPRKxP5ZICPDv4NwZvleb2gx6rQtYX/AEUaW8IaG'
    'OqCl3lwEEciAfFTI9AbaY2c7UzNIqA1rbGn6UZ5QfHIsY1taQ8n4znrCdpUSQ87cXPkK9Hp1N8P6Gxt6M3zrJaLUlAabvWVpTJoa'
    'LtwbJegOYdeenZVCGdLy3fIFv1YMz4yfJ36r95kBvEa8aFRimh0rL9V886CwnqicPu9o1s3TBLUHtS2UDOZMbcE8xp6HNM2dBDPY'
    'ORuJtnSuuBSBMquMvmvsoReXzQ+10XOHNNg9xjj/2E4ySN1PcJUytie5qg69VrmdJIwaqpnSXyY31MS2LV0uItjKVUPfNU1eKgGe'
    'hstzeBNpKFpvlPV9Q814o+nQA02fnjCjTYFadh5MHkPlLERyWZwknAerGcGwmWgtNItyOykrJizJ/sBvZphRzRGwu9v6xC4C9Tne'
    'ZzsT1yW+nS2nEvv/GHDV6ye3VKNx9haqnynkVAmHhBDQByTPc7HVUufIk+GtxqC+086P4MqMStbI4Y4wDYIUtIh8IR+lu9eITE3X'
    'pBpKf9HqW5l6LKmGgo83WsCZvdnEn1mgS4eRHwlOHbVNrmxh0qsj4PDwzzy0QjLggSYE379keRFUjICBCYsKN0VcNtA8+vMdPc7h'
    '2qBPtqL7gZidZaijWxkOIWknj2QzGbihHax3G1VhjiO+XaQQrWyjt/Q9TZjqtaWl7aXToPKnYheLZISosvZunyei36AUO+nkNSbh'
    '8AdNhbBmfH2v72UdcOvDBFUvkXzmrOQDSZNgTmRgI5PIZUskzd6256WOhbUxalQvfTzhN+r1ZkI2m85wDwE2DoJZlIh52Rk0fJV2'
    'gBLltfpeNEwFYIJcV+tV1jaceczR9LZrW4NPhBttpbjRWVLLJ8n6zt6k5fXSjDYm9z9lgHmiWlXo6Um75PbZ/Kb6YEq1Ie6UNXEn'
    'EXPZeADlfytfa1fxD2vXhVN9nUUbK7R4VzY5V+SVTc59iXPevYK2LSvody6h8yfmxawk805anHUSqlV2r0yt3gjYSecSasWXdk/v'
    '/c/T+2+c3v/Z6b1vWKcn3zm999en96Dev52evHF68tPTk5epje+e3r13ZXMKXWN3mLWyNwum890LNvBCnFXQm9vtC8BeYKfhQDr9'
    'sLcghnXoz58Y+fjzM0dP9Qs2frUdWfbqC88+/9jnnjj47BNffOrxJzo2QOJGOPYm3oE/ORwF0fCA83Qe3KrYyTrPPf/Ek0/971l1'
    '2AYSQaXqQTwsb9LvFCadSsPp7C75Xbcz8W9bLwJzaT42m3lHhYnT7s2OpvMQx/081AjHX/RGCz8qdJ32zJ8vZhOLSpYGs3Bc6Lp3'
    'Ort3SvPwKoBgcliAtkE+6F9F5R42gV22Haf0UhhMCrbtrORIFrBcBRjE/GjqhwNLdDij3l588anPdjode7CYkGhh76U+F5zW9UeX'
    '+FyoOaui+FmFnzX1uxSNAGqFCrz0sl6Kdw1ndV2OKohCGhVC5LOwpwsOzOupq8+KqaklwyC/Z6JOIdLLRg4C7AX4FBd8aYqf0gXn'
    '4dMh5lnFZ9G4Hd0qXn3CdpfY+P8BgmHLfiwKvM0XwhtHob1STY6wIrcKjXIHBRh4wYEiEmTWNIzmBQSuCzJAZ7lyYNcD8G7D0swQ'
    'JfH7M7BpQT8qLIMIxuB741Eg37Xms4XvUv1SqQRNrFz707B8cQe3ECWew1763txzltShHcl2WpE/fzwcT2EekzmhD8yM6rSwvIv/'
    'vADNt+yXgHDA9FZien7U86b+5+fjEUNNQCfa2wP0AS4LtBbWb/PaxpXdS/b+5qHb6+wWlvaG3bI3vPG0bbv2Ffw9muPPXfx5SD8v'
    '4c+bixAfLtmX4OGRrZ22vbrW23cUcB/tFII+9Jq3deGjLDoYz3mE0ZVGec+unJ78O5ANICDvI7m4900bMfQZbz4s9fxgVIg2G2Vn'
    'xYUUvt3yZxEA82ngLqOos+z6IDeBnNyyT09+TpToBAiQ7ZKTP7GtuY/fgFK9RpTp9dOTN23X69/yJj2/D5/u/fr0/iun9+8jQUOy'
    'hj9sten6/sBbjOawNQX2FJbiLCFqLSmNXMuWY7DdW5TJgRAhmvrQfLnUrLmIHI2VOwyieTg7al3bd3uLGaJUa7IYjdz+zBvMI3yN'
    '1rWrqH+3bMlAbfeCZb0Uduk7nu60bCxlu3y28tgcealoiND8L2YgzD3pBSPofeCNIt/FCM3nZuEAIyioXHQ06dGEWjZVsanIE7MZ'
    'CDc2PgDCDp/xJwsqjtsIOJnFFLXDQwZU/G/+ET9EBBsdUAXHheVfRB0YszxX5YexN4Wd5Y75LzcMom+EL4ERTubB/Oh5YDFHHTH2'
    'YHLD74uHKU/iqT73O/RHo1A+3PYCXBQxIv9mB/d4aRLeLjifrpTLZe6KNzTUAVoKgyQkgR2GBGgmGwUa3AVhRHuH0HkezYCzL8IC'
    'dGyG12N4SCr2Pr4bB70XMGiPWJx4cZWMzx076I98W8wWq11dTDGaE2YmiDliS2949WgyH/pREF0EUg6yrI/ZJftQcXPTou6A2loe'
    'q4Z04g5ilzUBJJzB28gHOoXmNPspC9gZKGxQ1QK5GIAAyHBIO7JEY8Dhfw5A4PepVbWSFqnY0PJjvD1iGGhksodfRs+YJQvOMhgU'
    'sqo7yx6OF3+Hi3l2kXZuvyuNfMLumT5NQhONuoBHdDkzaV+w5rMjHJIJbicB5xJPpuCsejiCgu8s8TBBdXkYN/3sBBefOmXKEHUI'
    '8UtiL0OX0N3F6Pg4Yl2/D7+oAO5aXFC5E+zjY0UrOdT3+PgiF5WkpUSExGHJoS17HHdw31yLSri5DoL+fht7HEPtaxq9sCUw7f1S'
    'MOmNFn0QQ8YliTQHZOBzkm3fAMgB8Y1KHlMUaH7VwmcZU4UcH2eIBTudNNzjBjPWBCqpnlDD7iTHg7KLmsKeAOn/JgAGLGOvxCt3'
    'QLnNL1jX4oG58c/Llf0SQKgQdHZvMqRIsb0W7O8bDTgloCOw9QufCUMYx0QKWyULRUxaRyqmpgT777/5/tQCrLEwKiECYh9ZsMiw'
    '8dAfmmKuLJTtLBLiNr+Aljw8ZeGkVSHGW3Xx+ErUjkrUjYFBAINoY+OiRJ+NjRh9Ojr6QJkE/mxsZMC8g1B3UPEv4GRcoqEwPX1H'
    'YYTeYuQnN3NEWJ69z9u8ihLknRj67QvZ9CNiCQ93PzJQaHodnbFy4JIPDA1gaixQRv7c2IA24T/XFMLo6ILE8wgRJmL74mdB+gJ8'
    'cRy0xSoERKxYuchHCICCkM/D533K8n/0F4zLQPU1Qhl5A//p0OsXbjhLpEZCDyCWexUkAUB7lJWeAhSFIjEFEuVS5A+au+rPCzfc'
    'W9ye0VAkG4KvUuNAOSRulgGYlBE6WEhWIBTR+5yisAVCKlH3i4Lry20hByReu//16rNfKEUkewaDI15DR5d/8bqEz5IUwbQbhYqO'
    'gpKp08l9uPlX18rFHa842F82aqtHN0tzH+Xn42MQbZ1lv0P6yFbVUaMxm3H7MAApuvTbUm4xdcHLfaHilN1qzVGEKhxpo5Nz52HB'
    'J14DsRnwIol+hwBAv6kAUmf+srHByl8QsbrIb0tCIHRyPqPU5zgsXS1BpUhIWPCGC7qxQJoqpThKXFy9Wq1i5MhE5j+8/z8+eOc7'
    'pNK/eXr/b07vv3d6733Q+D/62Tsgsn/wtW+TTA16/j+Q8v9PouTdezbgEK2eOS/GQBZ3xcTEE8iGTGWfQxemcBGNjiwRaCLs3tbM'
    'J5MF2QwxCNi6PfQnRJCJDE+D3g2UjfrBYOAj1bCiRfclvzfPILSSmIhH4SKAZCWYHMg0DDaiqIVjegH66I1CAJ0197pI9yewMiA4'
    '4gugXCiU9f1R0PVR/IKRT8I5aOege4DEYXlRPBMGbAnbzZYhhLoKxBzoKv45AArdu0ExywfefI+EWsawrO9OK5Z6kZKyRKLIY/yx'
    'iHV3iZ4t/XEwfwKDoQs2zuZACsUHPGfQQZl+WuR7AL20lFaOrSTUfRfkZCxD2rXrj7wptHEwjljzYEioR9Gwf4ekFCq2ZI7G39ER'
    'IegF8wOaAb8j71mUG1DiZwXFBbkBPtshYMPMlq3CZLDYzYU3wiANkKdREp7YLisBME+YEDAfkHRaUi9wAb88QLeWPfNHsO0PDr2p'
    'vXKpY9YsGK4IjZJo8IAOVEGvNV8cH5edyxUqvbpA5RVgJSA7BKR26gtQ3UEH/wlnYxyhWNCsFVdNpCfVkZNC3nUhJuWGBNANwznQ'
    'myOcLCI8kXmilo5OraEJ0tJEyTZrd+KJxFGQe+lPO9b35Gf15vhY/URZAXXAZ3mPouT0xARQCEVVbIbEuHFn99pYCrvuGG0ON3Mq'
    'qYap4k2oeFP1i5VvksGCpifURmcp9UfSBduxcWYprnGxqYDtMjxY3URkEfXQ/qJBMpw8JfRXHZ4G1IQye/GihAy/aMd6rfwg3kBv'
    'bVMrJm4tGRRdiqHqCG5yfEy0VNCXXjj1+1kcj+aks73Ldkv02rIvqxExzATzAyVGNcjUUUMqRdNG/qHXO2LC5uKQfI2NxvUxggep'
    'OReQsp9U2/i1o75rrFV80jU2Jk7AJmX5jQ35q6RZP1AolBPby+aostq5earqJ+aqLaYQDIfc/vlzy2yaQCCFFAWrtm7c4N28jOEN'
    'ovMhQhCI8jOA+4QUtAvuwC64o+lzLk7ljkaD75TU7729O6X+gq+Zoceya1AzKGs87+0V7pRMCov8U7j/+/ZeuVVxVrzpLFSECjzY'
    'oYXGDuJ5Uvoh0ZInUQI6XhhqQ3Yc8QGga3xwh0687LKpjmZiF/VusRXegUULZ6B/eG43NpB2+TYTHxmWw5KxjwZYb+YXRBFPLyJm'
    'IwRpbV317SK/KyNbh3f5nk0rY0ubG68jiYhiz4+8yQHb3vYk0dvYII0/o4iyAThyONJo11lTuq3zgRmZtJB74BQ/o05QCyS58qid'
    'CAqhMgsvydXgOWj0aWoza+Amc0lVgJ+SyeDvPWBswKuOjy/yLOGVmtbxMT0Kz4MDYfUFCoQUtSQeUwYSb3YDFEmxgZCiQRtIzrAp'
    '6ovpmSJHXEEzhkgtgj+4tlh920kaYYzBCs4SRC9O2JGyMHaUwqUtjFanLTBXWnxTFpF4eXhwgCw0GLaAFfS2COrirMLr90mYe5ot'
    'gLOCPWYTpe36t+akfcNQ4SfmFJ71fICoccpxfIzfEIJ7JbRNouEqPqHgMdlJuE87slIJl+f4GE27hNssGzhLITDwY/uhWL/YLbE4'
    '4Sw1WSN+/fFkhJUhA7F45MjJSF58gHEGRxsbFw3m7OgiANbxQZvGimapJcsEpB0CAb4B1R7r3RC/+S3uvQOxbg7DnC3Jz05GRwWU'
    'O9SRCvCf4Et8MpFxnPTkzBv7n6cDa5Djxck1HbDgKXujUnaVJUn+EEc3Jc7ow3Uvb9Ud7BJ5zPPU4bOsAM0K3L9TEhpRQbWHx8xQ'
    'JTmonjzgImDAoLxp8EXeza3KSj+OS88bOcWjBVuGnIUTNAEkXpTQ1vW4uFqxIEnv1cXUQ6+mP9398Ydf/80ffvUOkOE/vv3zD7//'
    'ttBx7//2w+//jL/ajm4BOfTnuHcLoHL0lWmGKMB1cWxcenSJH1cleQx0fd+sf3UxRtfrguBesQVZkBLxPmHVdTQzkNpo3iS6DcDq'
    'yCoAfYBm5Eck9aFExcpI2Q0J/4G5R/CAzsTP3vCOOmVoKWbGHjJj0aQjTBk3O2Q59fSdwSO66SAxDiYggMLjzVLsXQaoOh+GfbLh'
    'LubhGKSInlCf42FcvozVPJVUDErflBnWD9hvDUkZjR/KAneU28eoY0e+D8ssZ3T58ooNSZi41+/YFK9oU08CRLFyL4WTvr2xoYEH'
    'WAqDAAjw5HA+1D86mpyFyn2HhrcZFyCGz33T906nsmdjPmW7hc+7nVJzz+Y0x+pNY8/m/MOAhGK8JAuIBV/GUk5LTkITfASWtBJY'
    '4/I8W+a0URcGOdk/BOkIK41L2pOLtpKgB9Kn+GY8u7HgozcqXrkDUA/RpUr/rL07PpYKvkLRlgQzUl8PD1I1FGsZCOfKBW/Fa89q'
    'fcQnOQddH9DYP5CNY7nsL8iLXO75AF2OJr0jFH2BUSXfgcLuApXiQUIB9Rv31spxcADkE3YgsZYlY/o33m/ibYwitPtgPDS6aNHr'
    'wa4RhSQWY9PcGQCPP5k46SK7n8BHBSQuNS5lf3AJJbFZTahnwj8YhUAAFGJJBQDNFW7CZKJKpQwbezZIC3j1LaCwkvmxO5R6Ydku'
    'XlQoQy9WhlwINPFzOD46wy/QUBVpXeLmwQP719EfwOWtg89/S8+8cfD5n09PXrE5Gzg+vnF673V7dY0aA+FRvdGkUR5R9CRMHzfN'
    'UzE9N7QIeTY07OwquRn2NVfZ2BhmUhTdzE2Hw/mdZYwjWznRtlOudqKXMWztwDphYZ8Txkw1BslIfJaJOhmDwcN9+IK8HiVhUZJ2'
    'ra+cZ3xzs/spNUlKJ+RRhebdhA4omnXi1zN8DUqewdMcosAGa5qlWNPNvTOZkRhIabqIhkB4XLGFW7Mz+JEbDQHxWzczjivVMevK'
    'YfotjDLcREf2KLBp1tmdyeYduavn4dwbqZL8ss38jLuRwOdPezYa3NHU/gY63J28cnryvdOT923E/9+dnvzQZjmV1zE++7XRGfzA'
    'djY2qL/dTnNjg9a4hKLbbqe6sSEGtikKlJp1hwdgVz984x9PT756evK105O3cQvm9CEPb6EfJ2fs6BT4I9i47O/z5pnDlgCOm5Rv'
    'YjWLUXbPruHBA43RQrdD+N+9k9N7X7VbaQjeI8CpsZgQNQYlSRJ17sqtkmgStstR1IrhyYsqEcz1ej2gwL2jFr3eMwDN1muDNPqD'
    'AbONzwq6TVPUnA4WwRxPP1IbV+mCEuGQw3ppyg2YW97YgC8G5d8tSy+/YqUs1B3ZlZjnbmdLyoiSp0QdVUbwdK1Zk6h5xdgRcgms'
    'SDVxTWNKBfVW9FmsOJtVZx9kHi/CuxOFZ5WHVDdqJQa40kQo6IGAgnQCkAboksYH4+bYrSivPWNh5iGu8+MIxvMQ9HgRBMH0TIJp'
    '2JXQn0J6KKKpSvSvsS6xuR4X/Kag+r5Wcavulltz69pRtj4gpaWoDfroMtB0FdkbYIDWYd5GW8/Dxj4yTYWrs06CmEsEmIk+Yd61'
    'jY2ZGPgd4bRxx6DvGxsZL9dR442NOwZNz6id1jqQgKPuHx9VR8bUcQNubqq0J2pBLLSYTSNKfTINenjBZxFTL8v35K7FoSKxo5aI'
    'tYUSIHRQu89S+M7Q1yJ2rMIgXMxEmIljUcQPANPy8Z4NEKnY2QTryJnzMSPIbXzieZHGrR/sx2R2nfMNn+Osg7CjuResbRP5jiqd'
    'QilbYmZM5y9TQ5qKUoqmIIkW7APbrTrXKvuXbYW5ZJIzp7fSjQciBIg8DWIhI0AhQ9s0kqSNO1LRv25slOtkkRlvbFw0UD6mtlJn'
    'NG1/cs7CmpTevwntPh7gIQ3Q9iZAt0aR7doUc4I/BmHYx790MwAqE/B7QnfK4g+KBI3sfU1eIriqeWns9PKh4+LaxN9YQoD3wv+G'
    'ysKk03QAX6jZo0ShkUXj25WqsfKiYezIABa+SLSDr+JmKrIZfG0oygw7bdGHXjT8wmKM7ksoQg071UqjUdlqVCnR2KyAL4NOuR1c'
    'UcJWcPmyM+wQDwrGi1Fh+FdRqTf0Zo+Hff+xeSFw3Epje3u7UdlR7Gu4u7tb1v1yiNig802UYNbTMBx1Yquj4Ak3gc7pOC50C/0V'
    'ED1TGZdljJfO+Ta0hB+ORlo+DcPn+nZS235tOyJSIdIOpJz2+uOfhAaQVACWC+GzUjAEf7dA7w+T7x0+d0cbnhSZvNGc3YTqag1p'
    'DizwmHJK3KqXarUYf+ymPh4fS+wzKl7G3p2i/NZNf3PyYKmhWMof0nQbifVYwS2l32PsD7e/n27u2R7/QIe/vAb3olKoihkNsvCq'
    'eRIsglFfONrmtgdbA0MypfmDrtAzWkUjzNi7c0ClMFw9q9BepVV2L3CaiglLdWgVFOKcMOzQm4sXI2nogdLozqK34wKrBhoEn0gC'
    '1Bu5YPFxyMHQH03Z8YTiKI7U0PkxOXhTaBx7N/z/GnYlQXpJQAUdu1Ac7BdeAvlQM+6hp6N++inOlV5yli91dLOgXsgVFxlc23cj'
    'NjTL4d4KyKoOY9K6JQX4JWclFuQlw8HwFo5WmquVSfilTjyP9ksl0UtHs2zTe9nh5cvt+IxRephePZr0CrqEGXsdUcSMOEtU0QLs'
    'jx6jnvDrT6KV8LnOtJUTXDpL+oNAY5f/PChG/uFYFAQ9Tj2w1TEeB36Pn1zdgil/Y/TBAr+2Ll/GpvhBzkV3jqKR4fRbOgxWagYJ'
    'wPNC8wrS7wTU1/gH6Ye+BCmqn8JVZGLPAfnFOOB+IXLp7gzNwzdmbcIWoxysseC+PCdInA7CzIWPjUlMuFIHXsX+KrADO6Y1TqoV'
    'KcsQfyG7irYMZMbRCSkdxMUubjjeg6mco+3Gd4bQcC5XYOPMkQnztSGuIAMmBkjbtmiHSRAeArVwAnu2xPr+AQe22i0buKHtsjR/'
    'wPHRN0usf7BpLezshiUYbmwKlhRLWLRTNqiLUsKOsXDgjYMRGfM1GKiXbnQjGI3gRwSf1W+20Y9ISUZVeRZ4I24h4y2Agw4lJRBW'
    'rnmECmBiF7mopGD82FyutOacuAZXL3wCrnJEF7IAFkszSyTBaM1XA8VujCFK1HhMmOY5DKkdKURkLAGJ0vAEixbRlJIG6cbftBfq'
    'Xo7fadI7NWmCdgyjdRx9Il4bXra8UYjVROjinttjuhc+wWlnTOxx7vJ8oTDc48Wkb60iEbqHqkN/rkIBFHJQvZQc8MH8iKlN7S1T'
    'Cgq5zee1RjtMZBmTjVAEwWFSoUjtvGiJbLdLznwgXDmiJB9T5DDo3+nkrOdTiHlnzYlhAa3sdsrm/FCvhvHBJ7eSnmXU1qIt4lgL'
    '8daIPIwhknBnMSOV9hJ78fg4VlAMpyTeJxIhGE4SI5w2HQkLxxiBH0aAWOwfkzzwEGft/DoOnMpS29kT/THNp9tCXUbeJ347wIut'
    'VEIWC56H4WJu9YMI0xSgJQbNMuGoL81kpfNvflLfk4VzSYCJRoZohPp2cr/qxxQo7PU7WaRKukjd8nP6oS9ZS570YMqPIUrvn5iU'
    '6IIuy2yabCZfCAmrrI7DefD6oTULWfo5tYpWXUQtA+rIAzkFiqHMOypSqIVHw/IcGyRtTYxpLVeuxuvwkRQW/CF0hFZ8BC14Or5B'
    '+YGwXKgc69zS05xK8/R3U9xSzD2DV7ZSvBLHkebFooXYVzTpDxoDJBaVEuxSmteH4e3PQ6viUeb4vUoHa1LbYiPRU5P5LBTv6MVV'
    '6QdAS6cCtBB89PACHsSoJxmIb2P49scnaZrUGDEFOpDugO5S4Z1ywHhYPwuSIxkRsQuyHHO5rNcu3tvWevB4zz2bXuB5/dAbofWL'
    'D+xLpVKBXCqz3E+R4Mjfe0sqQfIz+msk6pT0rytYEkIs6RR9EE28KSACbA8Okc8KdxUh84lP9JJC6BMf4BVvogd0jdBIRKSdwqSi'
    'PLIUojKbg9eaybLqMY9N6tftXE5GoTdPie1b4JgUzFgid6idqwrny1x6YPLFDBE7KXzAZtfEYRnK01Heg2UXPhSNiKR0mzFhR8Lz'
    'RLqNFD0qFjKF/OPjVEkZ0SFGdqVeTk5BkKyOKLG7VYb/HB9T9143kjWL2tic3TplC5AOd0QAO6KhPcSOlqhlUoj80ClFlDPgI6Ol'
    'VEQV9JIKqIpjqLKGodFo/oV7IiuiyqhcTsZWJb6aUVbmR951FHKV1pH2bEnggdTMYUdgK3bSs0g2qIKyEm5EGbwwK8Tp+FhxSN4j'
    'qU0M6CG6cBLxWZcvszQZxUfWlzv8M0cFXbNIn0QMVxaB0GmCoRxFwQi5Gsd05+phiYQE2vY4t1xmUiLbxBqbtGRqmyOT5BPMCuDZ'
    'MaIRM9gpF4ZtIqPuEs2vMKw3CROaFE3fUS7yad1K6QxnAediGjoYh0qvNpV8rAI9MbaTZbmixG765pJJjYNSWUWglFwcg4rR/uJ4'
    'z5t2TCDtacRQC9A0CzmtMiMz1Cc36C/QeR9oxE9imB7S3rSICCptxtvLHWgDtYPEoahwmL/hH0UFw3qDHpSOk9mnYePZx/7MN9zX'
    'isxBOl6QgKUwR1pVPr7RJwPFGBsycYw/ZSNZjFl0NLZemU34H+TnpshNNpCfiMEMqOliNq+JUMSkfT4TsSU2P/ROF33BFmcVSm4o'
    '+SHh9GgWYgnkEx4gopHQmvlPO9KdahQZzcAC2sOAA8IrOkdkFNZs5XOrdg1/NneIpgIqfz48LEj48cbGQtWurpIaM0hxrzRemrbx'
    'xSQaBoN5AQP7olXy6ycV8ZZhAdN0qSxv2D2bFSpbJKvK1LJ0S1VWXBpLxeYBkikkU/pDwpzn2PemcDPor0W6TF7Igh4OiJc/Nq8V'
    'QN8KAHrBrnYIsrGB/gNqW1fhmU4dlL3Nm18pY0fxFvfm+yppRslQbLGafBfnkmpnBOnpE+d4F5p5Ad2NnjrvrIndGQP4xOGQbN9V'
    'R0XG+30dVhdv4v/VeQiZa8WBCLQoZpgLUmEyjA0C+HFjg6tdzA4zWSZgfj3hF3p69+TR5U09Z9DKolyX994XqeLQY/RVrHL33vVk'
    'rF5bmdnmoAxOZDCacBwtaPMQp1iFa4F7ex8gzDy2EDgY6TiHScTzx7Wk5tJLRtuIq3ZSkBCJCOKQGC64W022Q7JCx2yt06m4IkSi'
    'ky2oJMQA6jD+rCmAIkCjs9Q8AJKH/ayWGIf6F2lYxqk+eYFmnd3Th/Me3DNoRKAideLoxFp4iusHvNkhKrw8GTEm4qebF7Mi3mtB'
    'JxhnIuIGl8qBvqOPio5yzjzzxMWGmuj1HoexiBnljDtx2EipgxwW3Ux0MhHEZLfKJAhyL7ydC7lL2gml+TZhOTQajD9KQ61kqHb8'
    'iZNiLsVxaiDnQoppEMn4HPE2x7E/mEwXMlgANFVvejAPDwRltd1UPEFLiyYgy9YZi5qPDvkAT2rJsU5MM0vgn3GWDgujFN5101aE'
    'TxJRQV1SfEmI6CZjOj35CWbSPHnt9OTH6HB/79U/v3dirwTGpkv/SC8KhPL0BCjmWxY9f/P05FtMURMO+Rgc8FOgv7KzbzGRtdsp'
    'TKTsKrq0J9ZEKJXykTwsBBrZrlgwVozUshmuQzOQ02EFJoe8DdxzAH61xrwnluU/Ty2gSk8HE0x0IOgG3qPUeVQ4fdKtSjZrzvhT'
    'id5Ml28dxiUxQXxkO276RFfRI2AR0Aa6wX0GswXAsB4fBRTQ25tz6oCLWKpEKbOBr9MDhx5rcfa3DtGSC7LgLOguQJm0UZj8THjH'
    'dq9jEvxHl3EbK/nEjaBPbro6lUQSIWtlFRqKSGh9SCLehiaOolesFiNPhs2xr2nHGRyc1ePY63Ya9BhAgDOzI95P6Id/DcPji9JJ'
    'nB0HLqGL8aX9647L91+uqXibLu7sYxX8SbUI1tAiAJnrxxG6ajheBwrkLZbb7XDF3NXkRu5UOl6JrkMoEujwzh33CF+CknbZE6Dc'
    'rPJXeOfeqXa6VEyvgO+wQjddAQdMS3C5c/3KFAQNC6b6DCz8nQou/xH8+zj8LdypXL5TdTar4qWbeleld3fkwyWQakajziW8GucS'
    '5VG/4XcuPVIbNLuNmnzBSe07l+IXOJSeN8Xs6ACUS5u71/nsFFGKvM8//8IzT3dowKaCTgTkceJLKDTfXAS+stI9kF4i3azSqTDZ'
    'yWqdwIzeDKZsnLTSphwNhKOXyZkvV/jgscOfO0RwZYqylEzIP4NJodmooZ09Yc7Ksk+lZEPTiVRLxXejc2bA+V4hyGN6LXGi9/EE'
    'vWCdkHfBOlsmyBT09FQ+IvGbGtu1tPWgWCHnBSzJWT/XCoJUIFcCDM6Q/hjlk95O9G+Wd5SwABsHvPJlvhOuTGn1scVI+ned+Ihw'
    'zhchAxAfNdkxvGFKiGejn81t2S2bAr7JxM+dCi1SjMjIE42Wkl54OAm+5GNqoEkopRfxmhaSct6qhHlp0TRjbO7Dy6exESuJFgTh'
    '3Ypr5cqpVNlH2HrAuw56HnAUCo08B/zocOkaAc92bdbi7P2k9JXhu+7kGcuIUCIFzjsomM+OYme2M08JEviONNtEwd2OplOvcR80'
    'd4h6u9Yb8cL/G4Jumtk8NOwzIW7m1H04Q106CTab6Nca5TX5LMBw9DxRnDqHEvkiuRrNw5+hIRQO8OpnW4ZbxWPY7ZhG6GLVWSbs'
    '71rSgTg1lIZulztVqSqRP41CsHMoeOiLl+n4oPmAt9d/v1xZc57CNl0Fw1X+0in/Fk7wnJRfDEGLc8K4usPoOpHnfAukXISIjqxZ'
    'ocr5VkiDELrqS68osTrJywPaqcsDMqB+JqCN4Lhg8sB7j37lwzEdmYPWx6yYHjRAanNOs/y1FG1IHi/Z9IzsJilyxoms/9PpWZxc'
    'HfPFPU+GRZqcdMcxs8jHfsmJPP/L9H0Sf3rz3z748b+cnrz27JNPUmplvEvpo7fe+eDd78Hjs1/AbAyY5eCrpydvffDK63/81ptU'
    '6nV175KdkUAu49oKQT3V8BPe57j7DFdUQZSXeY7flpUZGoWIkR0xJZPknhcZuJU8dMjY+LnYwWk6HxJHMnw1LBnta145kbG4dMfW'
    'u6f3v316/59P7/309N4vafF+Lhb93jdSK0oZtrMXFTOm5l1rIU080xCPISili1nyRbyhjBgXoSovIJUujTzMAe5Pii9etdviHeW4'
    'EmcUWX56x8elZs2RpafoBsFWOsF8Cd0BaRLDPfTnX6QvasQwWi7LFu9bnd3Nv/In14oH+5sBp4C/RQN0iDr7E0d0SZU6/kSfCLBu'
    'vNqGcuTl77Q8oGtpzc0Fe5crij157xt//J+/+ehnr8sL0L52evLD05O/R7umvmyrdqwQxPOHZ+9GgYdLiKRy264hDH/4v98ne2oW'
    'dqzM1BWHhyOfAFyQWSlNAtTJJEsZp5C6qaOPt4MiOsHyoDKVapowQmILF1nfJNR8Gm9UKtzipLDGVU/XbsVnqGY/dAtT51Y7+wTZ'
    'bP+xQx9bFx6OanCERcDatzY2Jlc6lWpqLgj6SdboDX2CCMczQU/zOrr6vMyvyTvv+Vivk95rpdt+90YwT30XHOPq885SkwYWk0iS'
    'ljxqIDb9jDf88yiTzhLbecY+NcH4eTqTj6SQOENjzmMYp45ncJgej7evNgC+Wwilat3ADUg9g53GR/wdH3aaKdLI0/9or3StvC/+'
    'mavveJ+DJvOs05EB3P5s7gUTW6RizxVlIiO5vZIxZZ4MTD4pfoLOzjq6pnbbbqyw87AeSqDIYBUrHnd8tB/DjymVAJ+EOL3UaQgX'
    'nfB1gHTxkirc0RfIMfBGgS1BjGbs8VEwKc+a/lMxN3ruYJZ8jJu1NAnIuHAL7yyRQrecSVL6SN10ky2PJCR42KhB2MfEXyu3Uudr'
    'W6zE1V6p3uPdnZX+eOXW5fUvakzpZLsYjNsN0CrSG3rkYy+uvGHFUs8Dq4uFiVkCgTq3cpkBs/NAiDuyjQC1OOXm+WRA822u+966'
    'Unluskadc4Q1Z1zU1V7j+BmJxNr/3/j0cf7e3ITNU+gelkfizkMusGpFAxN2u7lpqZsrLZWNlwPCIzw3tKASvKULvy1PhIrbkYV3'
    'iJIHLKUxmvmHOFoMELakLa2UvlmK3baythZMQ6S1d7QLouR+cyvVssm65T7M2kvHxxe5UWCp3Ka8ey3Owo7rGUS0RKn81S+F3ezU'
    'DCLXQfKCHhmLr+6UgGqG+zBmb8M7amBK3fCOa3lzaxxCR82yBHSAN0b4lkjy7OLlMLfQY5gAiXfhjpXPcG+4mNzoQBcyA4C8taFZ'
    'jpFcIMNV/2Z8JhP5Ny9X3MRFiKTe+upgCSrAC3nBwBK+tOIvLnSKtnHsO5lxguLIaWgyNaRfkh+cOPsEVpUPyG8yrtnANbLdRM/i'
    '0g2R3IL6UfktsE3xe2Uq5JxKGxNpCzRR6ADvMBcDpjvnV/jEr+PLNi5qFzQkcURGMMn6yUsZzsAkM0hXtFVi+Eq/QRwi54fd2ECM'
    '0k6G0GopM3JiObUEFBFMfDxGEB1XRNIhWB6ya+IFC9o6qVuCsM2x30e6TOGd4s6fMy9uGJoTMxHFGYr0r2QTEVLPWZcxrWsvcW1T'
    '3HZ8zQ40r81e5ZkrE0QVJuprIN858bqZS0gAxEW8SANyMi95ELc7tOPLIeg+VbawEF9dZlYTWJSuyCtC1AHT2WrXb/3p7knuxVvJ'
    'u35MFxQNwxyQWxc+6CqzcO5FNxThVceSmUS5IUWg2KTv3dK0neGiyxc0wI+DxWy0sbH5V8P5fBq1/vvmf98Ul7fpBZy961c8ebc4'
    'vCtCe5es4cwfoKdDfLGxWWl1yRIOE5cOuqDY3LiEKSzwlD+cIleyJiG0AGKrP7u0+/tXvm4lrjY/PfnVlU1v93qLVkfsbxZ2Hypj'
    'fJx94fqVfnBLzgdkNZzObvpdccR3tl/afXQJk1pdiabeRBbpYrKq4jiYBJdy72TH8rtXNqHhXUQrvQeeiPXoMnnviL2Coegd9enm'
    'd9EWfUAHkzibPo6OW1sZPfK/1+kmxNi+zDOKU1Nef5g75d8+vf/3p/d+dHr/u+Rm+6r1+1fwgnnTbYxeioyveL38dR0fw7l+vyCg'
    'rzJyJm0pDnxEdxMNdlwb562hXqreSgEgpmbJexXXNM5odHryLmPSn374nQ/ehJl9I23QOb3/Pdr1v8Jd/+0v0/XWaPAlzDv5w/s/'
    '+uit7/zptX89PXntw1++inXxK0DoLfK7u3d67yvKHGwMOeO2v/MCI6tqJjwkITtvw8lqZqO0/fVrMUB8FCraeQeebMFZkUWdAHjv'
    'GykK8fYHX3v9w+/8UBrZ30bzLO12aYR/7YP3//qjn54o43w8XrEBYGC4RYQd6AW8fesLjz3zxNXOUh5u4e3jGUhvu1LzwGzEJu7b'
    'lLmxJRMexxeVf+75Z198TnXA6SNlnvTTk1+envzEdjmXZItSMd973XYppSQ+QlO/JkfMd/EYTeSXxA/vIg6JD5xskpOtn3yf0rGL'
    'tJP4DmD0PRyN2omLAHNLfsEb+yotYjItaTKftf1gGQ3NtIkjNBPG0cvQb0eDybX81KKYWHRfpD1NtSaJ2aNLbQWvZYxwf/Xn9773'
    '6BL7XV03T96AvPkzIxW7G2lxiZw8I91iUrbvpBXTPS17cqyWblady5WWrqbGly9TxvG8hnp+MCqYx5vQViIuSnPaGgyCO1mN2Ypw'
    '2a2M6505Cfd3MNc2/OCc4ln8U5rWikNiEFeI96CH3uTQ3NtJVEPiIcoZDA+GAoLDYbELOgj6+h2N/M4lUCMOg0kRXRRb29M7CbJh'
    '2qDTSTj3nQRv1PujkAOUQR5dijVcWZvAmWkV0EORQbhK8HMdBjJ8/xKo5oFXJLTsXErlgX9Xpj1H7+mvI+0/eVlyezFPcnJsPbrU'
    'EcVcWVIQV5+KZYIsPo9p/3BJKVdrpMl+cn31W9iW3HCrvnILBxRClJlm93Jldd1JXcqtXevFiNX5GHlxSUk9jPs30+Hm943U9kt+'
    '9Il2rbLtZnWrboGRPGKJwZYt+ShrjM0036mMxJjRXb9lIG5AZBd3tWu4RR/yUesjnQBYdZRoX1XW2idWxW0LOD708GV9mes9kfjJ'
    'n76ACR1EBgS2LHQo+LBIBMiO8ZQ2ZdRJ4rFL5WChjdwqFXvfvRZTNteu0gvOu2dv2fv7Ou0CyT6Wwv1pcQ5jSm7cl0kqA4b7cvLu'
    'AYqGQCEOBL1fCtn7UNy8UbgW9JHbYozYBeipu5jPw0myM6AoImEFOgHv2fzAoj9dK1mEN6hYMYDkS3YrD/orMVb0QcPA7EuJ5lDT'
    'hsboqAiVCaBUOrWjUTDW4+jh18pQLozBBvMRSWg6VwVqml+Dlo0oKS0YFi4hZq02jVdMWhUBYzjtXr9gOaDOB5OCbSPBhoXaTTBp'
    'dKGOkUTlDwcwaLnEY/9nTv7VQaVek+aQAL+Oeg5zOKLL9/6FJLz3MGhQW+H3RFiLsQ+TLbzLlF2IgK9SlAxHzSSCY9Rus5VRQJUB'
    '2fZNLeYGJLV7X7aMCzNY9H1Fsye8jkIvxezYF6xVMh1Kdvohl7eFloUokSHM2Uu8aBlJ4KS+RiaFy1KRu2yIBBzzWxxK9VmKAyyy'
    'czzRyxRy9FNkhfe++uf33tRkASDgo90UjONVEbN/B6pQ0Vimlxe9U8aCa5g16Vz53PauGcX2W9f26Z7ZzKx+RBnX5Gl0hK8jj0Iy'
    'bUTBtA7EyQ3E/QFRQvH3j/zuLLyN5oW3aPWVEGFSJLGNrpvpIiI0BcozIO0e2pRjJoryUj0zCZYaXTDVCROdCRlESVcQFY9YXcoX'
    '/1D2o0ET9v8jLTQifIoi4JxWNDibV1nYzuhVgqHgvk+DmMizlE2nMCRBFK5xJaRl+FYjJRmHTFx27zrjZgwfUaeIvm+4Tl9R19qQ'
    'mpE9e60rloEJidHMpWnT6nahZ+hOTr5zU+P4eWNUNkTBETR9LG7OSDogvCu8fLXLKYoy3TVlEiGxlD3348hj7ZzhUsMl8uR+dpA7'
    'anH6UpH8BG8nKppVuw9QlUIH07jFqFQ8nAV9nanrSpT8SYWEee+6cZfEWNjsxWQ1J+hovugHQMjOkMHcrCyR2q2zsjlKTtcZn3/a'
    'cdUA/nQy5/eYZ7cKsSXjP978+i9iC8Z/vPmt/0vZL/7jzdf/1rBb/Meb37sf2yt+/527f/7V1zRjRQUef3//x3RdHAwcr4v76Ku/'
    'MEYVob27Y2zdjJx4LgvF2viJA+LFsHpe0bYGd05fgmDdsxMkym5xjT2+gup7VpqVfx31aVq61E1WdHPVz8lESDdfaZ0Gfb8jm/79'
    'K9+ANrj/37/yW62933//m9DG77/9S62qEKRlZaLPKB7O/JsY54KPVDqTyAscxqSogMMMUvblETAlpEVDtWh+OsP+en6RnDrPKbZq'
    'lHCscQhD6l7HLYicCiv3JTKmm1KtmEV0NO6Go7y9CDQVyKcoJPYiTBmAKEXR3IbxntxLZ5s1TJsG0XXdOC+klfVdISKQXgF/V1kM'
    'UZIijSOmSRMpVd0QKo2LvCAoXphL350D7RqG0VxfP2XK2CX58nUUP0n0QjlNjeM8LUm3PGzpH6S093LcRI4lVr8Bw3/Om/ijwk1X'
    'xodpCiLGEC78+BbrXgmTbpJrFa2zMkCaounCtwQewE/z1IffRwm5pUeXFTsrXqzkN1rTpHVJFz8WXaFFkXTAZtrvWKf3f2uhGZue'
    'Euc15mRELHLubMwpkGRGm4pdhzqXUB1Mzcgfhy8F6M0nDfjZQ07Uon1q1Moe8u0ZhgNOzjlkDJTOBHl2Tx8LDMCQvvIAExajoJV7'
    'i44fXqezh1fUuC4grZFJFY0xjRdzPzkvI1WNPj1T+NNtJuhz7M8+M59wBAONsxOPyKIhAdskPIwzDSoomfsUqAqW27PVhrXoRRGe'
    'gSBOZwG6a1jkG2+SdRqIeIEjIXI96cGKv/j8U49LByX2TyeyKjpCiNskCXzl9O5de2XAg2aDMIipWzKVInmJRe5Ym9Q6zXMehqOu'
    'N8sndfF89dkhtRRn0Lgj/9kgddLeG/ky7SvbfJE08SCL9Bs6HVbP4A1QIGU5BtEOz1VfJsVBCBIvs2YvcHWaQKqESGIljAGnJ7+l'
    'k55307are8qy8WtVHBUgc1B5DEPghw451hEBdt/+pSWH9XcPyilEsjqc2DfpfwgCIJVfS68DEFpehgSySPsGexXmpZN0U+ov3p5C'
    '0Q750YbJZPd8N5WBnOxP9ryPLje+datSqlnBpChZqUpC3w8wahlvEQwp+/zM90aWf8ef9YLIb1uT0Ir8qUe57Kfo8IL57MMJyFlj'
    'SrVU0nNoUdSgShSjxxDGjoSxQSSYdcREyVAZ4MXegXuzZd4Ps483aCeusQfBWdbMc6I8p1XoP2NvPlBLtGbQ1F//yJLb7W6GOCKE'
    'qaztTp4giYNCN4KNnbWjs9LoaAbBpNUK+eBzuFBot8IV2zf0Xu1yMvN6Ms316rIWAFrUbjo7VwXNfJKgN/JsCol70RsFh5NWz+cj'
    's9OTf8UQGjSWkwlUeIK8jzeBS6MoWkMtfvoO0iGExtvZOdrSpChOjXOJ/F605910OVA8F+NJUsNGTF+xOSyYZZu6uPo8GPkWkLhD'
    'n38+ukzG4yZSN+zZMk2D1JLMrbHHdlfxWcdF7lAId3mqkpkmQtbPyk6T0XM/iNC7lbs2LYsoHiUlE5ChWCx0MpUOXeO4Et061BaD'
    'EqxcMiEp3mWIYND4rcM1S2ebS8cLJ/eGjAki+67I9kO+qol0fcq2fTP7GlnrLCSgRD4CB7CzsxaShNjcVUyPQTahJQw6u4Ycirmy'
    '+RKmKVmZdtRYd4xZyjPSacd85sCT6C+C+bAg0oXZToZDj0yYYHU9gMUsRJLBum/SichoPulDJDW9FC0iQPcpRZDZuAwGfPPP753Q'
    'RsiP00erzd+RLvrVWKsF8kN2mZ8IqlWlI5f39WvK72IZMhVfl66XaQAEE0R7pW4nXBfm4bRVqaLrQgbXisJBDtMSBA8lctZfLE34'
    'N41LebzMjoUmu20q21pYHLqgaqHnFzJ8gFl2yrr0Zn1kRvJ24fWhH246n5KjMnzclAEtfEUIJ66Vd77S6eAqNweFG0RPk4rfGa9z'
    'XFLGhk46TPmcwqDM6vXgSSFd8mOk3lKZnnYrewVvL84UxCdS3rxQrDh76jrtlhf/FpLZ8P/3clmO+vUg8liCTvJrSXzQ9SdtbFoJ'
    'miTxhmzzwweVkAxV/WWZNpHPP9+gM923LfnM56GGNPSwmhnmxyBFXCEx5f01s2LsiSh3S5A8GqbQvAyaKJzBVql1sR6MAjand9oY'
    'khwMjoqYBw/jlySoHl1q5g6Dk7l2OgEl2z04ejgmeMqJH5bJaGJvTdvmmT017LDXOa+2ebRNR7VZxL3GfmmpKyO141d1573EMU4P'
    'JjZ8p4O54dzeKNK+i3RxGTLBni1e2S3Z7p59G43Pthh9nh1I3JIGWD+KDGmGu82TZOjuSxJElM0rIYxgn48uQ5Yk8bxUP8/Gd4l9'
    'GCZkTjaEGd55NFSyOaXqSiEn69DY8CSR2MGZH5QtefjJMfDb3mycQyf5bPj+N07v/9vp/VfJjPh+2rCBG1WmXjEtidxAgnzhS8N6'
    'eH3F04tnp5LyGRiWlWWXkkZ2YrwlVhVnKswTolObQ0mAgAI39uwQb5cBYRAFZlNiiw9SsBwdD7xMJquXMVUt0p1vk5r4DvxLyWvV'
    'qQoj2EWoZvRMCakDaUF6k3b0z0/vvmZAjaa5p9mWT+++TtorWsES8NUyXGcYaZPRHIos09BQgE6k4+t0gNSexxRGkYVoDsyW7GiX'
    '8dHRJ8cAUgKxRvl/lSL5vL3oGGqYLVsOM7JtvoBhoTdV2MnNdQKYdD1mvpSwdLcyyXXiZpnRPGEHHCbuKyYMz7iXM30DgiODVEXV'
    'a2XOPzZ0DKlTE2a1K7eHjrQ4Dg2HGxJlx3ktZN7T6FJWlwxgXccVNu+zWAl2fb1FHzn7jtzDosQmaUoh6dB4sRK/js1RqGh1hqWs'
    'iyNcxKysoRQM5wL920Hd3ks79UrnEKelvqkK9mVxlU1hvMbr5HLFcZwW39+V9G8vrHGL3Uu6+a7rpDVWuUlNO6dBgvg8gHGnOPRn'
    '4aU1bu1nHSHzCTGfJ+BK7NlCLNNTeuNW0D3DYqs5RxRhuKEtDx1EO+YZFcaSEh4czkCITkae8XloYqxjRInx9KA39GZOpiPoLI6a'
    'M+qJ94nD0utM0ZJecQDD2EkVUX+VcxYiHHCTBITJBtpfBSlBGfvfKSIT3SwxDoZOSpRv/lskASPB+Tmxnp8SjcF8T5YWpIWuHlq0'
    'hB5MwWmEhEQvjmXepPxCsA5fS/p5UiBOK1HrXUtjX/9k6XyRV1NWXAlDaRoYIpywIIN64xhJjmPj/Ecf/go6eB/6lx9VnJtKkfSH'
    'X73DQVMoCidiKhNhWHGIpRiXtiZadoY0/sUhYOu2aqyiKOfYd03PWOFzF3vDrgUs1vidTHsPRV6jBdYT4Kd0DV46xodYP7NXBgpr'
    'sxYORrxzs2Zc+fCNf+Rh8RL/A/GxHxIv/icWXQiF36MRv0mCylsJ3HxDDEqc+f2aholN/iuf872JIDn5H1KXJHtferM9gEbJGv+a'
    '00XNM14JDResc/mKpHxKFQKs8qWh1JmNeM6xccnzuOQZIa0aM3lZ5Grq+mutLMoyHc0lfj1fiBZdji9+WOsK6AzioORX8cyVR/Vr'
    'tAuMECPhthN7Ip1xtIXOXrO+OsSeJt4DCec44w/e+ekf3/8GU6IP/uEHH/79vyDZvHvy4ffvfvAq4Nm78PKP76BY9sGr/3h6Fwb0'
    'tgx9fUMLcZ0SzRauuyzb2BLuMg5kpRkvDc5AI0JfSj4pkDFu3cifn8dJlq/ZzfC/pBakzjTt9P0ZCEWxUUlRI9efkLrbMXwHXZKW'
    'zvDTjB32+sAXc0S5qRRIoxUTfj5Ne/N6FtOh8kKuwwiLqQissEzq97bBSUgofIhqmqvi+fxNGVUfY+dEATbhnSjdEqWXYlyJfQHz'
    'XC9lKwUhE613rnSy4iy+rrtCplELtaPzBjFmevvh2oJieXcT/o+g7XtH0QqovRms8EBHAI8udVCucskkcH+EXpbCtsr0GLTjvc5u'
    '8sCe/JwYf9jVH/0UEOFNuaV/DrTgg9+98cGrP+FspwR6Q1CC3S7Z9L17H3wdKNV3mO398df/AuU+ev9bRBhirsctsnBCwdxv6G0h'
    '5cg/yTASCJLfoSLzSJzndzKJ88e3fWdS55SLmeYgZDpDphyCxOiLFPkhUZDTScbIlo09+gg5nWSRUkTKDBHJ1JF79rNf+PN7r0pZ'
    '+TVcBIzFgY1mP/vkk/EnNFlxnsyfkYnmyxl24HPOATNy3gWU+Htt55Dtkg6UUdAv8rPpG5yofEnYga5dK22jbfgVgigqPhj4V2rW'
    '0Kj777TlX4FpAHf64P37H9396w++Dpj2dzgBKFZxOZALJRgWrYCOvGzv74tYvomLYeIYy3f9Chu+OC8SbrsJWUHVFdVZOTWLE+dK'
    'qVxJuAjsiuDzK5vc5O51zVAJUNzk0lmepGuBykL7g2BIRFeyiTPFz/ujUXhx7aKqxBjf/c1H//wLjMi6y/KzElBBR/g///Cb34CC'
    'AJrCR+/8r49IBED59N5XP/qbn33wv34hs6+KZAyn939weu8np/d+Hudp/dnrH4GS8u9f//AH3weM/OhHb/3xJ79BzEPF7adI7++e'
    'wACgMCDlh+/8mJWrD//2R3+892uRX0ek1nib6FGCgKRnRTcPxPAUStJXfvnhv53EwJyekaQCBMXcrDMO6UTQhEoHonzZRe6imd9f'
    '9Hz083kJcM27/JKZF8ktO6s//PaXFAL3EyLHZEa+e09lKFFphz748lf+9F3A+X9Kpx754Ce/IMvAa2uzj0x3Y7fWRKqPvYdPDiLV'
    'I5nq5jzqR7aWACot8CgKiQPE+51FusgPiMN/N21Sl9qOqRUAJ8g4+S5EvVmoe9CuSQUphP0pZ63he6QL8ak0aRagU1u2yk7fEsWT'
    'p+zt7sz3brS5tLyNVZWN7ZiinGxXxRrKsqZmY7QqiZIqa7JH1XLfH3jQnywlbJLyK4BxFoZz7VolLtcW6XQfQ0sezunJGYlG6q6z'
    '7KSPeIZO8HZEfkV+eiEsLPGUpex2/aF3KwhnLZsvkp/bKw67j4Iv+ZzfncaTzsvYGwV4o4tPx27iCIQy24o7tCgBYzQv2HxjFzlW'
    'FJkW7/MtAvDgLFEVpG34WYYL9ImOMOEUdIKpd+iJ9aPc8n0/5QcNbZSwfQB2ibp4lnpwXP1uBeWpwFibMUb+cE3uADHAi/z6+Jj/'
    'luQRXOrKURa9ZSk5nN7cBV6beBv0KbmvCh6kwwIhrEs7NT2Ja621fHhGYSnRS1VKmL+l3Xt8fJzUyi5Ke4l5qdb6aLVrlf12xqiu'
    'A8UcBdGwpEzMjy6poVWp6x8S8l53VolxG/kHErHPnaCfdc1vfIGs0VJSi11mGBUerEXDTVAtRMadyhnrEXumxRX1O4lzq7D7/5rb'
    'JyK+7oN9YGgL5GdeFe7GSUfjPcNRLZlhQ4hEJcs2d0w7a+0QzqyLqmuC2mkfoZybq9VONJoVkc9Y33ZSuV0d/ixwzvzU5tvCsnyU'
    'tGzn2b1SivR4t8k86xnrRCWLccj5MjPZ+jpMy0NdG7Ntqh0teQfBIKOwk4XgZ1nSNNhwkw+2NuLmJAmmxGV+KVDhWZUqbF5t1E6t'
    '+nx2pMqaF08ly9JtJ+oAz7i1JUUX0fFEbScKnsngGAl6rA6pJZlTt5ik6NcYM2irQcfZ7ZPjoP1qGz5r8jKcDFAghmvN4mNuaRG/'
    'Ea8JP4sNkgYIaR7xSHBmNmkgrjUMb1N646NwsWe7LI0l6+u6rWrFuD8hPR2xlbOuuMe73bXtKsSwB0NKKZlqu1emQm5THukcaeWG'
    'fwTiz4TllYeVVjY2Cn4JWsKBPIGuVLCJ1QsgoZnSzMNJLqs1c5G51H2ZSl3Ngs+CNeXedvSLKVQ5cf1EVmW0Tsm64oaIVDWROPsJ'
    'ug/PCiejI8uzht5sjPE3GGzTL9LLF5/iDK9oBLYGM/JC61vROLzhW5j7NCrJtN8HB0KgOMD34m5AyudfWGJ7Ry1DRXARg1oxMrms'
    '8bjCdeBxvtvccEQQOt4FdcVNy8xYspS8tJVIJy65rbys0vycvJDSZWbdyspJvlK3FiIPxQQ3D6acAtQvgK5Mt0CgF1bYP4I/Q9AI'
    'dy/8P9nhg14='
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
 hub=secret('CHOKOMANA_HUB_URL') or 'https://chokomana-hkgx4uyxxezjtr2sj35jwj.streamlit.app/';app_url=secret('ENGLISH_APP_URL') or 'https://chokomanaeigojunior-wuyqysc66uknyiyvpdvaw2.streamlit.app/';client=None;err=None
 if url and key:
  try:client=server_client(url,key) if https(url) else None
  except Exception:err='Supabaseに接続できません。端末内で学習できます。'
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
   try:
    ticket=st.session_state.get('pending_launch')
    profile,linked=claim_identity(client,device,ticket)
    if ticket:st.session_state['plan_launch']=verified_plan_launch(client,ticket,profile)
    history=list_history(client,profile)
    publish_catalog(client,app_url)
    st.session_state.pop('pending_launch',None)
    if 'cm_launch' in st.query_params:del st.query_params['cm_launch']
   except Exception:
    profile='local:'+proof[:32];linked=False;message='データベースに接続できません。端末内で学習できます。'
  st.session_state['device']=device
  st.session_state['identity']=dict(profile_id=profile,linked=linked,history=history,
   link_message=('Supabaseに保存できます' if linked else (message or '端末内のみ保存・ちょこまな未連携')))
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
   except Exception:ack['message']='DB保存を確認できません。端末の未送信記録を保持します。'
  else:ack['message']='端末内保存のみ。ちょこまな未連携です。'
  st.session_state['ack']=ack;st.rerun()

if __name__=='__main__':
 if '--catalog-count' in sys.argv:
  print(json.dumps(dict(menus=len(MENUS),questions=len(QUESTIONS),skills=sum(r['entry_type']=='skill' for r in CATALOG_ROWS),content_version=CONTENT_VERSION),ensure_ascii=False))
 else:main()
