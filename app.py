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

APP_VERSION='1.9.11'
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
# An observable ASR gold medal is a gate, not a phonetic mastery claim.
for _menu in MENUS:
 if _menu['learning_stage'] in ('matching','quiz','listening'):
  _menu['unlock_requirements']={'all_best_grade_gold':['english.alphabet_6.beginner','english.alphabet_7.beginner','english.speech_words.beginner'], 'measurement':'browser_asr_near_match_not_pronunciation_score'}
  _menu['prerequisite_skill_ids']=[]
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
