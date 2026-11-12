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

APP_VERSION='1.9.1'
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
