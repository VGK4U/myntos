import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.core.database import engine
from app.models.base import Base
import app.models  # This imports all models and registers them with Base

print("Creating tables if they don't exist...")
Base.metadata.create_all(bind=engine)
print("Done!")
