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

APP_VERSION='1.4.0'
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
