-- [DC-PHONE-OTP-001] Phone OTP Verifications table for pre-registration phone verification
-- Applied: 2026-04-26
-- Purpose: Stores OTP codes and verified tokens for new member registration flows

CREATE TABLE IF NOT EXISTS phone_otp_verifications (
    id SERIAL PRIMARY KEY,
    phone VARCHAR(20) NOT NULL,
    purpose VARCHAR(50) NOT NULL,
    otp_code VARCHAR(10) NOT NULL,
    expires_at TIMESTAMP NOT NULL,
    verified BOOLEAN NOT NULL DEFAULT FALSE,
    verified_at TIMESTAMP,
    phone_verified_token VARCHAR(100),
    token_expires_at TIMESTAMP,
    token_used BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pov_phone_purpose ON phone_otp_verifications(phone, purpose);
CREATE INDEX IF NOT EXISTS idx_pov_token ON phone_otp_verifications(phone_verified_token) WHERE phone_verified_token IS NOT NULL;
