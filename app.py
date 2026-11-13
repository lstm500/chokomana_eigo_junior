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

APP_VERSION='1.9.5'
SOURCE_APP='english'
# A medal is an observed result, not proof of full skill mastery. Older
# attempts keep the earlier criteria; the policy version is written at start.
MEDAL_POLICY_VERSION=2
MEDAL_PERCENT={'gold':90,'silver':70,'bronze':50}
def medal_minimum(total, percentage):
 return (total*percentage+99)//100
def medal_grade(score,total,policy=MEDAL_POLICY_VERSION):
 if total<=0:return 'white'
 if policy==1:
  # Previous version: only fully objectively evaluated attempts were graded.
  return 'gold' if score==total else 'silver' if score*100>=80*total else 'bronze' if score*100>=60*total else 'white'
 for grade,pct in MEDAL_PERCENT.items():
  if score>=medal_minimum(total,pct):return grade
 return 'white'

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
# Publish per-course rules for the chokomana catalog consumer.
for menu in MENUS:
 is_voice=menu['presentation_mode'] in ('voice_alphabet','voice_random10')
 menu['medal_criteria']={
  'policy_version':MEDAL_POLICY_VERSION,
  'basis':'asr_recognized_including_retries' if is_voice else (
      'first_response_correct' if menu['learning_stage']!='alphabet' else 'unscored_guided_exposure'),
  'total_questions':menu['planned_question_count'],
  'gold_min':medal_minimum(menu['planned_question_count'],90),
  'silver_min':medal_minimum(menu['planned_question_count'],70),
  'bronze_min':medal_minimum(menu['planned_question_count'],50),
  'below_bronze':'white',
  'note':'音声はブラウザによる認識結果であり、音響的な発音採点ではありません。' if is_voice else '最初の回答で採点します。'
 }
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
 seen=set();clean=[];correct=0;objective=0;spoken=0;medal_points=0;unverified_count=0
 policy=raw.get('medal_policy_version',1)
 if type(policy) is not int or policy not in (1,MEDAL_POLICY_VERSION):raise ValueError('メダル採点規則の版が不正です')
 for a in response:
  q=QUESTION_BY_ID.get(a.get('question_id'))
  if not q or f"english.{q['category_id']}.{q['difficulty_id']}"!=menu['menu_id'] or q['question_id'] in seen:raise ValueError('問題が一致しません')
  seen.add(q['question_id']);selected=a.get('selected')
  if selected not in {c['id'] for c in q['options']}:raise ValueError('選択肢が不正です')
  first=None
  if q['assessment_method']=='automatic' and selected!='speech_unverified':
   objective+=1;first=(selected==q['correct_option_id']);correct+=int(first)
  else:spoken+=int(selected=='seen')
  # Speech is practice: a later successful recognition on this item counts
  # toward the medal, while the *first* answer remains unchanged for learning analysis.
  is_voice=menu['presentation_mode'] in ('voice_alphabet','voice_random10')
  retries=a.get('reanswers') or []
  if not isinstance(retries,list):raise ValueError('再回答が不正です')
  allowed={o['id'] for o in q['options']}
  if any(not isinstance(r,dict) or r.get('selected') not in allowed for r in retries):raise ValueError('再回答が不正です')
  recognized=selected=='speech_ok' or any(r['selected']=='speech_ok' for r in retries)
  medal_points+=int(recognized if is_voice else first is True)
  unverified_count+=int(is_voice and not recognized and selected=='speech_unverified')
  clean.append(dict(question_id=q['question_id'],selected=selected,first_is_correct=first,
   skill_ids=q['skill_ids'],family_id=q['question_family_id'],support_before_response=a.get('support_before_response') or {},
   answer_latency_ms=a.get('answer_latency_ms'),reanswers=a.get('reanswers') or []))
 status=raw.get('status')
 if status not in ('completed','in_progress','abandoned','interrupted'):raise ValueError('実施状況が不正です')
 if status=='completed' and len(clean)!=menu['planned_question_count']:raise ValueError('完了の回答数が不正です')
 grade='white'
 if status=='completed' and len(clean)==menu['planned_question_count']:
  if policy==MEDAL_POLICY_VERSION:
   grade=medal_grade(medal_points,menu['planned_question_count'])
  elif objective==len(clean) and objective:
   grade=medal_grade(correct,objective,1)
 return dict(attempt_id=attempt,menu_id=menu['menu_id'],category_id=menu['category_id'],difficulty_id=menu['difficulty_id'],
  content_version=CONTENT_VERSION,status=status,started_at=raw['started_at'],finished_at=raw.get('finished_at'),
  responses=clean,first_correct_count=correct,objective_count=objective,self_report_success_count=spoken,
  answered_count=len(clean),planned_question_count=menu['planned_question_count'],grade=grade,
  medal_policy_version=policy,medal_count=medal_points if policy==MEDAL_POLICY_VERSION else correct,
  unverified_count=unverified_count,
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
 policy=summary.get('medal_policy_version',1)
 if policy!=starts[0]['payload'].get('medal_policy_version',1):
  raise ValueError('採点規則の版が一致しません')
 if policy==MEDAL_POLICY_VERSION:
  voice=menu['presentation_mode'] in ('voice_alphabet','voice_random10')
  if voice:
   verified=set()
   for e in rows:
    root=roots.get(e['occurrence_id'])
    if not root or root['question_id']!=e['question_id']:continue
    p=e['payload'] or {}
    if (e['event_type']=='response_submitted' and (p.get('response_value') or {}).get('choice_id')=='speech_ok'
      and p.get('is_correct') is True):verified.add(e['occurrence_id'])
    elif (e['event_type']=='learning_activity' and p.get('activity')=='speech_recognition_extra'
      and p.get('recognized') is True):verified.add(e['occurrence_id'])
   awarded=len(verified)
  else:awarded=points
  if awarded!=summary['medal_count']:raise ValueError('メダルの判定数が学習ログと一致しません')
  if medal_grade(awarded,menu['planned_question_count'])!=summary['grade']:
   raise ValueError('メダル等級が一致しません')
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
   difficulty=m['difficulty_id'],correct_count=summary['medal_count'],total_count=m['planned_question_count'],
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
