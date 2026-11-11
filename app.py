# -*- coding: utf-8 -*-
"""Chokomana English: independent Streamlit app; common Supabase learning records.

No service role credentials are sent to the browser. Run: streamlit run app.py
"""
from __future__ import annotations
import hashlib
import json
import re
import sys
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

APP_VERSION='1.0.0'
SOURCE_APP='english'
LEVELS={'beginner':('はじめて',1),'intermediate':('なれてきた',2),'advanced':('ステップアップ',3)}
GROUPS={'animals':'どうぶつ','colors':'いろ','foods':'たべもの','transport':'のりもの','nature':'しぜん','numbers':'かず'}
CAT={
 'listening':('きいて わかる','えいごを きいて、あう えを えらぼう','👂','聞','きく',6,180),
 'speaking':('まねして はなす','おとを まねして はなそう','🗣️','話','はなす',4,180),
 'vocabulary':('ことばと え','えと ことばを むすびつけよう','🍎','語','ご',6,180),
 'phonics':('もじと おと','もじと おとの かんけいを しろう','🔤','音','おん',5,240),
 'conversation':('やりとり','きこえた ことばに へんじしよう','💬','会','かい',4,240),
 'reading':('よんで わかる','えいごを みて えを えらぼう','📖','読','どく',5,240),
 'alphabet':('アルファベット','おおもじと こもじを むすびつけよう','🔡','字','じ',6,180),
}

def words(level,group,raw):
 return [dict(key=x.split('|')[0],en=x.split('|')[0],ja=x.split('|')[1],emoji=x.split('|')[2],group=group,level=level) for x in raw.split(';')]
W=[]
for lv,groups in {
 'beginner':{
 'animals':'cat|ねこ|🐱;dog|いぬ|🐶;bird|とり|🐦;fish|さかな|🐟',
 'colors':'red|あか|🔴;blue|あお|🔵;yellow|きいろ|🟡;green|みどり|🟢',
 'foods':'apple|りんご|🍎;banana|バナナ|🍌;bread|パン|🍞;milk|ぎゅうにゅう|🥛',
 'transport':'train|でんしゃ|🚃;car|くるま|🚗;bus|バス|🚌;bike|じてんしゃ|🚲',
 'nature':'sun|たいよう|☀️;moon|つき|🌙;star|ほし|⭐;rain|あめ|🌧️',
 'numbers':'one|いち|1️⃣;two|に|2️⃣;three|さん|3️⃣;four|よん|4️⃣'},
 'intermediate':{
 'animals':'pig|ぶた|🐷;cow|うし|🐮;bear|くま|🐻;rabbit|うさぎ|🐰',
 'colors':'orange|オレンジ|🟠;pink|ピンク|🩷;black|くろ|⚫;white|しろ|⚪',
 'foods':'egg|たまご|🥚;rice|ごはん|🍚;grapes|ぶどう|🍇;water|みず|💧',
 'transport':'plane|ひこうき|✈️;boat|ふね|⛵;truck|トラック|🚚;taxi|タクシー|🚕',
 'nature':'tree|き|🌳;flower|はな|🌼;leaf|はっぱ|🍃;snow|ゆき|❄️',
 'numbers':'five|ご|5️⃣;six|ろく|6️⃣;seven|なな|7️⃣;eight|はち|8️⃣'},
 'advanced':{
 'animals':'horse|うま|🐴;lion|ライオン|🦁;duck|あひる|🦆;mouse|ねずみ|🐭',
 'colors':'purple|むらさき|🟣;brown|ちゃいろ|🟤;gray|はいいろ|◯;gold|きんいろ|🟨',
 'foods':'cheese|チーズ|🧀;pizza|ピザ|🍕;lemon|レモン|🍋;cake|ケーキ|🍰',
 'transport':'ship|おおきなふね|🚢;rocket|ロケット|🚀;subway|ちかてつ|🚇;scooter|キックボード|🛴',
 'nature':'cloud|くも|☁️;river|かわ|🏞️;mountain|やま|⛰️;sea|うみ|🌊',
 'numbers':'nine|きゅう|9️⃣;ten|じゅう|🔟;eleven|じゅういち|1️⃣1️⃣;twelve|じゅうに|1️⃣2️⃣'}
}.items():
 for group,raw in groups.items():W.extend(words(lv,group,raw))

DIALOGS={
 'beginner':[
 ('hello','Hello!','こんにちは','Hello!','こんにちは',['Good night.','Thank you.','Goodbye.']),
 ('morning','Good morning!','おはよう','Good morning!','おはよう',['Good night.','See you.','No, thanks.']),
 ('thanks','Thank you.','ありがとう',"You're welcome.",'どういたしまして',['Goodbye.','I am six.','Good night.']),
 ('bye','Goodbye!','さようなら','Goodbye!','さようなら',['Good morning!','I like cats.','Yes, please.']),
 ('name','What is your name?','なまえを きかれたよ','My name is Ken.','わたしのなまえはケンです',['I am hungry.','It is blue.','Good night.']),
 ('fine','How are you?','げんきか きかれたよ',"I'm fine, thank you.",'げんきです、ありがとう',['It is red.','One, two, three.','This is a cat.'])],
 'intermediate':[
 ('like','Do you like apples?','りんごが すきか きかれたよ','Yes, I do.','はい、すきです',['I am six.','That is big.','See you.']),
 ('hungry','Are you hungry?','おなかが すいたか きかれたよ','Yes, I am.','はい、すいています',['Good night.','I have a car.','It is yellow.']),
 ('color','What color is it?','いろを きかれたよ','It is red.','あかいろです',['I like dogs.','Thank you.','I am fine.']),
 ('age','How old are you?','なんさいか きかれたよ','I am six.','6さいです',['It is a cat.','Yes, I do.','Good morning.']),
 ('please','Here you are.','はい、どうぞ','Thank you.','ありがとう',['I am seven.','It is big.','Goodbye.']),
 ('weather','How is the weather?','てんきの はなしだよ','It is sunny.','はれです',['I am Ken.','This is a bus.','Yes, please.'])],
 'advanced':[
 ('where','Where is the train?','でんしゃは どこかな','It is here.','ここです',['I like bananas.','It is yellow.','Good morning.']),
 ('what','What is this?','これは なにかな','It is a dog.','いぬです',['Good evening.','I am fine.','I like red.']),
 ('count','How many cats?','ねこが なんびきかな','Two cats.','2ひきです',['I am six.','It is blue.','Goodbye.']),
 ('want','Would you like some water?','みずを すすめられたよ','Yes, please.','はい、おねがいします',['I am eight.','It is a train.','Good night.']),
 ('doing','What are you doing?','なにを しているか きかれたよ','I am reading.','よんでいます',['I am a cat.','It is sunny.','Thank you.']),
 ('help','Can you help me?','てつだってくれるか きかれたよ','Yes, I can.','はい、できます',['I am hungry.','A red bus.','Good evening.'])]
}
PHONICS={
 'beginner':[('ball','B'),('cat','C'),('dog','D'),('fish','F'),('moon','M'),('sun','S'),('train','T'),('pig','P'),('hat','H'),('red','R'),('van','V'),('zip','Z')],
 'intermediate':[('apple','A'),('egg','E'),('igloo','I'),('orange','O'),('up','U'),('jam','J'),('kite','K'),('leaf','L'),('nest','N'),('queen','Q'),('water','W'),('yarn','Y')],
 'advanced':[('cat','C'),('sun','S'),('pig','P'),('hat','H'),('pen','P'),('dog','D'),('red','R'),('cup','C'),('bus','B'),('bed','B'),('map','M'),('box','B')],
}

def choices(options,right,seed):
 d={x['id']:x for x in options}
 if right not in d:raise ValueError('missing correct choice')
 others=[x for k,x in d.items() if k!=right]
 others.sort(key=lambda x:hashlib.sha256((seed+x['id']).encode()).hexdigest())
 out=[d[right],*others[:3]]
 if len(out)!=4:raise ValueError('four choices required')
 out.sort(key=lambda x:hashlib.sha256((seed+'order'+x['id']).encode()).hexdigest())
 return out

def question(kind,level,key,prompt,cue,speech,options,correct,hint,explanation,family,skill,assessment='automatic'):
 return dict(question_id=f'english.{kind}.{level}.{key}',category_id=kind,difficulty_id=level,
 skill_ids=[skill],question_family_id=family,related_material_id='english.material.'+key,
 passage_id=None,speech_text=speech,prompt=prompt,cue=cue,options=options,correct_option_id=correct,
 hint=hint,explanation=explanation,assessment_method=assessment,
 answer_hidden_before_response=bool(speech))

def create_questions():
 qs=[]
 for level in LEVELS:
  level_words=[w for w in W if w['level']==level]
  for w in level_words:
   pool=[x for x in level_words if x['group']==w['group']]
   for kind in ('listening','vocabulary','reading'):
    if kind=='listening':
     opts=choices([dict(id=x['key'],text=x['ja'],emoji=x['emoji']) for x in pool],w['key'],f'l:{level}:{w["key"]}')
     prompt='きこえた ことばに あう えは どれ？';cue=dict(mode='audio',text='おとを きいてみよう');speech=w['en'];hint='ゆっくり もういちど きいてみよう。'
    elif kind=='vocabulary':
     opts=choices([dict(id=x['key'],text=x['en'],speak=x['en']) for x in pool],w['key'],f'v:{level}:{w["key"]}')
     prompt='この えは えいごで なんていう？';cue=dict(mode='picture',emoji=w['emoji'],label=w['ja']);speech='';hint='えらぶ ことばを タップして おとを たしかめよう。'
    else:
     opts=choices([dict(id=x['key'],text=x['ja'],emoji=x['emoji']) for x in pool],w['key'],f'r:{level}:{w["key"]}')
     prompt='えいごを よんで、あう えを えらぼう。';cue=dict(mode='written',text=w['en']);speech='';hint='もじを ひとつずつ みてみよう。'
    qs.append(question(kind,level,w['key'],prompt,cue,speech,opts,w['key'],hint,
     f'{w["en"]} は「{w["ja"]}」という いみだよ。',f'{kind}:{w["group"]}',f'english.{kind}.{w["group"]}'))
   qs.append(question('speaking',level,w['key'],'おとを きいて、まねして はなそう。',
    dict(mode='picture',emoji=w['emoji'],label=w['en']),w['en'],
    [dict(id='spoke',text='いえた！'),dict(id='practice',text='むずかしかった')],None,
    'ゆっくり くりかえして みよう。','発音の正しさは じどうで はんていしないよ。',
    'speaking:'+w['group'],'english.speaking.'+w['group'],'self_or_parent_confirmation'))
  for key,spoken,ja,right,right_ja,distractors in DIALOGS[level]:
   opts=choices([dict(id=f'correct-{key}',text=right,speak=right)]+[dict(id=f'alt-{key}-{i}',text=x,speak=x) for i,x in enumerate(distractors)],f'correct-{key}',f'conv:{level}:{key}')
   qs.append(question('conversation',level,key,'なんて へんじを する？',dict(mode='audio',text=ja),spoken,opts,
    f'correct-{key}','あいての ことばを もういちど きこう。',
    f'「{spoken}」には「{right}」（{right_ja}）が あうよ。','conversation:'+key,'english.conversation'))
  for word,letter in PHONICS[level]:
   if level=='advanced':
    opts=choices([dict(id=x,text=x) for x,_ in PHONICS[level]],word,'ph:'+word)
    prompt='きこえた ことばは どれ？';right=word;family='phonics:cvc'
    hint='さいしょ・まんなか・さいごの おとを きいてみよう。';explanation=f'{word} と かくよ。'
   else:
    letters=sorted({x[1] for x in PHONICS[level]})
    opts=choices([dict(id=x,text=x) for x in letters],letter,'ph:'+level+word)
    prompt='さいしょの おとは どの もじ？';right=letter;family='phonics:initial'
    hint='はじめの おとを きこう。';explanation=f'{word} は {letter} で はじまるよ。'
   qs.append(question('phonics',level,word,prompt,dict(mode='audio',text='おとを きこう'),word,opts,right,hint,explanation,family,'english.phonics'))
  alphabet='ABCDEFGHIJKLM' if level=='beginner' else 'NOPQRSTUVWXYZ' if level=='intermediate' else 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
  for letter in alphabet:
   opts=choices([dict(id=x.lower(),text=x.lower()) for x in alphabet],letter.lower(),'alpha:'+level+letter)
   qs.append(question('alphabet',level,letter.lower(),'おなじ アルファベットは どれ？',dict(mode='written',text=letter),letter,opts,letter.lower(),
     'おおもじと こもじを みくらべよう。',f'{letter} の こもじは {letter.lower()} だよ。','alphabet:case','english.alphabet'))
 return qs

QUESTIONS=create_questions()
QUESTION_BY_ID={q['question_id']:q for q in QUESTIONS}
assert len(QUESTIONS)==len(QUESTION_BY_ID)==394
MENUS=[]
for kind,(label,description,emoji,stamp,reading,count,seconds) in CAT.items():
 for level,(level_label,order) in LEVELS.items():
  pool=[q for q in QUESTIONS if q['category_id']==kind and q['difficulty_id']==level]
  assert len(pool)>=count
  MENUS.append(dict(menu_id=f'english.{kind}.{level}',label=f'{label}・{level_label}',
   category_id=kind,category_label=label,description=description,emoji=emoji,stamp_char=stamp,reading=reading,
   difficulty_id=level,difficulty_order=order,progression_group_id=f'english.{kind}',
   skill_ids=sorted({s for q in pool for s in q['skill_ids']}),prerequisite_skill_ids=[],
   planned_question_count=count,question_count=len(pool),estimated_duration_ms=seconds*1000,
   duration_basis='provisional',duration_rationale='初期目安。実測が3回以上蓄積したら中央値を使用。',
   next_menu_ids=[f'english.{kind}.{list(LEVELS)[order]}'] if order<3 else [],
   age_min=None,age_max=None,age_basis=None,launch_url=None,supports_direct_launch=False,
   selection_instructions=['英語アプリを開く',label+'を選ぶ',level_label+'を選ぶ','開始する'],is_active=True))
MENU_BY_ID={m['menu_id']:m for m in MENUS}
CONTENT_VERSION='english-'+hashlib.sha256(json.dumps(dict(menus=MENUS,questions=QUESTIONS),ensure_ascii=False,sort_keys=True).encode()).hexdigest()[:16]
CATALOG_ROWS=[]
for m in MENUS:
 CATALOG_ROWS.append(dict(schema_version=1,source_app=SOURCE_APP,entry_type='menu',entry_id=m['menu_id'],content_version=CONTENT_VERSION,payload=m))
for skill in sorted({s for q in QUESTIONS for s in q['skill_ids']}|{f'english.{k}' for k in CAT}):
 CATALOG_ROWS.append(dict(schema_version=1,source_app=SOURCE_APP,entry_type='skill',entry_id=skill,content_version=CONTENT_VERSION,
  payload=dict(skill_id=skill,label=skill.split('.')[-1],progression_group_id='.'.join(skill.split('.')[:2]))))
for q in QUESTIONS:
 CATALOG_ROWS.append(dict(schema_version=1,source_app=SOURCE_APP,entry_type='question',entry_id=q['question_id'],content_version=CONTENT_VERSION,
  payload=dict(question_id=q['question_id'],question_family_id=q['question_family_id'],related_material_id=q['related_material_id'],passage_id=None,
   skill_ids=q['skill_ids'],assessment_method=q['assessment_method'],choice_ids=[c['id'] for c in q['options']],
   correct_answer_spec=dict(choice_id=q['correct_option_id']),category_id=q['category_id'],difficulty_id=q['difficulty_id'])))

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
  client.table('chokomana_learning_catalog').upsert(batch,on_conflict='source_app,entry_type,entry_id,content_version',ignore_duplicates=True).execute()

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
 seen=set();clean=[];correct=0;objective=0;spoken=0
 for a in response:
  q=QUESTION_BY_ID.get(a.get('question_id'))
  if not q or f"english.{q['category_id']}.{q['difficulty_id']}"!=menu['menu_id'] or q['question_id'] in seen:raise ValueError('問題が一致しません')
  seen.add(q['question_id']);selected=a.get('selected')
  if selected not in {c['id'] for c in q['options']}:raise ValueError('選択肢が不正です')
  first=None
  if q['assessment_method']=='automatic':
   objective+=1;first=(selected==q['correct_option_id']);correct+=int(first)
  else:spoken+=int(selected=='spoke')
  clean.append(dict(question_id=q['question_id'],selected=selected,first_is_correct=first,
   skill_ids=q['skill_ids'],family_id=q['question_family_id'],support_before_response=a.get('support_before_response') or {},
   answer_latency_ms=a.get('answer_latency_ms'),reanswers=a.get('reanswers') or []))
 status=raw.get('status')
 if status not in ('completed','in_progress','abandoned','interrupted'):raise ValueError('実施状況が不正です')
 if status=='completed' and len(clean)!=menu['planned_question_count']:raise ValueError('完了の回答数が不正です')
 grade='white'
 if status=='completed' and objective==len(clean) and objective:
  r=correct/objective
  grade='gold' if r==1 else 'silver' if r>=.8 else 'bronze' if r>=.6 else 'white'
 return dict(attempt_id=attempt,menu_id=menu['menu_id'],category_id=menu['category_id'],difficulty_id=menu['difficulty_id'],
  content_version=CONTENT_VERSION,status=status,started_at=raw['started_at'],finished_at=raw.get('finished_at'),
  responses=clean,first_correct_count=correct,objective_count=objective,self_report_success_count=spoken,
  answered_count=len(clean),planned_question_count=menu['planned_question_count'],grade=grade,
  duration_ms=max(0,int(raw.get('duration_ms') or 0)),timing_quality=raw.get('timing_quality') or 'unknown')

def normalize_events(events,profile):
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
   if sorted(p.get('choice_order') or [])!=sorted(c['id'] for c in q['options']):raise ValueError('選択肢が一致しません')
   p.update(skill_ids=q['skill_ids'],question_family_id=q['question_family_id'],related_material_id=q['related_material_id'],passage_id=None)
  if event_type=='response_submitted':
   chosen=(p.get('response_value') or {}).get('choice_id')
   if chosen not in [c['id'] for c in q['options']]:raise ValueError('回答が不正です')
   if p.get('response_index') not in (1,2,3):raise ValueError('再回答回数が不正です')
   is_auto=q['assessment_method']=='automatic'
   p.update(is_correct=(chosen==q['correct_option_id'] if is_auto else None),assessment_method=q['assessment_method'],
     correctness_basis='catalog_exact_choice_v1' if is_auto else 'self_or_parent_confirmation',
     input_method='choice' if is_auto else 'self_check',response_status='answered',
     self_report_success=chosen=='spoke' if not is_auto else None)
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
   app_version=APP_VERSION,content_version=CONTENT_VERSION,attempt_id=valid_uuid(raw['attempt_id']),
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
 return True

def save_records(client,profile,device,events,raw_summary):
 if claim_identity(client,device)[0]!=profile:raise PermissionError('学習者が一致しません')
 summary=calculate_summary(raw_summary);validated=normalize_events(events,profile)
 if any(x['attempt_id']!=summary['attempt_id'] for x in validated):raise ValueError('実施IDが不一致です')
 if validated:
  olds=client.table('chokomana_learning_events').select('event_id,event_hash').in_('event_id',[x['event_id'] for x in validated]).execute().data or []
  lookup={x['event_id']:x['event_hash'] for x in olds}
  if any(lookup.get(x['event_id'],x['event_hash'])!=x['event_hash'] for x in validated):raise ValueError('イベントIDの内容が異なります')
  client.table('chokomana_learning_events').upsert(validated,on_conflict='event_id',ignore_duplicates=True).execute()
 completed=validated_completion(client,profile,summary) if summary['status']=='completed' else False
 state=dict(summary,status=summary['status'] if summary['status']!='completed' or completed else 'in_progress')
 old=client.table('english_attempts').select('status').eq('attempt_id',summary['attempt_id']).limit(1).execute().data
 if not(old and old[0]['status']=='completed' and state['status']!='completed'):
  row=dict(attempt_id=summary['attempt_id'],profile_id=profile,menu_id=summary['menu_id'],
   category_id=summary['category_id'],difficulty_id=summary['difficulty_id'],content_version=CONTENT_VERSION,
   started_at=summary['started_at'],finished_at=summary['finished_at'] if state['status']=='completed' else None,
   status=state['status'],duration_ms=state['duration_ms'],payload=state)
  client.table('english_attempts').upsert(row,on_conflict='attempt_id').execute()
 stamped=False
 if completed:
  m=MENU_BY_ID[summary['menu_id']]
  medal=dict(profile_id=profile,source_app=SOURCE_APP,attempt_id=summary['attempt_id'],
   category_key=m['category_id'],category_label=m['category_label'],stamp_char=m['stamp_char'],reading=m['reading'],
   difficulty=m['difficulty_id'],correct_count=summary['first_correct_count'],total_count=m['planned_question_count'],
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

FRONTEND=Path(__file__).with_name('frontend.html').read_text(encoding='utf-8')

def main():
 import streamlit as st
 st.set_page_config(page_title='ちょこまな（英語）',page_icon='🔤',layout='wide',initial_sidebar_state='collapsed')
 st.markdown('<style>.stApp{background:#f7f5ef}.block-container{padding:.3rem!important;max-width:1180px!important}header[data-testid="stHeader"]{display:none}</style>',unsafe_allow_html=True)
 def secret(k):
  try:return str(st.secrets.get(k,'')).strip()
  except Exception:return ''
 url=secret('SUPABASE_URL');key=secret('SUPABASE_SERVICE_ROLE_KEY') or secret('SUPABASE_SECRET_KEY')
 hub=secret('CHOKOMANA_HUB_URL');app_url=secret('ENGLISH_APP_URL');client=None;err=None
 if url and key:
  try:client=server_client(url,key) if https(url) else None
  except Exception:err='Supabaseに接続できません。端末内で学習できます。'
 if st.query_params.get('cm_launch'):
  ticket=str(st.query_params['cm_launch']);st.session_state['pending_launch']=ticket
 ctx=st.session_state.get('identity')
 args=dict(menus=MENUS,questions=QUESTIONS,version=CONTENT_VERSION,hub_url=hub if https(hub) else '',identity_ready=bool(ctx),linked=False)
 if ctx:args.update(ctx)
 if st.session_state.get('ack'):args['ack']=st.session_state['ack']
 event=component()(**args,key='cm_english_board_v1',default=None)
 if not isinstance(event,dict):return
 if event.get('action')=='hello':
  if event.get('hello_id')==st.session_state.get('last_hello'):return
  st.session_state['last_hello']=event.get('hello_id');device=event.get('device')
  try:proof=device_hash(device)
  except ValueError:return
  profile='local:'+proof[:32];linked=False;history=[];message=err
  if client:
   try:
    profile,linked=claim_identity(client,device,st.session_state.get('pending_launch'))
    history=list_history(client,profile)
    publish_catalog(client,app_url)
    st.session_state.pop('pending_launch',None)
    if 'cm_launch' in st.query_params:del st.query_params['cm_launch']
   except Exception:
    profile='local:'+proof[:32];linked=False;message='データベースに接続できません。端末内で学習できます。'
  st.session_state['device']=device
  st.session_state['identity']=dict(profile_id=profile,linked=linked,history=history,
   link_message=('Supabaseに保存できます' if linked else (message or '端末内のみ保存・ちょこまな未連携')))
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
   except Exception:ack['message']='DB保存を確認できません。端末の未送信記録を保持します。'
  else:ack['message']='端末内保存のみ。ちょこまな未連携です。'
  st.session_state['ack']=ack;st.rerun()

if __name__=='__main__':
 if '--catalog-count' in sys.argv:
  print(json.dumps(dict(menus=len(MENUS),questions=len(QUESTIONS),skills=sum(r['entry_type']=='skill' for r in CATALOG_ROWS),content_version=CONTENT_VERSION),ensure_ascii=False))
 else:main()
