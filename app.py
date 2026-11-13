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

APP_VERSION='1.9.8'
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
    '7u+x+yWdxX'
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
