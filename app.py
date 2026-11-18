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
