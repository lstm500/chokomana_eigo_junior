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
  profile='local:'+proof[:32];linked=False;history=[];message=err;connection_code='client_init_failed' if err else 'config_missing'
  if client:
   ticket=st.session_state.get('pending_launch')
   try:
    profile,linked=claim_identity(client,device,ticket)
    connection_code='linked'
    st.session_state.pop('pending_launch',None)
    if 'cm_launch' in st.query_params:del st.query_params['cm_launch']
   except Exception as exc:
    logging.getLogger('chokomana_english').warning('identity stage failed (%s)',type(exc).__name__)
    connection_code='launch_ticket_rejected' if ticket else 'identity_unavailable'
    message='起動リンクが期限切れか、別の端末で使用されています。本体の「更新」を押して、新しいリンクから開いてください。' if ticket else '保存先で学習者を確認できませんでした。「連携を再確認」を押してください。'
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
  st.session_state['identity']=dict(profile_id=profile,linked=linked,history=history,identity_reply_id=event.get('hello_id'),connection_code=connection_code,
   link_message=(message or ('Supabaseに保存できます' if linked else '保存先の接続設定を確認できません。管理者に連絡してください。')))
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
