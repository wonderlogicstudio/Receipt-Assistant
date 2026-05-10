PROCESSING_JOBS_SQL = """
CREATE TABLE IF NOT EXISTS processing_jobs (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    receipt_count INTEGER NOT NULL DEFAULT 0,
    card_transaction_count INTEGER NOT NULL DEFAULT 0,
    needs_review_count INTEGER NOT NULL DEFAULT 0,
    excluded_count INTEGER NOT NULL DEFAULT 0,
    total_amount INTEGER NOT NULL DEFAULT 0,
    export_file_name TEXT,
    export_relative_path TEXT,
    note TEXT
)
"""

UPLOADED_FILES_SQL = """
CREATE TABLE IF NOT EXISTS uploaded_files (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    session_id TEXT,
    original_file_name TEXT,
    stored_file_name TEXT,
    stored_relative_path TEXT,
    file_extension TEXT,
    file_size_bytes INTEGER,
    file_role TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES processing_jobs(id)
)
"""

RECEIPT_RECORDS_SQL = """
CREATE TABLE IF NOT EXISTS receipt_records (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    session_id TEXT,
    source_file_id TEXT,
    ocr_result_id TEXT,
    source_file_name TEXT,
    transaction_date TEXT,
    merchant_name TEXT,
    business_number TEXT,
    total_amount INTEGER,
    supply_amount INTEGER,
    vat_amount INTEGER,
    payment_method TEXT,
    recommended_expense_category TEXT,
    expense_category TEXT,
    review_status TEXT,
    review_reasons_json TEXT,
    validation_warnings_json TEXT,
    parser_warnings_json TEXT,
    card_match_status TEXT,
    card_match_reason TEXT,
    card_match_score REAL,
    duplicate_suspected INTEGER,
    memo TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES processing_jobs(id)
)
"""

CARD_TRANSACTIONS_SQL = """
CREATE TABLE IF NOT EXISTS card_transactions (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    session_id TEXT,
    source_file_id TEXT,
    source_file_name TEXT,
    transaction_date TEXT,
    merchant_name TEXT,
    total_amount INTEGER,
    card_name TEXT,
    approval_number TEXT,
    currency TEXT,
    parse_status TEXT,
    warning_messages_json TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES processing_jobs(id)
)
"""

EXPORT_FILES_SQL = """
CREATE TABLE IF NOT EXISTS export_files (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL,
    session_id TEXT,
    export_file_name TEXT,
    export_relative_path TEXT,
    file_size_bytes INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(job_id) REFERENCES processing_jobs(id)
)
"""

SCHEMA_SQL = [
    PROCESSING_JOBS_SQL,
    UPLOADED_FILES_SQL,
    RECEIPT_RECORDS_SQL,
    CARD_TRANSACTIONS_SQL,
    EXPORT_FILES_SQL,
]
