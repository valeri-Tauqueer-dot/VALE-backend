"""Runtime gateway for externally hosted VALE models. Never loads model weights in this process."""
from __future__ import annotations
import base64, json, time
import requests
from search_engine import ai_hosting_registry as registry

TIMEOUT=(10,180)
def provider_config(provider_id):
 row=next((p for p in registry.list_providers(reveal=True) if p["id"]==int(provider_id)),None)
 if not row or not row["enabled"]: raise RuntimeError("Assigned hosting provider is unavailable or disabled.")
 return row["_config"],row
def _headers(cfg):
 h={"Accept":"application/json"}
 if cfg.get("api_key"): h["Authorization"]="Bearer "+cfg["api_key"]
 return h
def health(provider_id):
 cfg,row=provider_config(provider_id); url=cfg["endpoint_url"].rstrip("/")
 try:
  start=time.monotonic()
  candidates=[url+"/health",url+"/v1/models",url]
  last=None
  for target in candidates:
   try:
    r=requests.get(target,headers=_headers(cfg),timeout=(8,15))
    if r.status_code not in (404,405): 
     elapsed=round((time.monotonic()-start)*1000)
     return {"status":"healthy" if r.ok else "endpoint_error","http_status":r.status_code,"latency_ms":elapsed,"checked_at":time.time()}
   except requests.RequestException as exc:last=exc
  raise last or RuntimeError("No health route responded.")
 except Exception as exc:
  return {"status":"unreachable","error":type(exc).__name__,"checked_at":time.time()}
def _json_response(r):
 if not r.ok: raise RuntimeError(f"Hosted model returned HTTP {r.status_code}: {r.text[:400]}")
 try:return r.json()
 except Exception:return {"text":r.text[:12000]}
def run_vision(image_bytes,content_type,question,model):
 if not model.get("assigned"): raise RuntimeError("Vision AI has no hosting provider assigned.")
 cfg,row=provider_config(model["provider_id"]); url=cfg["endpoint_url"].rstrip("/")
 if cfg.get("protocol")=="huggingface":
  headers=_headers(cfg); headers["Content-Type"]=content_type or "application/octet-stream"
  params={"wait_for_model":"false"}
  r=requests.post(url,data=image_bytes,headers=headers,params=params,timeout=TIMEOUT)
  data=_json_response(r)
 else:
  payload={"model":model["repo_id"],"messages":[{"role":"user","content":[
   {"type":"text","text":"Analyze this image. Return visible evidence only, uncertainty and chart labels. User question: "+(question or "Describe the chart.")},
   {"type":"image_url","image_url":{"url":"data:"+content_type+";base64,"+base64.b64encode(image_bytes).decode()}}
  ]}],"temperature":0.1}
  r=requests.post(url+"/chat/completions",json=payload,headers=_headers(cfg),timeout=TIMEOUT)
  data=_json_response(r)
 if isinstance(data,list) and data and isinstance(data[0],dict): data=data[0]
 if isinstance(data,dict):
  choices=data.get("choices")
  if choices:
   msg=choices[0].get("message",{}).get("content") or choices[0].get("text") or ""
   return {"description":msg if isinstance(msg,str) else json.dumps(msg),"structured_data":{"vision_raw":data}}
  return {"description":data.get("description") or data.get("generated_text") or data.get("text") or json.dumps(data)[:12000],
          "structured_data":{"vision_response":data}}
 return {"description":str(data)[:12000],"structured_data":{}}
def run_trading(prompt,model):
 if not model.get("assigned"): raise RuntimeError("Trading AI has no hosting provider assigned.")
 cfg,row=provider_config(model["provider_id"]);url=cfg["endpoint_url"].rstrip("/")
 if cfg.get("protocol")=="huggingface":
  r=requests.post(url,json={"inputs":prompt,"options":{"wait_for_model":False}},headers=_headers(cfg),timeout=TIMEOUT)
  data=_json_response(r)
  if isinstance(data,list) and data and isinstance(data[0],dict): data=data[0]
  if isinstance(data,dict): return str(data.get("generated_text") or data.get("text") or json.dumps(data))
  return str(data)
 r=requests.post(url+"/chat/completions",json={"model":model["repo_id"],"messages":[{"role":"user","content":prompt}],"temperature":0.2},
  headers=_headers(cfg),timeout=TIMEOUT)
 data=_json_response(r)
 try:return str(data["choices"][0]["message"]["content"])
 except Exception:return json.dumps(data)[:12000]
