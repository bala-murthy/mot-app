"""Generate sample data and upload it via CSV to seed the database."""
import csv, io, random, sys
from datetime import date, timedelta

sys.path.insert(0, '.')
from app.database import SessionLocal, Base, engine
from app.models import ParameterData, RGSData, SkillConsolidatedLookup
from app import models  # noqa

Base.metadata.create_all(bind=engine)

STATUSES   = ['Open','Pending','Under Evaluation','Recommended','Approved','Fulfilled','Closed Won','On Hold']
CUSTOMERS  = ['Acme Corp','TechGlobal','BankFirst','HealthSys','RetailMax','EduLearn','ManuCo','FinServ']
ACCOUNTS   = ['Digital Transformation','Core Banking','ERP Implementation','Cloud Migration','Data Analytics','CRM Rollout']
IOUS       = ['BFS','CPG','HLS','TMT','ENE','MFG']
PRACTICES  = ['Java Full Stack','SAP','Salesforce','Microsoft','Data Engineering','AI/ML','Cloud Infra','BPS','Oracle']
SKILLS     = ['Java','Python','SAP ABAP','Salesforce Admin','Azure','AWS','Tableau','PowerBI','React','Angular','Node.js','PL/SQL']
COUNTRIES  = ['India','USA','UK','Australia','Singapore','Germany']
MANAGERS   = ['Rajesh Kumar','Priya Sharma','Anand Mehta','Deepa Nair','Suresh Babu','Lakshmi Iyer']
CHANNELS   = ['Internal','RPO','Vendor','Direct','Referral']
DOMAINS    = ['Banking','Insurance','Healthcare','Retail','Manufacturing','Education','Energy']
RMG_NAMES  = ['Venkat R','Kavitha M','Arjun S','Meena P','Ravi T']
EVAL_NAMES = ['Suresh P','Anjali K','Mohan D','Preethi L','Kumar N']
PENDING    = ['RMG','Delivery Manager','Customer','Evaluator','HR']

random.seed(42)

def rand_date(start_days_ago: int, end_days_ago: int = 0) -> date:
    d = random.randint(end_days_ago, start_days_ago)
    return date.today() - timedelta(days=d)

def make_req_id(i: int) -> str:
    return f"REQ{str(i).zfill(4)}"

N = 80

# ── Seed reference tables directly ──────────────────────────────────────────
db = SessionLocal()

# RGS data
db.query(RGSData).delete()
for i in range(1, N + 1):
    req_id = make_req_id(i)
    start = rand_date(400, 10)
    db.add(RGSData(
        requirement_id=req_id,
        won_sp=f"SP{random.randint(100,999)}",
        requirement_pending_with=random.choice(PENDING),
        gbams_rmg_name=random.choice(RMG_NAMES),
        evaluator_emp_name=random.choice(EVAL_NAMES),
        requirement_start_date=start,
    ))

# Skill lookup
db.query(SkillConsolidatedLookup).delete()
for s in SKILLS:
    db.add(SkillConsolidatedLookup(
        input_skill=s,
        consolidated_skill=s,
        second_consolidated_skill=random.choice(SKILLS),
        verify_skill_flag='N',
    ))

# Parameters
db.query(ParameterData).delete()
param_map = {
    'Open': 'Open Requirement',
    'Pending': 'Open Requirement',
    'Recommended': 'Recommended',
    'Under Evaluation': 'Under Evaluation',
    'Approved': 'Approved',
    'Fulfilled': 'Fulfilled',
    'Closed Won': 'Fulfilled',
    'On Hold': 'Open Requirement',
}
for status, perspective in param_map.items():
    db.add(ParameterData(fulfillment_status=status, fulfillment_perspective=perspective))

db.commit()

# ── Build CSV for main requirements ─────────────────────────────────────────
headers = [
    'Fulfillment Status','Group Customer Name','Account Name','Domain','IOU','Sub IOU',
    'Country','Branch','Primary Competency Proficiency Details','Competency',
    'Experience Range','Revenue Impact','Onsite/Offshore','Delivery Manager',
    'Requirement ID','Skill','Added Date','Service Practice',
    'Target Fulfillment Date','Revenue At Risk','Revenue Won',
    'Requirement Start Date','Candidate Name','Fulfillment Channel',
    'Evaluation Status','Candidate Evaluation Stage','Sub Practice',
    'GBAMS Requirement ID','SLA Breach Days',
]

buf = io.StringIO()
writer = csv.writer(buf)
writer.writerow(headers)

for i in range(1, N + 1):
    req_id = make_req_id(i)
    status = random.choice(STATUSES)
    start  = rand_date(400, 10)
    added  = start - timedelta(days=random.randint(1,30))
    target = start + timedelta(days=random.randint(30,120))
    rev    = round(random.uniform(50_000, 500_000), 2)
    risk   = round(rev * random.uniform(0.1, 0.6), 2) if status not in ('Fulfilled','Closed Won') else 0
    won    = rev if status in ('Fulfilled','Closed Won') else 0
    skill  = random.choice(SKILLS)
    iou    = random.choice(IOUS)
    country = random.choice(COUNTRIES)

    writer.writerow([
        status,
        random.choice(CUSTOMERS),
        random.choice(ACCOUNTS),
        random.choice(DOMAINS),
        iou, f"{iou}-Sub{random.randint(1,3)}",
        country, f"{country}-Branch{random.randint(1,3)}",
        f"{skill} Expert",
        skill,
        f"{random.randint(3,15)} years",
        rev,
        random.choice(['Onsite','Offshore','Hybrid']),
        random.choice(MANAGERS),
        req_id, skill,
        added.isoformat(),
        random.choice(PRACTICES),
        target.isoformat(),
        risk, won,
        start.isoformat(),
        f"Candidate_{random.randint(100,999)}" if status in ('Under Evaluation','Approved','Fulfilled') else '',
        random.choice(CHANNELS),
        'Submitted' if status in ('Under Evaluation','Approved') else '',
        'L1 Cleared' if status == 'Approved' else '',
        f"{iou}-Sub Practice",
        f"GBAMS{req_id}",
        random.randint(0, 90) if status not in ('Fulfilled','Closed Won') else 0,
    ])

csv_bytes = buf.getvalue().encode()

# Upload via the service
from app.services.upload_service import process_upload
result = process_upload(csv_bytes, 'seed_data.csv', db)
print(f"Seed complete: {result.rows_loaded} loaded, {result.rows_skipped} skipped, {result.rows_failed} failed")
print(f"  Transformation: {result.transformation_summary}")
db.close()
