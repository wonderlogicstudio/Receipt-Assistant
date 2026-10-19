from streamlit.testing.v1 import AppTest
from types import SimpleNamespace
import app.ui.review_view as view


def test_db_candidate_is_labeled_and_only_changes_draft_after_explicit_apply(monkeypatch):
    candidate = SimpleNamespace(candidate_merchant_name='초록놀이 바다점',match_type='business_number_exact',source='synthetic')
    matcher = SimpleNamespace(find_candidates=lambda **kwargs:[candidate])
    monkeypatch.setattr(view,'_build_merchant_matcher',lambda:matcher)
    app = AppTest.from_string('''
import streamlit as st
import app.ui.review_view as view
draft=st.session_state.setdefault('receipt_review_drafts',{}).setdefault('synthetic',{'merchant_name':'관측상호'})
st.session_state.setdefault('saved_name','관측상호')
view._render_merchant_candidates('synthetic',dict(draft,business_number='123-45-67891'),None)
st.text('saved:'+st.session_state['saved_name'])
st.text('draft:'+draft['merchant_name'])
''').run()
    app.button[0].click().run()
    assert not app.exception
    assert 'DB 조회 후보' in app.caption[0].value
    assert '사업자번호 일치' in app.selectbox[0].options[0]
    assert app.session_state['receipt_review_drafts']['synthetic']['merchant_name'] == '관측상호'
    app.selectbox[0].select(0).run()
    app.button[1].click().run()
    assert not app.exception
    assert app.session_state['receipt_review_drafts']['synthetic']['merchant_name'] == '초록놀이 바다점'
    assert app.session_state['saved_name'] == '관측상호'
