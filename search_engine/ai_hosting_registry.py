"""External AI model hosting registry for VALE.

Secrets are Fernet-encrypted with the same stable SECRET_KEY as Storage Command Center.
Model weights and inference stay on external providers; this service stores metadata/endpoints only.
"""
from __future__ import annotations
import base64, hashlib, json, os
from datetime import datetime, timezone
from urllib.parse import urlparse
from typing import Any
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import create_engine, text
from search_engine.storage_registry import _primary_database_url, _PG_CONNECT_ARGS

PREFIX="VALE-AI-HOSTING-V1:"
PROVIDERS=[
 {"id":"kaggle","name":"Kaggle","console_url":"https://www.kaggle.com/code"},
 {"id":"lightning","name":"Lightning AI","console_url":"https://lightning.ai"},
 {"id":"saturn","name":"Saturn Cloud","console_url":"https://saturncloud.io"},
 {"id":"hf_endpoints","name":"Hugging Face Inference Endpoints","console_url":"https://huggingface.co/inference-endpoints"},
 {"id":"hf_spaces","name":"Hugging Face Spaces","console_url":"https://huggingface.co/spaces"},
 {"id":"runpod","name":"RunPod","console_url":"https://www.runpod.io/console"},
 {"id":"modal","name":"Modal","console_url":"https://modal.com"},
 {"id":"replicate","name":"Replicate","console_url":"https://replicate.com"},
 {"id":"custom","name":"Custom endpoint","console_url":""},
]
MODELS=[
 {"model_key":"vision","name":"Vision AI","repo_id":"MdTauqueer/Visionvale","task":"image-to-structured-evidence"},
 {"model_key":"trading","name":"Trading AI","repo_id":"MdTauqueer/vale-trading-model","task":"text-analysis"},
]
def _fernet():
 secret=(os.getenv("SECRET_KEY") or "").strip()
 if len(secret)<32: raise RuntimeError("Set a stable SECRET_KEY of at least 32 characters in Render before saving AI hosting credentials.")
 key=base64.urlsafe_b64encode(hashlib.sha256(secret.encode()).digest())
 return Fernet(key)
def encrypt(data:dict)->str:
 return _fernet().encrypt((PREFIX+json.dumps(data,separators=(",",":"))).encode()).decode()
def decrypt(value:str)->dict:
 try: raw=_fernet().decrypt(value.encode()).decode()
 except InvalidToken as e: raise RuntimeError("AI hosting credential cannot be decrypted. Confirm SECRET_KEY has not changed.") from e
 if not raw.startswith(PREFIX): raise RuntimeError("Invalid AI hosting credential record.")
 return json.loads(raw[len(PREFIX):])
def engine():
 url=_primary_database_url()
 if url.startswith("sqlite"): return create_engine(url,pool_pre_ping=True,connect_args={"check_same_thread":False})
 return create_engine(url,pool_pre_ping=True,pool_recycle=300,connect_args=dict(_PG_CONNECT_ARGS))
def init():
 e=engine()
 try:
  with e.begin() as c:
   c.execute(text("""CREATE TABLE IF NOT EXISTS vale_ai_hosting_providers(
    id INTEGER PRIMARY KEY, name VARCHAR(100) NOT NULL, provider_type VARCHAR(40) NOT NULL,
    encrypted_config TEXT NOT NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at VARCHAR(40) NOT NULL)"""))
   c.execute(text("""CREATE TABLE IF NOT EXISTS vale_ai_hosting_models(
    model_key VARCHAR(30) PRIMARY KEY, name VARCHAR(100) NOT NULL, repo_id VARCHAR(250) NOT NULL,
    provider_id INTEGER NULL, enabled BOOLEAN NOT NULL DEFAULT TRUE,
    updated_at VARCHAR(40) NOT NULL)"""))
   c.execute(text("""CREATE TABLE IF NOT EXISTS vale_ai_hosting_settings(
    setting_key VARCHAR(80) PRIMARY KEY, encrypted_value TEXT NOT NULL,
    updated_at VARCHAR(40) NOT NULL)"""))
   if e.dialect.name=="postgresql":
    c.execute(text("CREATE SEQUENCE IF NOT EXISTS vale_ai_hosting_providers_id_seq"))
    c.execute(text("ALTER TABLE vale_ai_hosting_providers ALTER COLUMN id SET DEFAULT nextval('vale_ai_hosting_providers_id_seq')"))
    c.execute(text("SELECT setval('vale_ai_hosting_providers_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM vale_ai_hosting_providers),0)+1,1), false)"))
   for m in MODELS:
    c.execute(text("""INSERT INTO vale_ai_hosting_models(model_key,name,repo_id,provider_id,enabled,updated_at)
      VALUES(:k,:n,:r,NULL,TRUE,:t) ON CONFLICT(model_key) DO NOTHING"""),
      {"k":m["model_key"],"n":m["name"],"r":m["repo_id"],"t":datetime.now(timezone.utc).isoformat()})
 finally:e.dispose()
def list_providers(reveal=False):
 init(); e=engine()
 try:
  with e.connect() as c: rows=c.execute(text("SELECT * FROM vale_ai_hosting_providers ORDER BY id")).mappings().all()
  out=[]
  for r in rows:
   cfg=decrypt(r["encrypted_config"])
   item={"id":r["id"],"name":r["name"],"provider_type":r["provider_type"],"enabled":bool(r["enabled"]),
    "endpoint_url":cfg.get("endpoint_url",""),"console_url":cfg.get("console_url",""),
    "protocol":cfg.get("protocol","openai"),"has_credentials":bool(cfg.get("api_key") or cfg.get("provider_token")),
    "created_at":r["created_at"]}
   if reveal:item["_config"]=cfg
   out.append(item)
  return out
 finally:e.dispose()
def add_provider(name,provider_type,endpoint_url,api_key="",provider_token="",console_url="",protocol="openai"):
 init()
 if provider_type not in {p["id"] for p in PROVIDERS}: raise ValueError("Unsupported provider type.")
 if not endpoint_url.startswith("https://"): raise ValueError("Inference endpoint must use HTTPS.")
 parsed=urlparse(endpoint_url)
 if parsed.username or parsed.password or parsed.query or parsed.fragment:
  raise ValueError("Do not embed credentials or query parameters in the endpoint URL. Use the encrypted credential fields.")
 if len(name.strip())<2: raise ValueError("Enter a provider connection name.")
 cfg={"endpoint_url":endpoint_url.rstrip("/"),"api_key":api_key,"provider_token":provider_token,
      "console_url":console_url,"protocol":protocol if protocol in ("openai","huggingface") else "openai"}
 e=engine()
 try:
  with e.begin() as c:
   result=c.execute(text("""INSERT INTO vale_ai_hosting_providers(name,provider_type,encrypted_config,enabled,created_at)
    VALUES(:n,:p,:cfg,TRUE,:t) RETURNING id"""),{"n":name.strip()[:100],"p":provider_type,"cfg":encrypt(cfg),"t":datetime.now(timezone.utc).isoformat()})
   return int(result.scalar())
 finally:e.dispose()
def assign_model(model_key,provider_id,repo_id=None):
 if model_key not in ("vision","trading"): raise ValueError("Unknown VALE model.")
 e=engine()
 try:
  with e.begin() as c:
   if provider_id is not None:
    row=c.execute(text("SELECT id FROM vale_ai_hosting_providers WHERE id=:id AND enabled=TRUE"),{"id":int(provider_id)}).first()
    if not row: raise ValueError("Selected hosting provider is missing or disabled.")
   c.execute(text("""UPDATE vale_ai_hosting_models SET provider_id=:p,repo_id=:r,updated_at=:t WHERE model_key=:k"""),
    {"p":provider_id,"r":repo_id or next(x["repo_id"] for x in MODELS if x["model_key"]==model_key),"t":datetime.now(timezone.utc).isoformat(),"k":model_key})
 finally:e.dispose()
def list_models():
 init();e=engine()
 try:
  with e.connect() as c: rows=c.execute(text("""SELECT m.*,p.name AS provider_name,p.provider_type,p.encrypted_config
    FROM vale_ai_hosting_models m LEFT JOIN vale_ai_hosting_providers p ON p.id=m.provider_id ORDER BY m.model_key""")).mappings().all()
  out=[]
  for r in rows:
   out.append({"model_key":r["model_key"],"name":r["name"],"repo_id":r["repo_id"],"provider_id":r["provider_id"],
    "provider_name":r["provider_name"],"provider_type":r["provider_type"],"enabled":bool(r["enabled"]),
    "assigned":r["provider_id"] is not None})
  return out
 finally:e.dispose()
def save_hf_token(token):
 init(); e=engine()
 try:
  with e.begin() as c:
   c.execute(text("""INSERT INTO vale_ai_hosting_settings(setting_key,encrypted_value,updated_at)
    VALUES('huggingface_token',:v,:t) ON CONFLICT(setting_key) DO UPDATE SET encrypted_value=excluded.encrypted_value,updated_at=excluded.updated_at"""),
    {"v":encrypt({"token":token}),"t":datetime.now(timezone.utc).isoformat()})
 finally:e.dispose()
def get_hf_token():
 init();e=engine()
 try:
  with e.connect() as c:r=c.execute(text("SELECT encrypted_value FROM vale_ai_hosting_settings WHERE setting_key='huggingface_token'")).first()
  return decrypt(r[0]).get("token","") if r else ""
 finally:e.dispose()
def remove_provider(pid):
 e=engine()
 try:
  with e.begin() as c:
   c.execute(text("UPDATE vale_ai_hosting_models SET provider_id=NULL WHERE provider_id=:id"),{"id":int(pid)})
   result=c.execute(text("DELETE FROM vale_ai_hosting_providers WHERE id=:id"),{"id":int(pid)})
   return result.rowcount>0
 finally:e.dispose()
