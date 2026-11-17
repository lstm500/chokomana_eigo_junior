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
