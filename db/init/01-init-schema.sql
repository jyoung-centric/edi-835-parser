-- Initialize bot schema for EDI 835 parser test database
-- Based on V1.0.2__create edi bot tables.sql

-- Create bot schema
CREATE SCHEMA IF NOT EXISTS bot;

-- Set search path
ALTER DATABASE bot_automation SET search_path TO bot, public;

-- Grant privileges to bot user
GRANT ALL PRIVILEGES ON SCHEMA bot TO bot;
GRANT ALL PRIVILEGES ON DATABASE bot_automation TO bot;

-- Switch to bot schema for table creation
SET search_path TO bot, public;

-- Drop existing tables in dependency order
DROP TABLE IF EXISTS bot.cas_adjustments CASCADE;
DROP TABLE IF EXISTS bot.nm1_entities CASCADE;
DROP TABLE IF EXISTS bot.payees CASCADE;
DROP TABLE IF EXISTS bot.payers CASCADE;
DROP TABLE IF EXISTS bot.plb_adjustments CASCADE;
DROP TABLE IF EXISTS bot.service_lines CASCADE;
DROP TABLE IF EXISTS bot.claims CASCADE;
DROP TABLE IF EXISTS bot.edi_transactions CASCADE;
DROP TABLE IF EXISTS bot.raw_835_files CASCADE;
DROP TABLE IF EXISTS bot.payments_835 CASCADE;

-- Simple storage table (complete JSON data)
CREATE TABLE bot.payments_835 (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    file_id UUID NOT NULL UNIQUE,
    file_name TEXT,
    receive_date_time TIMESTAMP,
    check_number TEXT,
    payment_date DATE,
    payment_amount NUMERIC(18,2),
    payer_id TEXT,
    payee_id TEXT,
    json_transaction JSONB NOT NULL,
    file_processing_details JSONB DEFAULT NULL
);

-- Raw file metadata
CREATE TABLE bot.raw_835_files (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    file_id UUID NOT NULL REFERENCES bot.payments_835(file_id) ON DELETE CASCADE UNIQUE,
    receive_date_time TIMESTAMP DEFAULT now(),
    archive_s3_key TEXT,
    raw_json_transaction JSONB,
    raw_edi TEXT
);

-- Normalized tables for structured queries
CREATE TABLE bot.edi_transactions (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    raw_file_id INT REFERENCES bot.raw_835_files(id) ON DELETE CASCADE,
    trace_number TEXT,
    payment_method TEXT,
    payment_amount NUMERIC(18,2),
    payment_date DATE,
    payer_id TEXT,
    payee_id TEXT,
    check_amount NUMERIC(18,2),
    check_date DATE,
    json_tr JSONB NOT NULL
);

CREATE TABLE bot.payers (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES bot.edi_transactions(id) ON DELETE CASCADE,
    payer_name TEXT,
    payer_id_qualifier TEXT,
    payer_id TEXT,
    json_payer JSONB NOT NULL
);

CREATE TABLE bot.payees (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES bot.edi_transactions(id) ON DELETE CASCADE,
    payee_name TEXT,
    payee_id_qualifier TEXT,
    payee_id TEXT,
    json_payee JSONB NOT NULL
);

CREATE TABLE bot.claims (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES bot.edi_transactions(id) ON DELETE CASCADE,
    claim_account_number TEXT,
    patient_control_number TEXT,
    claim_status_code TEXT,
    total_claim_charge_amount NUMERIC(18,2),
    claim_net_amount NUMERIC(18,2),
    patient_responsibility_amount NUMERIC(18,2),
    claim_icn_number TEXT,
    facility_type_code TEXT,
    claim_frequency_code TEXT,
    json_clm JSONB NOT NULL,
    post_date_time TIMESTAMP
);

CREATE TABLE bot.service_lines (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    claim_id INT NOT NULL REFERENCES bot.claims(id) ON DELETE CASCADE,
    hcpcs_code TEXT,
    modifier1 TEXT,
    modifier2 TEXT,
    modifier3 TEXT,
    modifier4 TEXT,
    line_item_charge_amount NUMERIC(18,2),
    service_line_payment_amount NUMERIC(18,2),
    revenue_code TEXT,
    units_of_service_paid_count DECIMAL(15,6),
    units_of_service_submitted_count DECIMAL(15,6),
    json_svc JSONB NOT NULL,
    post_date_time TIMESTAMP
);

CREATE TABLE bot.nm1_entities (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    claim_id INT REFERENCES bot.claims(id) ON DELETE CASCADE,
    service_line_id INT REFERENCES bot.service_lines(id) ON DELETE CASCADE,
    entity_type TEXT,
    last_name TEXT,
    first_name TEXT,
    middle_name TEXT,
    id_qualifier TEXT,
    entity_id TEXT,
    json_nm1 JSONB NOT NULL
);

CREATE TABLE bot.cas_adjustments (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    claim_id INT REFERENCES bot.claims(id) ON DELETE CASCADE,
    service_line_id INT REFERENCES bot.service_lines(id) ON DELETE CASCADE,
    group_code TEXT,
    reason_code TEXT,
    amount NUMERIC(18,2),
    quantity DECIMAL(15,6),
    json_cas JSONB NOT NULL
);

CREATE TABLE bot.plb_adjustments (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES bot.edi_transactions(id) ON DELETE CASCADE,
    provider_id TEXT,
    fiscal_period_date DATE,
    reason_code TEXT,
    reference_id TEXT,
    amount NUMERIC(18,2),
    json_plb JSONB NOT NULL
);

-- Add constraints
ALTER TABLE bot.edi_transactions ADD CONSTRAINT unique_trace_per_file
    UNIQUE (raw_file_id, trace_number);
ALTER TABLE bot.raw_835_files ADD CONSTRAINT unique_file_id_per_raw
    UNIQUE (file_id);

-- Create indexes for common queries
CREATE INDEX idx_payments_835_file_name ON bot.payments_835(file_name);
CREATE INDEX idx_payments_835_payment_date ON bot.payments_835(payment_date);
CREATE INDEX idx_payments_835_payer_id ON bot.payments_835(payer_id);
CREATE INDEX idx_payments_835_check_number ON bot.payments_835(check_number);
CREATE INDEX idx_claims_patient_control_number ON bot.claims(patient_control_number);
CREATE INDEX idx_claims_claim_icn_number ON bot.claims(claim_icn_number);
CREATE INDEX idx_service_lines_hcpcs_code ON bot.service_lines(hcpcs_code);

-- Grant privileges on all tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA bot TO bot;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA bot TO bot;
