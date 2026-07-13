-- Align promoted Flyway schema with the EDI 835 parser database contract.
-- This migration is intentionally non-destructive for production databases.

ALTER TABLE bot.payments_835
    ADD COLUMN IF NOT EXISTS raw_json_transaction JSONB,
    ADD COLUMN IF NOT EXISTS file_processing_details JSONB DEFAULT NULL;

ALTER TABLE bot.raw_835_files
    ADD COLUMN IF NOT EXISTS metadata JSONB;

UPDATE bot.payments_835
SET raw_json_transaction = json_transaction
WHERE raw_json_transaction IS NULL;

ALTER TABLE bot.payments_835
    ALTER COLUMN raw_json_transaction SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_payments_835_file_name
    ON bot.payments_835(file_name);

CREATE INDEX IF NOT EXISTS idx_payments_835_payment_date
    ON bot.payments_835(payment_date);

CREATE INDEX IF NOT EXISTS idx_payments_835_payer_id
    ON bot.payments_835(payer_id);

CREATE INDEX IF NOT EXISTS idx_payments_835_check_number
    ON bot.payments_835(check_number);

CREATE INDEX IF NOT EXISTS idx_claims_patient_control_number
    ON bot.claims(patient_control_number);

CREATE INDEX IF NOT EXISTS idx_claims_claim_icn_number
    ON bot.claims(claim_icn_number);

CREATE INDEX IF NOT EXISTS idx_service_lines_hcpcs_code
    ON bot.service_lines(hcpcs_code);

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'bot')
        AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'botuser') THEN
        GRANT USAGE ON SCHEMA bot TO botuser;
        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA bot TO botuser;
        GRANT USAGE ON ALL SEQUENCES IN SCHEMA bot TO botuser;
        GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA bot TO botuser;

        ALTER DEFAULT PRIVILEGES FOR ROLE bot IN SCHEMA bot
            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO botuser;
        ALTER DEFAULT PRIVILEGES FOR ROLE bot IN SCHEMA bot
            GRANT USAGE ON SEQUENCES TO botuser;
        ALTER DEFAULT PRIVILEGES FOR ROLE bot IN SCHEMA bot
            GRANT EXECUTE ON FUNCTIONS TO botuser;
    END IF;
END $$;
