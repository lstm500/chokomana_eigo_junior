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
