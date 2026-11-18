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

APP_VERSION='1.9.13'
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
  'この たんごを えいごで よんでみよう。',dict(mode='written',text=w['en'],emoji=w['emoji'],picture_label=w['ja'],picture_group=w['group']),'',
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
     correctness_basis=('browser_asr_child_friendly_text_v3' if app_version==APP_VERSION else 'browser_asr_text_match_v1' if content_version!=CONTENT_VERSION else 'browser_asr_approximate_text_v2') if
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
_FRONTEND_B64 = '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'
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
