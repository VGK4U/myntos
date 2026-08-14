import os
import sys

# Add backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'backend')))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.crm import CRMLead
from app.models.user import User

def fix_lead_uplines():
    db: Session = SessionLocal()
    try:
        # Find leads that have mnr_handler_id but might be missing uplines
        leads = db.query(CRMLead).filter(CRMLead.mnr_handler_id.isnot(None)).all()
        updated_count = 0
        
        for lead in leads:
            changed = False
            try:
                _muser = db.query(User).filter(User.id == lead.mnr_handler_id).first()
                if _muser and _muser.referrer_id:
                    _guru = db.query(User).filter(User.id == _muser.referrer_id).first()
                    if _guru:
                        if not lead.guru_id:
                            lead.guru_id = _guru.id
                            changed = True
                        if _guru.referrer_id:
                            _zguru = db.query(User).filter(User.id == _guru.referrer_id).first()
                            if _zguru:
                                if not lead.z_guru_id:
                                    lead.z_guru_id = _zguru.id
                                    changed = True
                                if _zguru.referrer_id:
                                    _adiguru = db.query(User).filter(User.id == _zguru.referrer_id).first()
                                    if _adiguru:
                                        if not lead.adi_guru_id:
                                            lead.adi_guru_id = _adiguru.id
                                            changed = True
            except Exception as e:
                print(f"Error processing lead {lead.id}: {e}")
            
            if changed:
                updated_count += 1
                
        db.commit()
        print(f"Successfully fixed uplines for {updated_count} leads.")
    finally:
        db.close()

if __name__ == "__main__":
    fix_lead_uplines()
