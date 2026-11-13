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

APP_VERSION='1.9.10'
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
