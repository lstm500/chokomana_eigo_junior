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

APP_VERSION='1.9.2'
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
    's0M='
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
