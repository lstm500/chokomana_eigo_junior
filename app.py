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

APP_VERSION='1.6.0'
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

def publish_catalog(client,url=None):
 for start in range(0,len(CATALOG_ROWS),150):
  batch=[]
  for original in CATALOG_ROWS[start:start+150]:
   row=dict(original)
   if row['entry_type']=='menu':row['payload']=dict(row['payload'],launch_url=url if url and https(url) else None)
   batch.append(row)
  client.table('chokomana_learning_catalog').upsert(batch,on_conflict='source_app,entry_type,entry_id,content_version',ignore_duplicates=True).execute()

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

def save_records(client,profile,device,events,raw_summary):
 if claim_identity(client,device)[0]!=profile:raise PermissionError('学習者が一致しません')
 summary=calculate_summary(raw_summary)
 # Older interrupted lessons may have already written part of their event stream.
 # Use that original immutable event version for the rest of the same attempt.
 previous=(client.table('chokomana_learning_events').select('content_version,app_version')
  .eq('profile_id',profile).eq('source_app',SOURCE_APP).eq('attempt_id',summary['attempt_id'])
  .limit(20).execute().data or [])
 versions={(x['content_version'],x['app_version']) for x in previous}
 if len(versions)>1:raise ValueError('同じ学習内で教材の版が一致しません')
 prior_content,prior_app=next(iter(versions)) if versions else (CONTENT_VERSION,APP_VERSION)
 summary['content_version']=prior_content
 validated=normalize_events(events,profile,prior_content,prior_app)
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
    'CwR6YYX9Q/gzBI1w59z/A4pRtCI='
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
 hub=secret('CHOKOMANA_HUB_URL');app_url=secret('ENGLISH_APP_URL');client=None;err=None
 if url and key:
  try:client=server_client(url,key) if https(url) else None
  except Exception:err='Supabaseに接続できません。端末内で学習できます。'
 if st.query_params.get('cm_launch'):
  ticket=str(st.query_params['cm_launch']);st.session_state['pending_launch']=ticket
 ctx=st.session_state.get('identity')
 args=dict(menus=MENUS,questions=QUESTIONS,version=CONTENT_VERSION,hub_url=hub if https(hub) else '',identity_ready=bool(ctx),linked=False)
 if ctx:args.update(ctx)
 if st.session_state.get('ack'):args['ack']=st.session_state['ack']
 event=component()(**args,key='cm_english_board_v16',default=None)
 if not isinstance(event,dict):return
 if event.get('action')=='hello':
  if event.get('hello_id')==st.session_state.get('last_hello'):return
  st.session_state['last_hello']=event.get('hello_id');device=event.get('device')
  try:proof=device_hash(device)
  except ValueError:return
  profile='local:'+proof[:32];linked=False;history=[];message=err
  if client:
   try:
    profile,linked=claim_identity(client,device,st.session_state.get('pending_launch'))
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
    result=save_records(client,ctx['profile_id'],event['device'],event.get('events') or [],event.get('summary'))
    ack.update(success=True,**result)
   except Exception:ack['message']='DB保存を確認できません。端末の未送信記録を保持します。'
  else:ack['message']='端末内保存のみ。ちょこまな未連携です。'
  st.session_state['ack']=ack;st.rerun()

if __name__=='__main__':
 if '--catalog-count' in sys.argv:
  print(json.dumps(dict(menus=len(MENUS),questions=len(QUESTIONS),skills=sum(r['entry_type']=='skill' for r in CATALOG_ROWS),content_version=CONTENT_VERSION),ensure_ascii=False))
 else:main()
