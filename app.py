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

APP_VERSION='1.6.4'
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
