"""Persistent runtime accounting and budget forecasting for VALE inference hosts.
The counter measures time spent inside VALE inference calls, not provider idle time or billed GPU time.
Configured limits are operator estimates unless a provider's own quota API is explicitly available.
"""
from __future__ import annotations
from datetime import datetime, timezone, timedelta
from sqlalchemy import text
from search_engine.ai_hosting_registry import engine

_initialized = False

def init():
    global _initialized
    if _initialized: return
    e=engine()
    try:
        with e.begin() as c:
            c.execute(text('''CREATE TABLE IF NOT EXISTS vale_hosting_usage (
              provider_id INTEGER NOT NULL, period_key VARCHAR(40) NOT NULL,
              seconds_used REAL NOT NULL DEFAULT 0, updated_at VARCHAR(40) NOT NULL,
              PRIMARY KEY(provider_id,period_key))'''))
            c.execute(text('''CREATE TABLE IF NOT EXISTS vale_hosting_usage_events (
              id INTEGER PRIMARY KEY, provider_id INTEGER NOT NULL, seconds REAL NOT NULL,
              recorded_at VARCHAR(40) NOT NULL)'''))
            if e.dialect.name=='postgresql':
                c.execute(text('CREATE SEQUENCE IF NOT EXISTS vale_hosting_usage_events_id_seq'))
                c.execute(text("ALTER TABLE vale_hosting_usage_events ALTER COLUMN id SET DEFAULT nextval('vale_hosting_usage_events_id_seq')"))
                c.execute(text("SELECT setval('vale_hosting_usage_events_id_seq', GREATEST(COALESCE((SELECT MAX(id) FROM vale_hosting_usage_events),0)+1,1), false)"))
        _initialized = True
    finally:e.dispose()


def period_key(period='monthly', now=None):
    now=now or datetime.now(timezone.utc)
    if period=='hourly': return now.strftime('%Y-%m-%dT%H')
    if period=='daily': return now.strftime('%Y-%m-%d')
    if period=='weekly': return f"{now.isocalendar().year}-W{now.isocalendar().week:02d}"
    return now.strftime('%Y-%m')


def record(provider_id, seconds, period='monthly'):
    init(); e=engine(); value=max(0,float(seconds)); now=datetime.now(timezone.utc); stamp=now.isoformat()
    try:
        with e.begin() as c:
            c.execute(text('''INSERT INTO vale_hosting_usage(provider_id,period_key,seconds_used,updated_at)
              VALUES(:p,:k,:s,:t) ON CONFLICT(provider_id,period_key) DO UPDATE SET
              seconds_used=vale_hosting_usage.seconds_used+excluded.seconds_used,updated_at=excluded.updated_at'''),
              {'p':int(provider_id),'k':period_key(period,now),'s':value,'t':stamp})
            c.execute(text('INSERT INTO vale_hosting_usage_events(provider_id,seconds,recorded_at) VALUES(:p,:s,:t)'),
                      {'p':int(provider_id),'s':value,'t':stamp})
    finally:e.dispose()


def used(provider_id, period='monthly'):
    init(); key=period_key(period); e=engine()
    try:
        with e.connect() as c:
            value=c.execute(text('SELECT seconds_used FROM vale_hosting_usage WHERE provider_id=:p AND period_key=:k'), {'p':int(provider_id),'k':key}).scalar()
        return float(value or 0)
    finally:e.dispose()


def forecast_monthly(provider_id):
    init(); e=engine(); now=datetime.now(timezone.utc); cutoff=(now-timedelta(days=7)).isoformat()
    try:
        with e.connect() as c:
            row=c.execute(text('''SELECT COALESCE(SUM(seconds),0),MIN(recorded_at),COUNT(*) FROM vale_hosting_usage_events
              WHERE provider_id=:p AND recorded_at>=:cutoff'''),{'p':int(provider_id),'cutoff':cutoff}).first()
        total=float(row[0] or 0); first=row[1]; count=int(row[2] or 0)
        if not count: return {'estimated_monthly_runtime_seconds':0,'forecast_sample_days':0,'forecast_confidence':'no_usage_yet'}
        try: first_dt=datetime.fromisoformat(first)
        except Exception: first_dt=now-timedelta(days=1)
        days=max(1,min(7,(now-first_dt).total_seconds()/86400))
        return {'estimated_monthly_runtime_seconds':round(total/days*30,2),
                'forecast_sample_days':round(days,2),'forecast_confidence':'early_estimate' if days<3 else 'rolling_7_day_estimate'}
    finally:e.dispose()


def status(provider_id, config):
    period=config.get('quota_period','monthly')
    limit=config.get('quota_limit_seconds')
    used_seconds=used(provider_id,period)
    limit=float(limit) if limit not in (None,'') else None
    threshold=float(config.get('quota_switch_at_percent',90) or 90)
    used_percent=None if not limit else min(100,round(100*used_seconds/limit,2))
    multipliers={'hourly':24*30,'daily':30,'weekly':30/7,'monthly':1}
    monthly_limit=None if limit is None else limit*multipliers.get(period,1)
    forecast=forecast_monthly(provider_id)
    forecast['monthly_equivalent_limit_seconds']=None if monthly_limit is None else round(monthly_limit,2)
    forecast['monthly_budget_status']='unconfigured' if monthly_limit is None else ('within_estimate' if forecast['estimated_monthly_runtime_seconds']<=monthly_limit else 'over_estimate')
    return {'period':period,'limit_seconds':limit,'used_seconds':round(used_seconds,2),
            'remaining_seconds':None if limit is None else max(0,round(limit-used_seconds,2)),
            'used_percent':used_percent,'switch_at_percent':threshold,
            'switch_recommended':bool(limit is not None and used_percent is not None and used_percent>=threshold),
            'source':'operator_estimate' if limit is not None else 'unconfigured',
            'exhausted':bool(limit is not None and used_seconds>=limit),**forecast}
