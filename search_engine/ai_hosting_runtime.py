"""Inference gateway for externally hosted VALE models with ordered failover and quota accounting."""
from __future__ import annotations
import base64, json, time
import requests
from search_engine import ai_hosting_registry as registry
from search_engine import hosting_quota

TIMEOUT=(10,180)

def provider_config(provider_id):
    row=next((p for p in registry.list_providers(reveal=True) if p["id"]==int(provider_id)),None)
    if not row or not row["enabled"]: raise RuntimeError("Assigned hosting provider is unavailable or disabled.")
    cfg=dict(row["_config"]); cfg["provider_type"]=row.get("provider_type")
    return cfg,row

def _headers(cfg):
    h={"Accept":"application/json"}
    credential=cfg.get("api_key") or (registry.get_hf_token() if cfg.get("provider_type") in ("hf_endpoints","hf_spaces") else "")
    if credential: h["Authorization"]="Bearer "+credential
    return h

def health(provider_id):
    cfg,row=provider_config(provider_id); url=cfg["endpoint_url"].rstrip("/")
    try:
        start=time.monotonic(); last=None
        models_url=url+"/models" if url.endswith("/v1") else url+"/v1/models"
        for target in (url+"/health",models_url,url):
            try:
                r=requests.get(target,headers=_headers(cfg),timeout=(8,15))
                if r.status_code not in (404,405):
                    return {"status":"healthy" if r.ok else "endpoint_error","http_status":r.status_code,
                            "latency_ms":round((time.monotonic()-start)*1000),"checked_at":time.time()}
            except requests.RequestException as exc: last=exc
        raise last or RuntimeError("No health route responded.")
    except Exception as exc:
        return {"status":"unreachable","error":type(exc).__name__,"checked_at":time.time()}

def control_provider(provider_id,action):
    cfg,row=provider_config(provider_id)
    target=cfg.get("start_url" if action=="start" else "stop_url")
    if not target: raise ValueError(f"No {action} control URL is configured for this provider. This provider cannot be remotely {action}ed by VALE.")
    try:
        headers=_headers(cfg)
        if cfg.get("provider_token"):
            headers["Authorization"]="Bearer "+cfg["provider_token"]
        r=requests.post(target,headers=headers,json={"provider_id":provider_id,"action":action},timeout=(8,30))
        if not r.ok: raise RuntimeError(f"Provider control endpoint returned HTTP {r.status_code}.")
        try: payload=r.json()
        except Exception: payload={"response":r.text[:500]}
        return {"success":True,"provider":row["name"],"action":action,"provider_response":payload}
    except requests.RequestException as exc:
        raise RuntimeError(f"Provider control request failed: {type(exc).__name__}.") from exc

def _chat_completions_url(base):
    base=base.rstrip("/")
    if base.endswith("/chat/completions"): return base
    if base.endswith("/v1"): return base+"/chat/completions"
    return base+"/v1/chat/completions"

def _json_response(r):
    if not r.ok: raise RuntimeError(f"Hosted model returned HTTP {r.status_code}: {r.text[:400]}")
    try:return r.json()
    except Exception:return {"text":r.text[:12000]}

def _maybe_start(provider_id,cfg):
    if cfg.get("start_url"):
        # Explicit lifecycle hook; endpoint owner must implement this contract.
        control_provider(provider_id,"start")
        deadline=time.monotonic()+60
        while time.monotonic()<deadline:
            state=health(provider_id)
            if state.get("status")=="healthy": return
            time.sleep(3)
        raise RuntimeError("Provider start was requested, but its inference endpoint did not become healthy within 60 seconds.")

def _vision_once(image_bytes,content_type,question,model,provider_id):
    cfg,row=provider_config(provider_id); _maybe_start(provider_id,cfg); url=cfg["endpoint_url"].rstrip("/")
    if cfg.get("protocol")=="huggingface":
        headers=_headers(cfg); headers["Content-Type"]=content_type or "application/octet-stream"
        r=requests.post(url,data=image_bytes,headers=headers,params={"wait_for_model":"false"},timeout=TIMEOUT); data=_json_response(r)
    else:
        payload={"model":model["repo_id"],"messages":[{"role":"user","content":[
          {"type":"text","text":"Analyze this image. Return visible evidence only, uncertainty and chart labels. User question: "+(question or "Describe the image.")},
          {"type":"image_url","image_url":{"url":"data:"+(content_type or "image/jpeg")+";base64,"+base64.b64encode(image_bytes).decode()}}]}],"temperature":0.1}
        r=requests.post(_chat_completions_url(url),json=payload,headers=_headers(cfg),timeout=TIMEOUT); data=_json_response(r)
    if isinstance(data,list) and data and isinstance(data[0],dict): data=data[0]
    if isinstance(data,dict):
        choices=data.get("choices")
        if choices:
            msg=choices[0].get("message",{}).get("content") or choices[0].get("text") or ""
            return {"description":msg if isinstance(msg,str) else json.dumps(msg),"structured_data":{"vision_raw":data}}
        return {"description":data.get("description") or data.get("generated_text") or data.get("text") or json.dumps(data)[:12000],"structured_data":{"vision_response":data}}
    return {"description":str(data)[:12000],"structured_data":{}}

def run_vision(image_bytes,content_type,question,model):
    if not model.get("assigned"): raise RuntimeError("Vision AI has no hosting provider assigned.")
    providers=registry.model_routes("vision") or [model["provider_id"]]; failures=[]
    for pid in providers:
        try:
            cfg,_=provider_config(pid); quota=hosting_quota.status(pid,cfg)
            if quota["switch_recommended"]: failures.append(f"provider {pid}: {quota['used_percent']}% of configured {quota['period']} runtime budget used; switching to next route"); continue
            start=time.monotonic()
            try: result=_vision_once(image_bytes,content_type,question,model,pid)
            except Exception:
                hosting_quota.record(pid,time.monotonic()-start,cfg.get("quota_period","monthly"))
                raise
            hosting_quota.record(pid,time.monotonic()-start,cfg.get("quota_period","monthly"))
            result["hosting_provider_id"]=pid; return result
        except Exception as exc: failures.append(f"provider {pid}: {type(exc).__name__}: {str(exc)[:180]}")
    raise RuntimeError("All configured Vision AI routes failed or reached their configured quota. "+" | ".join(failures))

def _trading_once(prompt,model,provider_id):
    cfg,row=provider_config(provider_id); _maybe_start(provider_id,cfg); url=cfg["endpoint_url"].rstrip("/")
    if cfg.get("protocol")=="huggingface":
        r=requests.post(url,json={"inputs":prompt,"options":{"wait_for_model":False}},headers=_headers(cfg),timeout=TIMEOUT)
        data=_json_response(r)
        if isinstance(data,list) and data and isinstance(data[0],dict): data=data[0]
        if isinstance(data,dict): return str(data.get("generated_text") or data.get("text") or json.dumps(data))
        return str(data)
    r=requests.post(_chat_completions_url(url),json={"model":model["repo_id"],"messages":[{"role":"user","content":prompt}],"temperature":0.2},headers=_headers(cfg),timeout=TIMEOUT)
    data=_json_response(r)
    try:return str(data["choices"][0]["message"]["content"])
    except Exception:return json.dumps(data)[:12000]

def run_trading(prompt,model):
    if not model.get("assigned"): raise RuntimeError("Trading AI has no hosting provider assigned.")
    providers=registry.model_routes("trading") or [model["provider_id"]]; failures=[]
    for pid in providers:
        try:
            cfg,_=provider_config(pid); quota=hosting_quota.status(pid,cfg)
            if quota["switch_recommended"]: failures.append(f"provider {pid}: {quota['used_percent']}% of configured {quota['period']} runtime budget used; switching to next route"); continue
            start=time.monotonic()
            try: result=_trading_once(prompt,model,pid)
            except Exception:
                hosting_quota.record(pid,time.monotonic()-start,cfg.get("quota_period","monthly"))
                raise
            hosting_quota.record(pid,time.monotonic()-start,cfg.get("quota_period","monthly"))
            return result
        except Exception as exc: failures.append(f"provider {pid}: {type(exc).__name__}: {str(exc)[:180]}")
    raise RuntimeError("All configured Trading AI routes failed or reached their configured quota. "+" | ".join(failures))
