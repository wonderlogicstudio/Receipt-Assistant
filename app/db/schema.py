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
    gross_amount INTEGER,
    discount_amount INTEGER,
    final_amount INTEGER,
    paid_amount INTEGER,
    amount_source TEXT,
    amount_warnings_json TEXT,
    supply_amount INTEGER,
    vat_amount INTEGER,
    estimated_supply_amount INTEGER,
    estimated_vat_amount INTEGER,
    vat_source TEXT,
    vat_note TEXT,
    vat_warnings_json TEXT,
    vat_review_required INTEGER,
    sensitive_text_detected INTEGER,
    sensitive_text_categories_json TEXT,
    sensitive_warnings_json TEXT,
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

MERCHANT_MASTER_SQL = """
CREATE TABLE IF NOT EXISTS merchant_master (
    id TEXT PRIMARY KEY,
    merchant_name TEXT NOT NULL,
    normalized_merchant_name TEXT NOT NULL,
    business_number TEXT,
    branch_name TEXT,
    area_hint TEXT,
    category_large TEXT,
    category_medium TEXT,
    category_small TEXT,
    road_name TEXT,
    building_main_number TEXT,
    building_sub_number TEXT,
    building_name TEXT,
    road_address TEXT,
    normalized_road_address TEXT,
    source TEXT NOT NULL,
    source_row_hash TEXT NOT NULL,
    source_batch_id TEXT NOT NULL,
    review_required INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""

MERCHANT_ALIAS_SQL = """
CREATE TABLE IF NOT EXISTS merchant_alias (
    id TEXT PRIMARY KEY,
    merchant_master_id TEXT,
    alias_name TEXT NOT NULL,
    normalized_alias_name TEXT NOT NULL,
    business_number TEXT,
    source TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(merchant_master_id) REFERENCES merchant_master(id)
)
"""

MERCHANT_SOURCE_LOG_SQL = """
CREATE TABLE IF NOT EXISTS merchant_source_log (
    id TEXT PRIMARY KEY,
    source_name TEXT NOT NULL,
    source_file_name TEXT,
    source_file_hash TEXT,
    source_batch_id TEXT NOT NULL,
    imported_row_count INTEGER NOT NULL DEFAULT 0,
    skipped_row_count INTEGER NOT NULL DEFAULT 0,
    duplicate_file INTEGER NOT NULL DEFAULT 0,
    note TEXT,
    created_at TEXT NOT NULL
)
"""

MERCHANT_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_master_business_number
ON merchant_master(business_number)
"""

MERCHANT_NAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_master_normalized_name
ON merchant_master(normalized_merchant_name)
"""

MERCHANT_SOURCE_INDEX_SQL = """
CREATE UNIQUE INDEX IF NOT EXISTS idx_merchant_master_source_row
ON merchant_master(source, source_row_hash)
"""

MERCHANT_ROAD_ADDRESS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_master_normalized_road_address
ON merchant_master(normalized_road_address)
"""

MERCHANT_ROAD_BUILDING_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_master_road_building
ON merchant_master(road_name, building_main_number, building_sub_number)
"""

MERCHANT_BUILDING_MAIN_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_master_building_main
ON merchant_master(building_main_number)
"""

MERCHANT_SOURCE_FILE_HASH_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_source_log_file_hash
ON merchant_source_log(source_name, source_file_hash)
"""

MERCHANT_ALIAS_BUSINESS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_alias_business_number
ON merchant_alias(business_number)
"""

MERCHANT_ALIAS_NAME_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_alias_normalized_name
ON merchant_alias(normalized_alias_name)
"""

MERCHANT_ALIAS_DEDUPE_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_merchant_alias_dedupe
ON merchant_alias(normalized_alias_name, business_number, source)
"""

SCHEMA_SQL = [
    PROCESSING_JOBS_SQL,
    UPLOADED_FILES_SQL,
    RECEIPT_RECORDS_SQL,
    CARD_TRANSACTIONS_SQL,
    EXPORT_FILES_SQL,
    MERCHANT_MASTER_SQL,
    MERCHANT_ALIAS_SQL,
    MERCHANT_SOURCE_LOG_SQL,
    MERCHANT_INDEX_SQL,
    MERCHANT_NAME_INDEX_SQL,
    MERCHANT_SOURCE_INDEX_SQL,
    MERCHANT_ROAD_ADDRESS_INDEX_SQL,
    MERCHANT_ROAD_BUILDING_INDEX_SQL,
    MERCHANT_BUILDING_MAIN_INDEX_SQL,
    MERCHANT_SOURCE_FILE_HASH_INDEX_SQL,
    MERCHANT_ALIAS_BUSINESS_INDEX_SQL,
    MERCHANT_ALIAS_NAME_INDEX_SQL,
    MERCHANT_ALIAS_DEDUPE_INDEX_SQL,
]
