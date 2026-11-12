# -*- coding: utf-8 -*-
"""Chokomana English: alphabet -> picture-word matching -> 4-choice checks.
Run: streamlit run app.py. A single file has the complete frontend embedded.
"""
from __future__ import annotations
import hashlib
import logging
import json
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

APP_VERSION='1.9.3'
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

# New speaking-first courses. Keep all legacy menu/question IDs intact so
# older local events can still be uploaded and completed without silent loss.
VOICE_LETTERS={'alphabet_6':'ABCDEFGHIJKLMN','alphabet_7':'OPQRSTUVWXYZ'}
for kind,letters in VOICE_LETTERS.items():
 CAT[kind]=(f'アルファベット {letters[0]}〜{letters[-1]}',
            'おとを きいて、マイクで はつおんしよう','🔤','字','じ',len(letters),len(letters)*25)
 for letter in letters:
  QUESTIONS.append(question(kind,letter.lower(),'きいて まねして はなそう',
   dict(mode='letter',text=letter,small=letter.lower()),letter,
   [dict(id='speech_ok',text='にんしき できた'),dict(id='speech_mismatch',text='にんしき できなかった'),dict(id='speech_unverified',text='ききとり みかくにん')],
   'speech_ok','おとを もういちど きいて、はっきり いってみよう。',
   f'{letter} の なまえを いってみよう。','alphabet:voice_letter','english.alphabet.speech',
   'automatic','alphabet',True))

EXTRA_WORD_DATA={
 'animals':'lion|ライオン|🦁;elephant|ぞう|🐘;rabbit|うさぎ|🐰;bear|くま|🐻;monkey|さる|🐵;horse|うま|🐴',
 'colors':'black|くろ|⚫;white|しろ|⚪;pink|ピンク|🩷;orange|オレンジいろ|🟠;purple|むらさき|🟣;brown|ちゃいろ|🟤',
 'foods':'egg|たまご|🥚;rice|ごはん|🍚;cheese|チーズ|🧀;cake|ケーキ|🍰;pear|なし|🍐;carrot|にんじん|🥕',
 'transport':'airplane|ひこうき|✈️;boat|ボート|⛵;taxi|タクシー|🚕;truck|トラック|🚚;ship|ふね|🚢;helicopter|ヘリコプター|🚁',
 'nature':'snow|ゆき|❄️;tree|き|🌳;flower|はな|🌸;cloud|くも|☁️;mountain|やま|⛰️;river|かわ|🏞️',
 'numbers':'five|ご|5️⃣;six|ろく|6️⃣;seven|なな|7️⃣;eight|はち|8️⃣;nine|きゅう|9️⃣;ten|じゅう|🔟',
}
ALL_WORDS=list(W)
for group,raw in EXTRA_WORD_DATA.items():
 for token in raw.split(';'):
  en,ja,picture=token.split('|');ALL_WORDS.append(dict(key=en,en=en,ja=ja,emoji=picture,group=group))
assert len(ALL_WORDS)==60 and len({w['en'] for w in ALL_WORDS})==60
for group,label in GROUPS.items():
 words=[w for w in ALL_WORDS if w['group']==group]
 assert len(words)==10
 CAT['matching10_'+group]=(f'{label}の えと たんご','えと えいごを つなごう','🧩','結','けつ',10,460)
 CAT['quiz10_'+group]=(f'{label}の 4たく','えいごと えを 4たくで たしかめよう','✅','確','かく',10,390)
 for i,w in enumerate(words):
  distractors=[words[(i+2)%10],words[(i+5)%10]]
  pair=[dict(id=x['key'],text=x['en']) for x in [w,*distractors]]
  opts=choices(pair,w['key'],'matching10:'+w['key'])
  QUESTIONS.append(question('matching10_'+group,w['key'],
   'えと たんごを つなごう。',dict(mode='picture',emoji=w['emoji'],label=''),w['en'],opts,w['key'],
   'おとを きいて、ことばを えらぼう。',f'{w["emoji"]} は {w["en"]} だよ。',
   'matching:picture_word_v2:'+group,'english.matching.'+group,'automatic','matching',False))
  picks=[w,words[(i+3)%10],words[(i+6)%10],words[(i+8)%10]]
  if i%2==0:
   options=choices([dict(id=x['key'],text=x['ja'],emoji=x['emoji']) for x in picks],w['key'],'quiz10s:'+w['key'])
   cue=dict(mode='audio',text='おとを きこう');speech=w['en'];prompt='きこえた えいごは どの え？'
  else:
   options=choices([dict(id=x['key'],text=x['en']) for x in picks],w['key'],'quiz10p:'+w['key'])
   cue=dict(mode='picture',emoji=w['emoji'],label='');speech='';prompt='この えの えいごを えらぼう。'
  QUESTIONS.append(question('quiz10_'+group,w['key'],prompt,cue,speech,options,w['key'],
   'おとと えを もういちど たしかめよう。',f'{w["emoji"]} は {w["en"]} だよ。',
   'quiz:picture_sound_v2:'+group,'english.quiz.vocabulary.'+group,'automatic','quiz',False))
CAT['speech_words']=('ランダム たんご 10もん','えいごを よんで こえで こたえよう','🎤','声','せい',10,390)
for w in ALL_WORDS:
 QUESTIONS.append(question('speech_words',w['key'],
  'この たんごを えいごで よんでみよう。',dict(mode='written',text=w['en']),'',
  [dict(id='speech_ok',text='にんしき できた'),dict(id='speech_mismatch',text='にんしき できなかった'),dict(id='speech_unverified',text='ききとり みかくにん')],
  'speech_ok','はつおんを もういちど ためしてみよう。',f'{w["en"]} を いってみよう。',
  'speech:random_word','english.speaking.word','automatic','speech',True))
QUESTION_BY_ID={q['question_id']:q for q in QUESTIONS}
assert len(QUESTIONS)==len(QUESTION_BY_ID)==304
MENUS=[]
for kind,(label,description,emoji,stamp,reading,count,seconds) in CAT.items():
 pool=[q for q in QUESTIONS if q['category_id']==kind]
 stage='alphabet' if kind.startswith('alphabet_') else ('matching' if kind.startswith('matching') else ('quiz' if kind.startswith('quiz') else 'speech'))
 is_legacy=(kind.startswith('alphabet_') and int(kind.split('_')[1])<6) or kind.startswith('matching_') or kind.startswith('quiz_')
 assert len(pool)>=count
 if stage=='alphabet':
  idx=int(kind.split('_')[1]);depends=[];prerequisite_skills=[]
  suggested_prior=[f'english.alphabet_{idx-1}.beginner'] if idx>1 and idx!=6 else []
 elif stage=='matching':
  depends=[];prerequisite_skills=[];suggested_prior=['english.alphabet_6.beginner']
 elif stage=='quiz':
  group=kind.split('_',1)[1]
  if kind.startswith('quiz10_'):
   group=kind.split('quiz10_',1)[1];ref='matching10_'+group
  else:ref='matching_'+group
  depends=['english.'+ref+'.beginner'];prerequisite_skills=['english.matching.'+group];suggested_prior=depends
 else:
  depends=['english.alphabet_6.beginner'];prerequisite_skills=[];suggested_prior=depends
 if stage=='alphabet':
  next_ids=(['english.speech_words.beginner','english.alphabet_7.beginner'] if kind=='alphabet_6' else
            ['english.speech_words.beginner'] if kind=='alphabet_7' else [])
 elif stage=='matching':next_ids=['english.quiz10_'+kind.split('matching10_',1)[1]+'.beginner'] if kind.startswith('matching10_') else []
 else:next_ids=[]
 MENUS.append(dict(menu_id=f'english.{kind}.beginner',label=label,category_id=kind,category_label=label,
  description=description,emoji=emoji,stamp_char=stamp,reading=reading,difficulty_id='beginner',difficulty_order=1,
  learning_stage=stage,progression_group_id=f'english.{stage}',skill_ids=sorted({s for q in pool for s in q['skill_ids']}),
  prerequisite_skill_ids=prerequisite_skills,requires_menu_ids=depends,recommended_previous_menu_ids=suggested_prior,
  selection_policy='learner_choice',planned_question_count=count,question_count=count,
  available_question_count=len(pool),estimated_duration_ms=seconds*1000,duration_basis='provisional',
  duration_rationale='学習開始時の仮の時間。実施履歴によって後で調整する。',
  next_menu_ids=next_ids,age_min=None,age_max=None,age_basis=None,launch_url=None,supports_direct_launch=False,
  selection_instructions=['英語アプリを開く',label+'を選ぶ','開始する'],
  presentation_mode=('voice_alphabet' if kind in ('alphabet_6','alphabet_7') else
                     'single_matching10' if kind.startswith('matching10_') else
                     'voice_random10' if stage=='speech' else 'standard'),
  is_active=not is_legacy))
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
  client.table('chokomana_learning_catalog').upsert(batch,on_conflict='source_app,entry_type,entry_id,content_version',ignore_duplicates=True,default_to_null=False).execute()

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
  if q['assessment_method']=='automatic' and selected!='speech_unverified':
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
   chosen_order=sorted(p.get('choice_order') or [])
   expected_order=sorted(c['id'] for c in q['options'])
   legacy_voice_order=sorted(['speech_ok','speech_mismatch']) if q['category_id'] in ('alphabet_6','alphabet_7','speech_words') and content_version!=CONTENT_VERSION else []
   if chosen_order!=expected_order and chosen_order!=legacy_voice_order:raise ValueError('選択肢が一致しません')
   p.update(skill_ids=q['skill_ids'],question_family_id=q['question_family_id'],related_material_id=q['related_material_id'],passage_id=None)
  if event_type=='response_submitted':
   chosen=(p.get('response_value') or {}).get('choice_id')
   if chosen not in [c['id'] for c in q['options']]:raise ValueError('回答が不正です')
   if p.get('response_index') not in (1,2,3):raise ValueError('再回答回数が不正です')
   is_auto=q['assessment_method']=='automatic'
   if chosen=='speech_unverified':
    p.update(is_correct=None,assessment_method='unassessed',correctness_basis='asr_not_verified_v2',
      input_method='manual_next',response_status='skipped',self_report_success=None)
   else:
    p.update(is_correct=(chosen==q['correct_option_id'] if is_auto else None),assessment_method=q['assessment_method'],
     correctness_basis=('browser_asr_text_match_v1' if content_version!=CONTENT_VERSION else 'browser_asr_approximate_text_v2') if
       (q['learning_stage']=='speech' or (q['learning_stage']=='alphabet' and q['assessment_method']=='automatic')) else
       'catalog_exact_choice_v1' if is_auto else 'self_or_parent_confirmation',
     input_method=('browser_speech_recognition' if q['learning_stage']=='speech' or
      (q['learning_stage']=='alphabet' and q['assessment_method']=='automatic') else
      'tap_to_connect' if q['learning_stage']=='matching' else 'choice') if is_auto else 'guided_exposure',response_status='answered',
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
  client.table('chokomana_learning_events').upsert(validated,on_conflict='event_id',ignore_duplicates=True,default_to_null=False).execute()
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

# Single-file frontend embedded after build. No external frontend.html dependency.
from base64 import b64decode as _frontend_b64decode
from zlib import decompress as _frontend_decompress
_FRONTEND_B64 = (
    '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'
    '8WZlRvxT7UzWR7f9H2vPPso='
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
 if url and key:
  try:client=server_client(url,key) if https(url) else None
  except Exception:err='Supabaseに接続できません。端末内で学習できます。'
 if st.query_params.get('cm_launch'):
  ticket=str(st.query_params['cm_launch'])
  fingerprint=hashlib.sha256(ticket.encode()).hexdigest()
  if fingerprint!=st.session_state.get('launch_instance'):
   for name in ('identity','last_hello','last_seq','ack','device'):
    st.session_state.pop(name,None)
   st.session_state['launch_instance']=fingerprint
   st.session_state['pending_launch']=ticket
 ctx=st.session_state.get('identity')
 args=dict(menus=MENUS,questions=QUESTIONS,version=CONTENT_VERSION,hub_url=hub if https(hub) else '',identity_ready=bool(ctx),linked=False)
 if ctx:args.update(ctx)
 if st.session_state.get('ack'):args['ack']=st.session_state['ack']
 event=component()(**args,key='cm_english_board_v19_'+st.session_state.get('launch_instance','standalone')[:16],default=None)
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
    st.session_state.pop('pending_launch',None)
    if 'cm_launch' in st.query_params:del st.query_params['cm_launch']
   except Exception as exc:
    logging.getLogger('chokomana_english').warning('identity stage failed (%s)',type(exc).__name__)
    message='Supabaseで学習者を確認できませんでした（'+type(exc).__name__+'）'
    profile='local:'+proof[:32];linked=False
   if linked:
    warnings=[]
    try:history=list_history(client,profile)
    except Exception as exc:
     warnings.append('学習履歴取得（'+type(exc).__name__+'）')
     logging.getLogger('chokomana_english').warning('history stage failed (%s)',type(exc).__name__)
    try:publish_catalog(client,app_url)
    except Exception as exc:
     warnings.append('教材一覧登録（'+type(exc).__name__+'）')
     logging.getLogger('chokomana_english').warning('catalog stage failed (%s)',type(exc).__name__)
    message=('識別は成功しました。確認が必要：'+'・'.join(warnings)) if warnings else None
  st.session_state['device']=device
  st.session_state['identity']=dict(profile_id=profile,linked=linked,history=history,
   link_message=(message or ('Supabaseに保存できます' if linked else '端末内に保存しています')))
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
   except Exception as exc:
    # Keep private data out of the UI. The error code is enough for diagnostics.
    code=getattr(exc,'code',None)
    logging.getLogger('chokomana_english').error('DB record save failed: %s (code=%s)',type(exc).__name__,str(code or 'unknown'))
    ack['message']='学習記録をSupabaseへ保存できていません。端末の未送信記録を保持しています。'
    if isinstance(code,str) and code in ('23502','23503','23505','42501','PGRST204'):
     ack['error_code']=code
  else:ack['message']='端末内保存のみ。ちょこまな未連携です。'
  st.session_state['ack']=ack;st.rerun()

if __name__=='__main__':
 if '--catalog-count' in sys.argv:
  print(json.dumps(dict(menus=len(MENUS),questions=len(QUESTIONS),skills=sum(r['entry_type']=='skill' for r in CATALOG_ROWS),content_version=CONTENT_VERSION),ensure_ascii=False))
 else:main()
