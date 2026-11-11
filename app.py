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

APP_VERSION='1.1.0'
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

from base64 import b64decode as _frontend_b64decode
from zlib import decompress as _frontend_decompress
# Embedded frontend: deploying app.py alone must be sufficient.
# Compressed HTML is byte-for-byte identical to the supplied frontend.html.
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
