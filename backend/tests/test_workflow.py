from fastapi.testclient import TestClient
from app.main import app, Base, engine

def test_login_and_referral():
 with TestClient(app) as c:
  token=c.post('/api/v1/auth/login',json={'username':'admin','password':'DemoPass123!'}).json()['access_token']
  h={'Authorization':'Bearer '+token}
  r=c.post('/api/v1/referrals',json={'patient_name':'Synthetic Test','requested_service':'ABA'},headers=h)
  assert r.status_code==201
  id=r.json()['id']
  v=c.post(f'/api/v1/referrals/{id}/validate',headers=h)
  assert v.status_code==200 and 'ABA Referral' in v.json()['missing_requirements']
  assert c.get('/api/v1/tasks',headers=h).json()['items']
  assert c.get('/api/v1/dashboard/overview',headers=h).json()['total_referrals']>=1
  assert c.get('/api/v1/audit-logs',headers=h).status_code==200

def test_unauthorized():
 with TestClient(app) as c:assert c.get('/api/v1/referrals').status_code==401
