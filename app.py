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

APP_VERSION='1.3.0'
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
 event=component()(**args,key='cm_english_board_v13',default=None)
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
