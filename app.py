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

APP_VERSION='1.2.0'
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
  idx=int(kind.split('_')[1]);depends=[f'english.alphabet_{idx-1}.beginner'] if idx>1 else []
 elif stage=='matching':depends=['english.alphabet_5.beginner']
 else:depends=['english.matching_'+kind.split('_',1)[1]+'.beginner']
 next_ids=([f'english.alphabet_{idx+1}.beginner'] if idx<5 else [f'english.matching_{g}.beginner' for g in GROUPS]) if stage=='alphabet' else ([f'english.quiz_{kind.split("_",1)[1]}.beginner'] if stage=='matching' else [])
 MENUS.append(dict(menu_id=f'english.{kind}.beginner',label=label,category_id=kind,category_label=label,
  description=description,emoji=emoji,stamp_char=stamp,reading=reading,difficulty_id='beginner',difficulty_order=1,
  learning_stage=stage,progression_group_id=f'english.{stage}',skill_ids=sorted({s for q in pool for s in q['skill_ids']}),
  prerequisite_skill_ids=depends,requires_menu_ids=depends,planned_question_count=count,question_count=count,
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

def normalize_events(events,profile):
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
   app_version=APP_VERSION,content_version=CONTENT_VERSION,attempt_id=valid_uuid(raw['attempt_id']),
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
 summary=calculate_summary(raw_summary);validated=normalize_events(events,profile)
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
   category_id=summary['category_id'],difficulty_id=summary['difficulty_id'],content_version=CONTENT_VERSION,
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
 event=component()(**args,key='cm_english_board_v12',default=None)
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
