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

APP_VERSION='1.5.0'
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
 event=component()(**args,key='cm_english_board_v15',default=None)
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
