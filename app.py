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
