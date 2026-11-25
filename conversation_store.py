"""Durable, user-scoped VALE conversation storage on the primary database."""
from __future__ import annotations
import json, uuid
from datetime import datetime, timezone
from sqlalchemy import text
from database import engine

_initialized = False

def init():
    global _initialized
    if _initialized: return
    with engine.begin() as c:
        c.execute(text('''CREATE TABLE IF NOT EXISTS vale_conversations (
            conversation_id VARCHAR(80) PRIMARY KEY, username VARCHAR(255) NOT NULL,
            title VARCHAR(300) NOT NULL DEFAULT 'New VALE conversation',
            created_at VARCHAR(40) NOT NULL, updated_at VARCHAR(40) NOT NULL)'''))
        c.execute(text('''CREATE TABLE IF NOT EXISTS vale_conversation_messages (
            id INTEGER PRIMARY KEY, conversation_id VARCHAR(80) NOT NULL,
            username VARCHAR(255) NOT NULL, role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}',
            created_at VARCHAR(40) NOT NULL)'''))
        if engine.dialect.name == 'postgresql':
            c.execute(text('CREATE SEQUENCE IF NOT EXISTS vale_conversation_messages_id_seq'))
            c.execute(text("ALTER TABLE vale_conversation_messages ALTER COLUMN id SET DEFAULT nextval('vale_conversation_messages_id_seq')"))
            c.execute(text("SELECT setval('vale_conversation_messages_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM vale_conversation_messages),0)+1,1), false)"))
    _initialized = True


def save_turn(username: str, conversation_id: str | None, user_text: str, answer: str, metadata=None):
    init(); cid = (conversation_id or '').strip()[:80] or str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat(); title = ' '.join(user_text.split())[:100] or 'New VALE conversation'
    meta = json.dumps(metadata or {}, ensure_ascii=False)
    with engine.begin() as c:
        c.execute(text('''INSERT INTO vale_conversations(conversation_id,username,title,created_at,updated_at)
          VALUES(:id,:u,:t,:n,:n) ON CONFLICT(conversation_id) DO UPDATE SET updated_at=excluded.updated_at'''),
          {'id':cid,'u':username,'t':title,'n':now})
        # Reject cross-user IDs rather than attaching messages to another account.
        owner = c.execute(text('SELECT username FROM vale_conversations WHERE conversation_id=:id'), {'id':cid}).scalar()
        if owner != username: raise PermissionError('Conversation does not belong to this account.')
        c.execute(text('''INSERT INTO vale_conversation_messages(conversation_id,username,role,content,metadata,created_at)
          VALUES(:id,:u,'user',:q,'{}',:n)'''), {'id':cid,'u':username,'q':user_text,'n':now})
        c.execute(text('''INSERT INTO vale_conversation_messages(conversation_id,username,role,content,metadata,created_at)
          VALUES(:id,:u,'assistant',:a,:m,:n)'''), {'id':cid,'u':username,'a':answer,'m':meta,'n':now})
    return cid


def list_conversations(username: str, limit=50):
    init()
    with engine.connect() as c:
        rows=c.execute(text('''SELECT v.conversation_id,v.title,v.created_at,v.updated_at,
          (SELECT COUNT(*) FROM vale_conversation_messages m WHERE m.conversation_id=v.conversation_id) AS message_count
          FROM vale_conversations v WHERE v.username=:u ORDER BY v.updated_at DESC LIMIT :n'''), {'u':username,'n':max(1,min(int(limit),100))}).mappings().all()
    return [dict(r) for r in rows]


def get_conversation(username: str, cid: str):
    init()
    with engine.connect() as c:
        owner=c.execute(text('SELECT 1 FROM vale_conversations WHERE conversation_id=:id AND username=:u'), {'id':cid,'u':username}).first()
        if not owner: return None
        rows=c.execute(text('''SELECT role,content,metadata,created_at FROM vale_conversation_messages
          WHERE conversation_id=:id AND username=:u ORDER BY id'''), {'id':cid,'u':username}).mappings().all()
    result=[]
    for r in rows:
        try: meta=json.loads(r['metadata'] or '{}')
        except Exception: meta={}
        result.append({'role':r['role'],'content':r['content'],'metadata':meta,'created_at':r['created_at']})
    return result


def delete_conversation(username: str, cid: str):
    init()
    with engine.begin() as c:
        owned=c.execute(text('SELECT 1 FROM vale_conversations WHERE conversation_id=:id AND username=:u'), {'id':cid,'u':username}).first()
        if not owned: return False
        c.execute(text('DELETE FROM vale_conversation_messages WHERE conversation_id=:id AND username=:u'), {'id':cid,'u':username})
        c.execute(text('DELETE FROM vale_conversations WHERE conversation_id=:id AND username=:u'), {'id':cid,'u':username})
        return True


def delete_all_conversations(username: str):
    init()
    with engine.begin() as c:
        c.execute(text('DELETE FROM vale_conversation_messages WHERE username=:u'), {'u':username})
        result=c.execute(text('DELETE FROM vale_conversations WHERE username=:u'), {'u':username})
        return int(result.rowcount or 0)
