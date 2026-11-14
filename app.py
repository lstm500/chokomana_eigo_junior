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
