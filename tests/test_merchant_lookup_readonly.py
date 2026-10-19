from hashlib import sha256
import sqlite3

import pytest

from app.core.config import get_config
from app.db.merchant_repository import MerchantMasterInput, MerchantRepository
from app.classifier.merchant_candidate import MerchantCandidateMatcher


def test_dictionary_lookup_is_read_only_and_does_not_migrate_or_create_a_database(tmp_path):
    path = tmp_path/'dictionary.db'
    repository = MerchantRepository(db_path=path)
    entry = MerchantMasterInput(merchant_name='초록놀이 바다점',business_number='123-45-67891',
        source='synthetic', source_row_hash='one',source_batch_id='batch')
    repository.add_master(entry)
    before = sha256(path.read_bytes()).hexdigest()
    readonly = MerchantRepository(db_path=path,read_only=True)
    candidates = MerchantCandidateMatcher(readonly).find_candidates(business_number='123-45-67891')
    assert candidates[0].candidate_merchant_name == entry.merchant_name
    assert candidates[0].review_required
    with pytest.raises(sqlite3.OperationalError):
        readonly.add_master(MerchantMasterInput(merchant_name='다른공방',source='synthetic',
            source_row_hash='two',source_batch_id='batch'))
    assert sha256(path.read_bytes()).hexdigest() == before
    missing = tmp_path/'missing'/'dictionary.db'
    with pytest.raises(sqlite3.OperationalError):
        MerchantRepository(db_path=missing,read_only=True)
    assert not missing.exists() and not missing.parent.exists()


def test_lookup_database_setting_does_not_change_the_review_database(monkeypatch,tmp_path):
    monkeypatch.setenv('APP_DB_PATH',str(tmp_path/'reviews.db'))
    monkeypatch.setenv('MERCHANT_LOOKUP_DB_PATH',str(tmp_path/'dictionary.db'))
    config = get_config()
    assert config.app_db_path == tmp_path/'reviews.db'
    assert config.merchant_lookup_db_path == tmp_path/'dictionary.db'
