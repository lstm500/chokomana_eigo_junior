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

APP_VERSION='1.9.0'
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
   [dict(id='speech_ok',text='にんしき できた'),dict(id='speech_mismatch',text='にんしき できなかった')],
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
  [dict(id='speech_ok',text='にんしき できた'),dict(id='speech_mismatch',text='にんしき できなかった')],
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
     correctness_basis=('browser_asr_text_match_v1' if q['learning_stage']=='speech' or
      (q['learning_stage']=='alphabet' and q['assessment_method']=='automatic') else
      'catalog_exact_choice_v1') if is_auto else 'self_or_parent_confirmation',
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
