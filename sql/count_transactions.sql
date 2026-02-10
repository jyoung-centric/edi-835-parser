-- Count transactions in payments_835 table using json_transaction JSONB column
-- This SQL can be run directly in psql or via ./db_test.sh query

-- Basic count
SELECT
    COUNT(*) as payment_count,
    SUM(jsonb_array_length(json_transaction->'interchange'->'transactions')) as total_transactions
FROM payments_835
WHERE removed_date_time IS NULL;

-- Detailed breakdown by payment
SELECT
    id,
    file_name,
    check_number,
    payment_date,
    payment_amount,
    jsonb_array_length(json_transaction->'interchange'->'transactions') as transaction_count
FROM payments_835
WHERE removed_date_time IS NULL
ORDER BY created_date_time DESC;

-- Extract TRN details from JSON
SELECT
    id,
    file_name,
    check_number,
    payment_amount,
    payment_date,
    tx->>'TRN' as trn_data,
    (tx->'TRN'->>'trace_type_code') as trace_type,
    (tx->'TRN'->>'reference_identification') as reference_id,
    (tx->'TRN'->>'originating_company_identifier') as originating_company,
    jsonb_array_length(tx->'CLP_loop') as claim_count
FROM payments_835,
    jsonb_array_elements(json_transaction->'interchange'->'transactions') as tx
WHERE removed_date_time IS NULL
ORDER BY created_date_time DESC;

-- Summary statistics
SELECT
    COUNT(DISTINCT id) as total_payments,
    COUNT(tx) as total_transactions,
    SUM(jsonb_array_length(tx->'CLP_loop')) as total_claims,
    ROUND(AVG(jsonb_array_length(tx->'CLP_loop')), 2) as avg_claims_per_transaction,
    SUM((tx->'BPR'->>'monetary_amount')::numeric) as total_transaction_amount
FROM payments_835,
    jsonb_array_elements(json_transaction->'interchange'->'transactions') as tx
WHERE removed_date_time IS NULL;

-- Count by trace type
SELECT
    (tx->'TRN'->>'trace_type_code') as trace_type,
    COUNT(*) as count,
    SUM((tx->'BPR'->>'monetary_amount')::numeric) as total_amount
FROM payments_835,
    jsonb_array_elements(json_transaction->'interchange'->'transactions') as tx
WHERE removed_date_time IS NULL
GROUP BY (tx->'TRN'->>'trace_type_code')
ORDER BY count DESC;

-- Transactions by date
SELECT
    DATE(payment_date) as payment_date,
    COUNT(DISTINCT id) as payment_count,
    COUNT(tx) as transaction_count,
    SUM((tx->'BPR'->>'monetary_amount')::numeric) as total_amount
FROM payments_835,
    jsonb_array_elements(json_transaction->'interchange'->'transactions') as tx
WHERE removed_date_time IS NULL
GROUP BY DATE(payment_date)
ORDER BY payment_date DESC;

-- Find transactions by reference ID
-- Usage: Replace '1234567890' with actual reference ID
SELECT
    id,
    file_name,
    check_number,
    payment_date,
    (tx->'TRN'->>'reference_identification') as reference_id,
    (tx->'BPR'->>'monetary_amount') as transaction_amount
FROM payments_835,
    jsonb_array_elements(json_transaction->'interchange'->'transactions') as tx
WHERE removed_date_time IS NULL
    AND (tx->'TRN'->>'reference_identification') = '1234567890';
