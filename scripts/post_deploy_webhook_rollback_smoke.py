#!/usr/bin/env python3
from __future__ import annotations
import hashlib,hmac,json,os,secrets,sys,time,uuid
import httpx,psycopg

def need(n):
    v=os.getenv(n,"").strip()
    if not v: raise RuntimeError(f"Missing {n}")
    return v
def dsn(u): return u.replace("postgresql+psycopg://","postgresql://",1)
def sign(payload,secret):
    ts=int(time.time())
    dig=hmac.new(secret.encode(),f"{ts}.".encode()+payload,hashlib.sha256).hexdigest()
    return f"t={ts},v1={dig}"
def event_count(c,eid):
    with c.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM subscription_events WHERE stripe_event_id=%s",(eid,))
        return int(cur.fetchone()[0])
def state(c,uid):
    with c.cursor() as cur:
        cur.execute("""SELECT subscription_status,stripe_subscription_id,last_stripe_event_id,
                      last_stripe_event_type,last_stripe_event_created FROM users WHERE id=%s""",(uid,))
        return cur.fetchone()
def send(client,whsec,inj,point,event):
    payload=json.dumps(event,separators=(",",":")).encode()
    return client.post("api/billing/webhook",content=payload,headers={
        "Content-Type":"application/json",
        "Stripe-Signature":sign(payload,whsec),
        "X-Webhook-Failure-Injection":f"{inj}:{point}",
    })
def main():
    base=need("SMOKE_BASE_URL").rstrip("/")+"/"
    dburl=need("DATABASE_URL"); whsec=need("STRIPE_WEBHOOK_SECRET")
    price=need("STRIPE_PRICE_ID"); inj=need("WEBHOOK_FAILURE_INJECTION_SECRET")
    if not base.startswith("https://"): raise RuntimeError("SMOKE_BASE_URL must use HTTPS")
    email=f"rollback-smoke-{uuid.uuid4().hex}@{os.getenv('SMOKE_TEST_EMAIL_DOMAIN','example.invalid')}"
    password=secrets.token_urlsafe(24)+"Aa1!"
    with httpx.Client(base_url=base,timeout=15,follow_redirects=False) as client, psycopg.connect(dsn(dburl),autocommit=True) as conn:
        r=client.post("api/auth/register",json={"email":email,"password":password})
        if r.status_code not in (200,201): raise RuntimeError(f"register HTTP {r.status_code}")
        r=client.post("api/auth/login",json={"email":email,"password":password})
        if r.status_code!=200: raise RuntimeError(f"login HTTP {r.status_code}")
        uid=str(client.get("api/auth/me").json().get("id") or "")
        baseline=state(conn,uid)
        cust="cus_smoke_"+uuid.uuid4().hex[:14]; sub="sub_smoke_"+uuid.uuid4().hex[:14]
        for i,point in enumerate(("after_state_update","after_event_add","before_commit"),1):
            eid=f"evt_rollback_{point}_{uuid.uuid4().hex}"
            ev={"id":eid,"object":"event","created":int(time.time())+i,"type":"customer.subscription.updated",
                "data":{"object":{"id":sub,"object":"subscription","customer":cust,"status":"active",
                "metadata":{"user_id":uid,"smoke_test":"true"},"items":{"data":[{"price":{"id":price}}]}}}}
            r=send(client,whsec,inj,point,ev)
            if r.status_code<500: raise RuntimeError(f"{point}: expected 5xx, got {r.status_code}")
            if event_count(conn,eid)!=0: raise RuntimeError(f"{point}: partial event ledger row survived")
            if state(conn,uid)!=baseline: raise RuntimeError(f"{point}: partial subscription/entitlement state survived")
        # control event proves clean recovery
        eid="evt_rollback_control_"+uuid.uuid4().hex
        ev={"id":eid,"object":"event","created":int(time.time())+100,"type":"customer.subscription.updated",
            "data":{"object":{"id":sub,"object":"subscription","customer":cust,"status":"active",
            "metadata":{"user_id":uid,"smoke_test":"true"},"items":{"data":[{"price":{"id":price}}]}}}}
        payload=json.dumps(ev,separators=(",",":")).encode()
        r=client.post("api/billing/webhook",content=payload,headers={"Content-Type":"application/json","Stripe-Signature":sign(payload,whsec)})
        if r.status_code not in (200,204): raise RuntimeError("control event failed")
        if event_count(conn,eid)!=1: raise RuntimeError("control event ledger write failed")
        if state(conn,uid)[0] not in ("active","trialing"): raise RuntimeError("control entitlement failed")
    print("WEBHOOK TRANSACTION ROLLBACK SMOKE TESTS PASSED")
    return 0
if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as e:
        print(f"WEBHOOK ROLLBACK SMOKE FAILED: {e}",file=sys.stderr); raise SystemExit(1)
