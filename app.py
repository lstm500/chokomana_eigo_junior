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

APP_VERSION='1.9.12'
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
