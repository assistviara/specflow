from abc import ABC

from core.approval_record_repository import ApprovalRecordRepository


def test_approval_record_repository_is_abstract_contract():
    assert issubclass(ApprovalRecordRepository, ABC)

    abstract_methods = ApprovalRecordRepository.__abstractmethods__

    assert "save" in abstract_methods
    assert "get" in abstract_methods