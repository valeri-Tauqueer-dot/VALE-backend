from __future__ import annotations
import logging, requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from auth import verify_token
from search_engine import ai_hosting_registry as registry
from search_engine import ai_hosting_runtime as runtime

router=APIRouter(prefix="/storage/ai-hosting",tags=["VALE AI Model Hosting"])
security=HTTPBearer(auto_error=True)
log=logging.getLogger(__name__)
def current_user(credentials:HTTPAuthorizationCredentials=Depends(security)):
 user=verify_token(credentials.credentials)
 if not user: raise HTTPException(401,"Invalid or expired token.")
 return user
class ProviderIn(BaseModel):
 name:str=Field(min_length=2,max_length=100)
 provider_type:str=Field(min_length=2,max_length=40)
 endpoint_url:str=Field(min_length=8,max_length=2000)
 api_key:str=Field(default="",max_length=10000)
 provider_token:str=Field(default="",max_length=10000)
 console_url:str=Field(default="",max_length=1000)
 protocol:str=Field(default="openai")
 quota_limit_seconds:float|None=Field(default=None,gt=0)
 quota_period:str=Field(default="monthly")
 quota_switch_at_percent:float=Field(default=90,ge=50,le=100)
 start_url:str=Field(default="",max_length=2000)
 stop_url:str=Field(default="",max_length=2000)
class AssignIn(BaseModel):
 provider_id:int|None=None
 repo_id:str|None=None
class RoutesIn(BaseModel):
 provider_ids:list[int]=Field(default_factory=list,max_length=20)

class EnabledIn(BaseModel):
 enabled:bool

class TokenIn(BaseModel):
 token:str=Field(min_length=10,max_length=10000)
@router.get("/catalog")
def catalog(user:str=Depends(current_user)):
 return {"providers":registry.PROVIDERS,"models":registry.MODELS}
@router.get("/status")
def status(user:str=Depends(current_user)):
 from search_engine.hosting_quota import status as quota_status
 providers=registry.list_providers()
 detailed=[]
 for p in providers:
  cfg=next((x.get("_config") for x in registry.list_providers(reveal=True) if x["id"]==p["id"]),{}) or {}
  p["quota"]=quota_status(p["id"],cfg)
  p["lifecycle_control_configured"]=bool(cfg.get("start_url") or cfg.get("stop_url"))
  detailed.append(p)
 return {"providers":detailed,"models":registry.list_models(),"huggingface_token_configured":bool(registry.get_hf_token()),
         "quota_note":"Runtime accounting is measured by VALE and compared with operator-entered limits; it is not a provider-reported billing meter."}
@router.post("/providers")
def add_provider(data:ProviderIn,user:str=Depends(current_user)):
 try:
  pid=registry.add_provider(**data.dict())
  return {"success":True,"id":pid,"message":"Hosting endpoint credentials encrypted and saved."}
 except (ValueError,RuntimeError) as e: raise HTTPException(400,str(e))
@router.delete("/providers/{provider_id}")
def delete_provider(provider_id:int,user:str=Depends(current_user)):
 if not registry.remove_provider(provider_id): raise HTTPException(404,"Hosting connection not found.")
 return {"success":True,"message":"Provider connection removed; model assignments cleared."}
@router.post("/models/{model_key}/assign")
def assign(model_key:str,data:AssignIn,user:str=Depends(current_user)):
 try:
  registry.assign_model(model_key,data.provider_id,data.repo_id)
  return {"success":True,"message":"Model assignment updated."}
 except ValueError as e: raise HTTPException(400,str(e))
@router.post("/huggingface/token")
def set_hf(data:TokenIn,user:str=Depends(current_user)):
 try:
  r=requests.get("https://huggingface.co/api/whoami-v2",headers={"Authorization":"Bearer "+data.token},timeout=(8,20))
  if not r.ok: raise HTTPException(400,"Hugging Face rejected this token. Check it and try again.")
  registry.save_hf_token(data.token)
  return {"success":True,"message":"Hugging Face token verified and encrypted."}
 except requests.RequestException as e: raise HTTPException(502,"Could not reach Hugging Face to verify the token.") from e
@router.post("/huggingface/check-models")
def check_models(user:str=Depends(current_user)):
 token=registry.get_hf_token()
 headers={"Authorization":"Bearer "+token} if token else {}
 results=[]
 for m in registry.MODELS:
  try:
   r=requests.get("https://huggingface.co/api/models/"+m["repo_id"],headers=headers,timeout=(8,20))
   results.append({"repo_id":m["repo_id"],"status":"available" if r.ok else "not_verified","http_status":r.status_code})
  except requests.RequestException as e: results.append({"repo_id":m["repo_id"],"status":"check_failed","error":type(e).__name__})
 return {"models":results}
@router.post("/models/{model_key}/routes")
def set_routes(model_key:str,data:RoutesIn,user:str=Depends(current_user)):
 try:
  registry.set_model_routes(model_key,data.provider_ids)
  return {"success":True,"message":"Ordered failover route saved."}
 except ValueError as e: raise HTTPException(400,str(e))

@router.patch("/providers/{provider_id}/enabled")
def set_enabled(provider_id:int,data:EnabledIn,user:str=Depends(current_user)):
 if not registry.set_provider_enabled(provider_id,data.enabled): raise HTTPException(404,"Hosting connection not found.")
 return {"success":True,"enabled":data.enabled,"message":"Provider routing enabled." if data.enabled else "Provider disabled for new inference requests."}

@router.post("/providers/{provider_id}/control/{action}")
def provider_control(provider_id:int,action:str,user:str=Depends(current_user)):
 if action not in ("start","stop"): raise HTTPException(400,"Action must be start or stop.")
 try:
  from search_engine.ai_hosting_runtime import control_provider
  return control_provider(provider_id,action)
 except (ValueError,RuntimeError) as e: raise HTTPException(400,str(e))

@router.post("/providers/{provider_id}/health")
def provider_health(provider_id:int,user:str=Depends(current_user)):
 try:return runtime.health(provider_id)
 except Exception as e: raise HTTPException(400,str(e))
