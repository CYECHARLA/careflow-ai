import os, uuid, hashlib, json, re, mimetypes
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional
from fastapi import FastAPI, Depends, UploadFile, File, HTTPException, Header, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, DateTime, ForeignKey, Text, Boolean, Integer, Float, select, func
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from pydantic import BaseModel, Field
import jwt
from passlib.context import CryptContext

DB_URL=os.getenv('DATABASE_URL','sqlite:///./careflow.db')
engine=create_engine(DB_URL,connect_args={'check_same_thread':False} if DB_URL.startswith('sqlite') else {},pool_pre_ping=True)
SessionLocal=sessionmaker(bind=engine)
class Base(DeclarativeBase):pass
class Stamp:
 id=Column(String,primary_key=True,default=lambda:str(uuid.uuid4()))
 created_at=Column(DateTime,default=lambda:datetime.now(timezone.utc))
 updated_at=Column(DateTime,default=lambda:datetime.now(timezone.utc),onupdate=lambda:datetime.now(timezone.utc))
class User(Stamp,Base):
 __tablename__='users'; username=Column(String,unique=True); password_hash=Column(String); role=Column(String,default='staff')
class Patient(Stamp,Base):
 __tablename__='patients'; name=Column(String); date_of_birth=Column(String)
class Referral(Stamp,Base):
 __tablename__='referrals'; patient_id=Column(String,ForeignKey('patients.id')); requested_service=Column(String); source=Column(String); status=Column(String,default='New'); assigned_to=Column(String,ForeignKey('users.id'),nullable=True); notes=Column(Text,default='')
class Document(Stamp,Base):
 __tablename__='documents'; referral_id=Column(String,ForeignKey('referrals.id'),nullable=True); filename=Column(String); content_type=Column(String); path=Column(String); status=Column(String,default='Uploaded'); document_type=Column(String,default='Other'); extracted_text=Column(Text,default=''); extraction=Column(Text,default='{}'); confidence=Column(Float,default=0); error=Column(Text,default='')
class Task(Stamp,Base):
 __tablename__='tasks'; referral_id=Column(String,ForeignKey('referrals.id')); title=Column(String); status=Column(String,default='Pending'); assigned_to=Column(String,ForeignKey('users.id'),nullable=True); message=Column(Text,default=''); due_at=Column(DateTime,nullable=True)
class Audit(Stamp,Base):
 __tablename__='audit_logs'; actor_id=Column(String,nullable=True); action=Column(String); entity_type=Column(String); entity_id=Column(String); details=Column(Text,default='{}')
class IntegrationLog(Stamp,Base):
 __tablename__='integration_logs'; provider=Column(String); event_id=Column(String,unique=True); status=Column(String); payload=Column(Text); attempts=Column(Integer,default=1)
class Review(Stamp,Base):
 __tablename__='reviews'; document_id=Column(String,ForeignKey('documents.id')); reviewer_id=Column(String,nullable=True); status=Column(String,default='Pending'); notes=Column(Text,default=''); previous=Column(Text,default='{}'); updated=Column(Text,default='{}')

app=FastAPI(title='CareFlow AI API',version='0.1.0')
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:5173,http://localhost:3000').split(','),allow_credentials=True,allow_methods=['*'],allow_headers=['*'])
pwd=CryptContext(schemes=['bcrypt'],deprecated='auto')
SECRET=os.getenv('JWT_SECRET','local-demo-secret-change-before-deployment')
STORE=Path(os.getenv('STORAGE_DIR','./storage'));STORE.mkdir(parents=True,exist_ok=True)
def db():
 with SessionLocal() as s:yield s
def audit(s,actor,action,kind,eid,details=None):s.add(Audit(actor_id=actor,action=action,entity_type=kind,entity_id=eid,details=json.dumps(details or {})))
def current(authorization:Optional[str]=Header(None),s:Session=Depends(db)):
 try:
  token=authorization.split(' ',1)[1];payload=jwt.decode(token,SECRET,algorithms=['HS256']);u=s.get(User,payload['sub']);assert u;return u
 except Exception:raise HTTPException(401,'Authentication required')
def require(*roles):
 def check(u:User=Depends(current)):
  if u.role not in roles:raise HTTPException(403,'Insufficient permissions')
  return u
 return check
def obj(x):return {k:getattr(x,k) for k in x.__table__.columns.keys() if k not in ('password_hash','path')}
def get(s,model,id):
 x=s.get(model,id)
 if not x:raise HTTPException(404,'Not found')
 return x
class Login(BaseModel):username:str;password:str
class ReferralIn(BaseModel):patient_name:str;date_of_birth:Optional[str]=None;requested_service:str='ABA';source:str='Manual';notes:str=''
class PatchReferral(BaseModel):status:Optional[str]=None;notes:Optional[str]=None;assigned_to:Optional[str]=None
class TaskIn(BaseModel):referral_id:str;title:str;message:str=''
class TaskPatch(BaseModel):status:str
class ReviewIn(BaseModel):notes:str='';fields:dict=Field(default_factory=dict)
@app.on_event('startup')
def startup():
 if os.getenv('AUTO_CREATE_TABLES','true').lower()=='true':Base.metadata.create_all(engine)
 with SessionLocal() as s:
  if not s.scalar(select(User).where(User.username=='admin')):
   s.add(User(username='admin',password_hash=pwd.hash(os.getenv('DEMO_PASSWORD','DemoPass123!')),role='admin'));s.commit()
@app.post('/api/v1/auth/login')
def login(data:Login,s:Session=Depends(db)):
 u=s.scalar(select(User).where(User.username==data.username))
 if not u or not pwd.verify(data.password,u.password_hash):raise HTTPException(401,'Invalid credentials')
 return {'access_token':jwt.encode({'sub':u.id,'exp':datetime.now(timezone.utc)+timedelta(hours=8)},SECRET,algorithm='HS256'),'token_type':'bearer'}
@app.get('/api/v1/auth/me')
def me(u:User=Depends(current)):return obj(u)
@app.post('/api/v1/auth/logout')
def logout(u:User=Depends(current)):return {'message':'Client must discard bearer token'}
@app.get('/api/v1/referrals')
def referrals(status:Optional[str]=None,q:Optional[str]=None,limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),s:Session=Depends(db),u:User=Depends(current)):
 rows=s.scalars(select(Referral).order_by(Referral.created_at.desc())).all();out=[]
 for r in rows:
  patient=s.get(Patient,r.patient_id)
  if status and r.status!=status:continue
  if q and q.lower() not in (patient.name+' '+r.requested_service).lower():continue
  out.append({**obj(r),'patient_name':patient.name,'date_of_birth':patient.date_of_birth})
 return {'items':out[offset:offset+limit],'total':len(out)}
@app.post('/api/v1/referrals',status_code=201)
def create_referral(data:ReferralIn,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 patient=Patient(name=data.patient_name,date_of_birth=data.date_of_birth);s.add(patient);s.flush();r=Referral(patient_id=patient.id,requested_service=data.requested_service,source=data.source,notes=data.notes);s.add(r);s.flush();audit(s,u.id,'created','referral',r.id);s.commit();return {**obj(r),'patient_name':patient.name}
@app.get('/api/v1/referrals/{id}')
def referral(id:str,s:Session=Depends(db),u:User=Depends(current)):
 r=get(s,Referral,id);return {**obj(r),'patient_name':s.get(Patient,r.patient_id).name,'documents':[obj(d) for d in s.scalars(select(Document).where(Document.referral_id==id))],'tasks':[obj(t) for t in s.scalars(select(Task).where(Task.referral_id==id))]}
@app.patch('/api/v1/referrals/{id}')
def patch_referral(id:str,data:PatchReferral,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 r=get(s,Referral,id);old=obj(r)
 for k,v in data.model_dump(exclude_unset=True).items():setattr(r,k,v)
 audit(s,u.id,'updated','referral',id,{'previous':old,'changes':data.model_dump(exclude_unset=True)});s.commit();return obj(r)
@app.post('/api/v1/referrals/{id}/assign')
def assign(id:str,assigned_to:str,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):return patch_referral(id,PatchReferral(assigned_to=assigned_to),s,u)
ALLOWED={'application/pdf':'.pdf','image/png':'.png','image/jpeg':'.jpg'}
@app.post('/api/v1/documents/upload',status_code=201)
async def upload(files:list[UploadFile]=File(...),referral_id:Optional[str]=None,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 if referral_id:get(s,Referral,referral_id)
 results=[];max_size=int(os.getenv('MAX_UPLOAD_MB','10'))*1024*1024
 for f in files:
  content=await f.read(max_size+1)
  if len(content)>max_size:raise HTTPException(413,'File too large')
  suffix=Path(f.filename or '').suffix.lower();expected=ALLOWED.get(f.content_type)
  if not expected or suffix not in (('.jpg','.jpeg') if expected=='.jpg' else (expected,)):raise HTTPException(415,'Unsupported file type')
  magic=content.startswith(b'%PDF-') if expected=='.pdf' else content.startswith(b'\x89PNG\r\n\x1a\n') if expected=='.png' else content.startswith(b'\xff\xd8\xff')
  if not magic:raise HTTPException(415,'Invalid file signature')
  d=Document(filename=Path(f.filename).name,content_type=f.content_type,referral_id=referral_id,path='');s.add(d);s.flush();d.path=str(STORE/(d.id+expected));Path(d.path).write_bytes(content);audit(s,u.id,'uploaded','document',d.id);results.append(obj(d))
 s.commit();return {'items':results}
@app.get('/api/v1/documents')
def documents(limit:int=Query(50,ge=1,le=200),offset:int=Query(0,ge=0),s:Session=Depends(db),u:User=Depends(current)):
 q=select(Document).order_by(Document.created_at.desc());return {'items':[obj(x) for x in s.scalars(q.offset(offset).limit(limit))],'total':s.scalar(select(func.count()).select_from(Document))}
@app.get('/api/v1/documents/{id}')
def document(id:str,s:Session=Depends(db),u:User=Depends(current)):return obj(get(s,Document,id))
@app.get('/api/v1/documents/{id}/file')
def document_file(id:str,s:Session=Depends(db),u:User=Depends(current)):
 d=get(s,Document,id);return FileResponse(d.path,media_type=d.content_type,filename=d.filename)
@app.get('/api/v1/documents/{id}/extraction')
def extraction(id:str,s:Session=Depends(db),u:User=Depends(current)):
 d=get(s,Document,id);return {'text':d.extracted_text,'fields':json.loads(d.extraction or '{}'),'confidence':d.confidence}
TYPES=['ABA Referral','Speech Therapy Referral','Plan of Care (POC)','Diagnostic Report','Insurance Authorization','Insurance Denial','Partial Insurance Denial','Medical Records','Other']
def extract_text(d):
 if os.getenv('AI_MODE','demo')=='demo':
  try:
   if d.content_type=='application/pdf':
    import fitz
    with fitz.open(d.path) as pdf:return '\n'.join(p.get_text() for p in pdf)
   import pytesseract
   from PIL import Image
   return pytesseract.image_to_string(Image.open(d.path))
  except Exception:return ''
 if d.content_type=='application/pdf':
  import fitz
  with fitz.open(d.path) as pdf:return '\n'.join(p.get_text() for p in pdf)
 import pytesseract
 from PIL import Image
 return pytesseract.image_to_string(Image.open(d.path))
def classify(text):
 lower=text.lower();kind=next((label for key,label in [('partial denial','Partial Insurance Denial'),('denial','Insurance Denial'),('authorization','Insurance Authorization'),('speech','Speech Therapy Referral'),('plan of care','Plan of Care (POC)'),('diagnostic','Diagnostic Report'),('medical record','Medical Records'),('aba','ABA Referral')] if key in lower),'Other')
 def field(pattern):
  m=re.search(pattern,text,re.I);return m.group(1).strip() if m else None
 name=field(r'(?:patient name|patient)\s*:\s*([^\n]+)');dob=field(r'(?:date of birth|dob)\s*:\s*(\d{4}-\d{2}-\d{2})');provider=field(r'provider\s*:\s*([^\n]+)')
 signature=bool(re.search(r'(?:signed by|signature)\s*:\s*(?!missing|no\b|unsigned)([^\n]+)',text,re.I))
 missing=[key for key,value in [('patient_name',name),('date_of_birth',dob),('provider_name',provider),('signature',signature)] if not value]
 return {'document_type':kind,'patient_name':name,'date_of_birth':dob,'provider_name':provider,'signature_present':signature,'missing_fields':missing,'confidence_score':0.92 if kind!='Other' else 0.45,'requires_human_review':bool(missing) or kind=='Other','recommended_workflow':'human_review' if missing else 'referral_validation'}
def validate_referral(s,r,actor):
 docs=s.scalars(select(Document).where(Document.referral_id==r.id,Document.status.in_(['Processed','Needs Review']))).all();types={d.document_type for d in docs};required=['ABA Referral','Diagnostic Report','Plan of Care (POC)'] if 'ABA' in r.requested_service.upper() else ['Speech Therapy Referral','Diagnostic Report'];missing=[x for x in required if x not in types]
 if docs and not any(json.loads(d.extraction or '{}').get('signature_present') for d in docs):missing.append('Provider signature verification')
 for item in missing:
  title='Missing: '+item
  if not s.scalar(select(Task).where(Task.referral_id==r.id,Task.title==title,Task.status!='Cancelled')):s.add(Task(referral_id=r.id,title=title,message='Please provide or verify '+item+'. Staff approval required before external delivery.',due_at=datetime.now(timezone.utc)+timedelta(days=3)))
 r.status='Documents Missing' if missing else 'Ready for Review';audit(s,actor,'validated','referral',r.id,{'missing':missing});return {'referral_id':r.id,'missing_requirements':missing,'complete':not missing,'status':r.status}
@app.post('/api/v1/documents/{id}/process')
def process(id:str,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 d=get(s,Document,id);d.status='Processing';s.flush()
 try:
  text=extract_text(d);fields=classify(text);d.extracted_text=text;d.extraction=json.dumps(fields);d.document_type=fields['document_type'];d.confidence=fields['confidence_score'];d.status='Needs Review' if fields['requires_human_review'] else 'Processed'
  if d.status=='Needs Review' and not s.scalar(select(Review).where(Review.document_id==id,Review.status=='Pending')):s.add(Review(document_id=id))
  if d.referral_id:validate_referral(s,get(s,Referral,d.referral_id),u.id)
  audit(s,u.id,'processed','document',id,{'status':d.status});s.commit();return obj(d)
 except Exception as e:
  d.status='Failed';d.error=str(e)[:500];audit(s,u.id,'processing_failed','document',id);s.commit();raise HTTPException(422,'Processing failed; see document error')
@app.post('/api/v1/documents/{id}/retry')
def retry(id:str,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):return process(id,s,u)
@app.post('/api/v1/referrals/{id}/validate')
def validate(id:str,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 result=validate_referral(s,get(s,Referral,id),u.id);s.commit();return result
@app.get('/api/v1/referrals/{id}/completeness')
def completeness(id:str,s:Session=Depends(db),u:User=Depends(current)):
 r=get(s,Referral,id);docs=s.scalars(select(Document).where(Document.referral_id==id)).all();required=['ABA Referral','Diagnostic Report','Plan of Care (POC)'] if 'ABA' in r.requested_service.upper() else ['Speech Therapy Referral','Diagnostic Report'];missing=[x for x in required if x not in {d.document_type for d in docs}];return {'required':required,'missing_requirements':missing,'complete':not missing}
@app.get('/api/v1/tasks')
def tasks(s:Session=Depends(db),u:User=Depends(current)):return {'items':[obj(t) for t in s.scalars(select(Task).order_by(Task.created_at.desc()))]}
@app.post('/api/v1/tasks',status_code=201)
def create_task(data:TaskIn,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 get(s,Referral,data.referral_id);t=Task(**data.model_dump());s.add(t);s.flush();audit(s,u.id,'created','task',t.id);s.commit();return obj(t)
@app.patch('/api/v1/tasks/{id}')
def patch_task(id:str,data:TaskPatch,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 t=get(s,Task,id)
 if data.status not in ['Pending','In Progress','Waiting','Completed','Cancelled']:raise HTTPException(422,'Invalid status')
 t.status=data.status;audit(s,u.id,'updated','task',id,{'status':data.status});s.commit();return obj(t)
@app.get('/api/v1/reviews')
def reviews(s:Session=Depends(db),u:User=Depends(current)):return {'items':[dict(**obj(r),filename=s.get(Document,r.document_id).filename) for r in s.scalars(select(Review).order_by(Review.created_at.desc()))]}
def review_action(id,data,s,u,decision):
 r=get(s,Review,id);d=get(s,Document,r.document_id);old=json.loads(d.extraction or '{}');r.previous=json.dumps(old);r.updated=json.dumps(data.fields);r.notes=data.notes;r.reviewer_id=u.id;r.status=decision
 if decision=='Approved':d.extraction=json.dumps({**old,**data.fields});d.status='Processed'
 else:d.status='Needs Review'
 audit(s,u.id,'review_'+decision.lower(),'document',d.id,{'previous':old,'updated':data.fields,'reason':data.notes});s.commit();return obj(r)
@app.post('/api/v1/reviews/{id}/approve')
def approve(id:str,data:ReviewIn,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):return review_action(id,data,s,u,'Approved')
@app.post('/api/v1/reviews/{id}/reject')
def reject(id:str,data:ReviewIn,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):return review_action(id,data,s,u,'Rejected')
@app.get('/api/v1/dashboard/overview')
def overview(s:Session=Depends(db),u:User=Depends(current)):
 referrals=s.scalars(select(Referral)).all();docs=s.scalars(select(Document)).all();tasks=s.scalars(select(Task)).all();return {'total_referrals':len(referrals),'new_referrals':sum(r.status=='New' for r in referrals),'awaiting_documents':sum(r.status=='Documents Missing' for r in referrals),'pending_signatures':sum('signature' in t.title.lower() and t.status!='Completed' for t in tasks),'documents_processed':sum(d.status=='Processed' for d in docs),'needs_review':sum(d.status=='Needs Review' for d in docs),'failed_jobs':sum(d.status=='Failed' for d in docs),'pending_tasks':sum(t.status=='Pending' for t in tasks),'referral_statuses':[{'name':status,'value':sum(r.status==status for r in referrals)} for status in ['New','Under Review','Documents Missing','Pending Signature','Ready for Review','Completed','On Hold']],'document_types':[{'name':kind,'value':sum(d.document_type==kind for d in docs)} for kind in TYPES]}
@app.get('/api/v1/dashboard/activity')
def activity(s:Session=Depends(db),u:User=Depends(current)):return {'items':[obj(x) for x in s.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(30))]}
@app.get('/api/v1/audit-logs')
def audits(s:Session=Depends(db),u:User=Depends(require('admin','staff'))):return {'items':[obj(x) for x in s.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200))]}
@app.get('/api/v1/integrations')
def integrations(u:User=Depends(current)):return {'items':[{'id':'mock-crm','name':'Lumary-style CRM','mode':'mock'},{'id':'mock-tasks','name':'Monday-style Tasks','mode':'mock'},{'id':'mock-email','name':'Email Service','mode':'mock'}]}
@app.post('/api/v1/integrations/{id}/sync')
def sync(id:str,event_id:Optional[str]=None,s:Session=Depends(db),u:User=Depends(require('admin','staff'))):
 if id not in ['mock-crm','mock-tasks','mock-email']:raise HTTPException(404,'Unknown integration')
 event_id=event_id or str(uuid.uuid4());old=s.scalar(select(IntegrationLog).where(IntegrationLog.event_id==event_id))
 if old:return {'id':old.id,'status':old.status,'duplicate':True}
 log=IntegrationLog(provider=id,event_id=event_id,status='Success',payload='{}');s.add(log);s.flush();audit(s,u.id,'synced','integration',log.id);s.commit();return {'id':log.id,'status':log.status,'duplicate':False}
@app.get('/api/v1/integrations/logs')
def integration_logs(s:Session=Depends(db),u:User=Depends(current)):return {'items':[obj(x) for x in s.scalars(select(IntegrationLog).order_by(IntegrationLog.created_at.desc()))]}
@app.get('/health')
def health():return {'status':'ok'}
