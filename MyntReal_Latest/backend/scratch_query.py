import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv('../.env')
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    res = conn.execute(text("SELECT id, title FROM vgk_gallery WHERE status = 'active' AND deleted_at IS NULL")).fetchall()
    print("Total Active Galleries:", len(res))
    for r in res:
        files = conn.execute(text("SELECT count(*) FROM vgk_gallery_files WHERE gallery_id = :gid"), {"gid": r[0]}).scalar()
        print(f" - Gallery '{r[1]}': {files} images")
