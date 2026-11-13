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

APP_VERSION='1.9.7'
SOURCE_APP='english'
# A medal is an observed result, not proof of full skill mastery. Older
# attempts keep the earlier criteria; the policy version is written at start.
MEDAL_POLICY_VERSION=3
MEDAL_PERCENT={'gold':90,'silver':70,'bronze':50}
def medal_minimum(total, percentage):
 return (total*percentage+99)//100
def medal_grade(score,total,policy=MEDAL_POLICY_VERSION,is_voice=False):
 if total<=0:return 'white'
 if policy==1:
  # Historical rules unchanged.
  return 'gold' if score==total else 'silver' if score*100>=80*total else 'bronze' if score*100>=60*total else 'white'
 if policy>=3 and is_voice:
  # Completing every item earns bronze, even if ASR cannot recognize speech.
  # Recognition is not a reliable acoustic pronunciation score.
  if score>=medal_minimum(total,90):return 'gold'
  if score>=medal_minimum(total,70):return 'silver'
  return 'bronze'
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

# Two-picture listening: the English sentence is heard before the answer is shown.
CAT['sentence_listen_1']=('えいごの ぶんを きいて えらぼう','みじかい えいごを きいて、えを 2つから えらぶ','🔊','聴','ちょう',10,420)
SENTENCE_SCENES=[('cat_box', 'The cat is on the box.', 'cat_on_box', 'cat_under_box', 'ねこが はこの うえに いるよ。'), ('dog_table', 'The dog is under the table.', 'dog_under_table', 'dog_on_table', 'いぬが テーブルの したに いるよ。'), ('red_apple', 'The apple is red.', 'red_apple', 'green_apple', 'りんごは あかいよ。'), ('blue_car', 'The car is blue.', 'blue_car', 'red_car', 'くるまは あおいよ。'), ('two_birds', 'I see two birds.', 'two_birds', 'three_birds', 'とりが 2わ いるよ。'), ('yellow_bus', 'The bus is yellow.', 'yellow_bus', 'blue_bus', 'バスは きいろいよ。'), ('sun_cloud', 'The sun is above the cloud.', 'sun_above_cloud', 'moon_above_cloud', 'くもの うえに たいようが あるよ。'), ('red_balloons', 'I see two red balloons.', 'red_balloons', 'blue_balloons', 'あかい ふうせんが 2こ あるよ。'), ('rabbit_tree', 'The rabbit is next to the tree.', 'rabbit_tree', 'rabbit_house', 'うさぎは きの となりに いるよ。'), ('fish_water', 'The fish is in the water.', 'fish_in_water', 'fish_out_water', 'さかなが みずの なかに いるよ。')]
for index,(item,spoken,correct_scene,other_scene,explain) in enumerate(SENTENCE_SCENES):
 options=choices([dict(id=correct_scene,text='え 1',scene=correct_scene),dict(id=other_scene,text='え 2',scene=other_scene)],correct_scene,'sentence_v1:'+item)
 QUESTIONS.append(question('sentence_listen_1',item,'おとを きいて、あう えを えらぼう',
  dict(mode='audio_sentence',text='みじかい えいご'),spoken,options,correct_scene,
  'もういちど きいてみよう。',explain,
  'sentence_listening:'+item,'english.listening.sentence', 'automatic','listening',False))
QUESTION_BY_ID={q['question_id']:q for q in QUESTIONS}
assert len(QUESTIONS)==len(QUESTION_BY_ID)==314
MENUS=[]
for kind,(label,description,emoji,stamp,reading,count,seconds) in CAT.items():
 pool=[q for q in QUESTIONS if q['category_id']==kind]
 stage='listening' if kind.startswith('sentence_') else ('alphabet' if kind.startswith('alphabet_') else ('matching' if kind.startswith('matching') else ('quiz' if kind.startswith('quiz') else 'speech')))
 is_legacy=(kind.startswith('alphabet_') and int(kind.split('_')[1])<6) or kind.startswith('matching_') or kind.startswith('quiz_')
 assert len(pool)>=count
 if stage=='alphabet':
  idx=int(kind.split('_')[1]);depends=[];prerequisite_skills=[]
  suggested_prior=[f'english.alphabet_{idx-1}.beginner'] if idx>1 and idx!=6 else []
 elif stage=='matching':
  depends=[];prerequisite_skills=[];suggested_prior=['english.alphabet_6.beginner']
 elif stage=='listening':
  depends=[];prerequisite_skills=[];suggested_prior=['english.matching10_animals.beginner']
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
                     'voice_random10' if stage=='speech' else 'two_picture_listening' if stage=='listening' else 'standard'),
  is_active=not is_legacy))
# Publish per-course rules for the chokomana catalog consumer.
for menu in MENUS:
 is_voice=menu['presentation_mode'] in ('voice_alphabet','voice_random10')
 menu['medal_criteria']={
  'policy_version':MEDAL_POLICY_VERSION,
  'basis':'voice_completion_and_asr_recognized_including_retries' if is_voice else (
      'first_response_correct' if menu['learning_stage']!='alphabet' else 'unscored_guided_exposure'),
  'total_questions':menu['planned_question_count'],
  'gold_min':medal_minimum(menu['planned_question_count'],90),
  'silver_min':medal_minimum(menu['planned_question_count'],70),
  'bronze_min':0 if is_voice else medal_minimum(menu['planned_question_count'],50),
  'below_bronze':'bronze_on_completion' if is_voice else 'white',
  'note':'音声は全問の練習完了で銅。銀・金はマイクの認識数に基づきます。発音の正確さの採点ではありません。' if is_voice else '最初の回答で採点します。'
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
 if type(policy) is not int or policy not in (1,2,MEDAL_POLICY_VERSION):raise ValueError('メダル採点規則の版が不正です')
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
  if policy in (2,MEDAL_POLICY_VERSION):
   grade=medal_grade(medal_points,menu['planned_question_count'],policy,menu['presentation_mode'] in ('voice_alphabet','voice_random10'))
  elif objective==len(clean) and objective:
   grade=medal_grade(correct,objective,1)
 return dict(attempt_id=attempt,menu_id=menu['menu_id'],category_id=menu['category_id'],difficulty_id=menu['difficulty_id'],
  content_version=CONTENT_VERSION,status=status,started_at=raw['started_at'],finished_at=raw.get('finished_at'),
  responses=clean,first_correct_count=correct,objective_count=objective,self_report_success_count=spoken,
  answered_count=len(clean),planned_question_count=menu['planned_question_count'],grade=grade,
  medal_policy_version=policy,medal_count=medal_points if policy in (2,MEDAL_POLICY_VERSION) else correct,
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
 if policy in (2,MEDAL_POLICY_VERSION):
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
  if medal_grade(awarded,menu['planned_question_count'],policy,voice)!=summary['grade']:
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
