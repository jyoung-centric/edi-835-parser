DROP TABLE IF EXISTS bot.cas_adjustments;
DROP TABLE IF EXISTS bot.nm1_entities;
DROP TABLE IF EXISTS bot.payees;
DROP TABLE IF EXISTS bot.payers;
DROP TABLE IF EXISTS bot.plb_adjustments;
DROP TABLE IF EXISTS bot.service_lines;
DROP TABLE IF EXISTS bot.claims;
DROP TABLE IF EXISTS bot.edi_transactions;
DROP TABLE IF EXISTS bot.raw_835_files;
DROP TABLE IF EXISTS bot.payments_835;

CREATE TABLE payments_835 (
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
    raw_edi TEXT
);

CREATE TABLE raw_835_files (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    file_id UUID NOT NULL REFERENCES payments_835(file_id) ON DELETE CASCADE UNIQUE,
    receive_date_time TIMESTAMP DEFAULT now(),
    archive_s3_key TEXT
);

CREATE TABLE edi_transactions (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    raw_file_id INT REFERENCES raw_835_files(id) ON DELETE CASCADE,
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

CREATE TABLE payers (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES edi_transactions(id) ON DELETE CASCADE,
    payer_name TEXT,
    payer_id_qualifier TEXT,
    payer_id TEXT,
    json_payer JSONB NOT NULL
);

CREATE TABLE payees (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES edi_transactions(id) ON DELETE CASCADE,
    payee_name TEXT,
    payee_id_qualifier TEXT,
    payee_id TEXT,
    json_payee JSONB NOT NULL
);

CREATE TABLE claims (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES edi_transactions(id) ON DELETE CASCADE,
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

CREATE TABLE service_lines (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    claim_id INT NOT NULL REFERENCES claims(id) ON DELETE CASCADE,
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

CREATE TABLE nm1_entities (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    claim_id INT REFERENCES claims(id) ON DELETE CASCADE,
    service_line_id INT REFERENCES service_lines(id) ON DELETE CASCADE,
    entity_type TEXT,
    last_name TEXT,
    first_name TEXT,
    middle_name TEXT,
    id_qualifier TEXT,
    entity_id TEXT,
    json_nm1 JSONB NOT NULL
);

CREATE TABLE cas_adjustments (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    claim_id INT REFERENCES claims(id) ON DELETE CASCADE,
    service_line_id INT REFERENCES service_lines(id) ON DELETE CASCADE,
    group_code TEXT,
    reason_code TEXT,
    amount NUMERIC(18,2),
    quantity DECIMAL(15,6),
    json_cas JSONB NOT NULL
);

CREATE TABLE plb_adjustments (
    id SERIAL PRIMARY KEY,
    created_date_time TIMESTAMP DEFAULT now(),
    removed_date_time TIMESTAMP,
    edi_transaction_id INT REFERENCES edi_transactions(id) ON DELETE CASCADE,
    provider_id TEXT,
    fiscal_period_date DATE,
    reason_code TEXT,
    reference_id TEXT,
    amount NUMERIC(18,2),
    json_plb JSONB NOT NULL
);

ALTER TABLE edi_transactions ADD CONSTRAINT unique_trace_per_file
    UNIQUE (raw_file_id, trace_number);
ALTER TABLE raw_835_files ADD CONSTRAINT unique_file_id_per_raw
    UNIQUE (file_id);