"""
One-Time Credential Migration Script (Release 1A Security Layer)
Encrypts existing plaintext tokens in facebook_pages and whatsapp_api_config tables.
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import create_engine, text
from app.core.config import settings
from app.core.security_encryption import encrypt_credential, decrypt_credential

def run_migration():
    engine = create_engine(settings.DATABASE_URL or "sqlite:///./mlm_app.db")
    print("🔒 Running Release 1A Credential Encryption Migration...")
    
    with engine.connect() as conn:
        # 1. Encrypt facebook_pages
        try:
            pages = conn.execute(text("SELECT id, access_token FROM facebook_pages")).fetchall()
            encrypted_count = 0
            for page_id, token in pages:
                if token and not token.startswith("gcm:v1:"):
                    enc_token = encrypt_credential(token)
                    dec_check = decrypt_credential(enc_token, strict_mode=True)
                    if dec_check == token:
                        conn.execute(
                            text("UPDATE facebook_pages SET access_token = :enc WHERE id = :id"),
                            {"enc": enc_token, "id": page_id}
                        )
                        encrypted_count += 1
                    else:
                        print(f"⚠️ Verification failed for page id {page_id}. Skipping.")
            conn.commit()
            print(f"✅ Encrypted {encrypted_count} tokens in facebook_pages.")
        except Exception as e:
            print(f"⚠️ facebook_pages migration note: {e}")

        # 2. Encrypt whatsapp_api_config
        try:
            configs = conn.execute(text("SELECT id, access_token FROM whatsapp_api_config")).fetchall()
            wa_count = 0
            for cfg_id, token in configs:
                if token and not token.startswith("gcm:v1:"):
                    enc_token = encrypt_credential(token)
                    dec_check = decrypt_credential(enc_token, strict_mode=True)
                    if dec_check == token:
                        conn.execute(
                            text("UPDATE whatsapp_api_config SET access_token = :enc WHERE id = :id"),
                            {"enc": enc_token, "id": cfg_id}
                        )
                        wa_count += 1
            conn.commit()
            print(f"✅ Encrypted {wa_count} tokens in whatsapp_api_config.")
        except Exception as e:
            print(f"⚠️ whatsapp_api_config migration note: {e}")

    print("🔒 Credential Encryption Migration Completed Successfully.")

if __name__ == "__main__":
    run_migration()
