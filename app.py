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
