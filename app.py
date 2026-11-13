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

APP_VERSION='1.9.9'
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
