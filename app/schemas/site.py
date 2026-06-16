"""Site/Storage 요청 폼/DTO (Pydantic).

원본 webservice.form.site.* 이식.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.schemas.base_form import BaseForm


class SiteInfoForm(BaseForm):
    """보관위치(사이트) 목록 조회 — 필수값 없음."""


class SiteEditForm(BaseForm):
    """보관위치 수정."""

    storageId: str | None = None
    siteName: str | None = None
    isEnable: str | None = None

    # _validations = (("storageId", "库位id不能为空"),)
    _validations = (("storageId", "보관위치 ID는 비어있을 수 없습니다"),)


class StorageInfo(BaseModel):
    """StorageDeviceAddForm 내 보관위치 항목."""

    siteCode: int | None = None
    siteName: str | None = None
    siteType: str | None = None
    orderNo: int | None = None


class StorageDeviceAddForm(BaseForm):
    """보관위치-장비 바인딩."""

    deviceImei: str | None = None
    ipStr: str | None = None
    type: str | None = None
    deviceName: str | None = None
    storageInfos: list[StorageInfo] | None = None

    # _validations = (
    #     ("deviceImei", "设备imei不能为空"),
    #     ("type", "设备类型不能为空"),
    #     ("deviceName", "设备名称不能为空"),
    #     ("storageInfos", "库位信息不能为空"),
    # )
    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("type", "장치 유형은 비어있을 수 없습니다"),
        ("deviceName", "장치 이름은 비어있을 수 없습니다"),
        ("storageInfos", "보관위치 정보는 비어있을 수 없습니다"),
    )


class StorageDeviceDelForm(BaseForm):
    """보관위치-장비 바인딩 해제."""

    siteCode: int | None = None

    # _validations = (("siteCode", "站点code不能为空"),)
    _validations = (("siteCode", "스테이션 코드는 비어있을 수 없습니다"),)


class StorageDeviceInfoForm(BaseForm):
    """장비별 바인딩된 보관위치 조회."""

    deviceImei: str | None = None

    # _validations = (("deviceImei", "设备imei不能为空"),)
    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class StorageStatusEditForm(BaseForm):
    """보관위치 상태 변경(수동)."""

    siteCode: int | None = None
    siteStatus: str | None = None
    actionType: str | None = None

    # _validations = (
    #     ("siteCode", "站点code不能为空"),
    #     ("siteStatus", "库位状态不能为空"),
    #     ("actionType", "操作类型不能为空"),
    # )
    _validations = (
        ("siteCode", "스테이션 코드는 비어있을 수 없습니다"),
        ("siteStatus", "보관위치 상태는 비어있을 수 없습니다"),
        ("actionType", "작업 유형은 비어있을 수 없습니다"),
    )


class AreaStatusEditForm(BaseForm):
    """구역 일괄 상태 변경(일괄 창고 정리)."""

    taskTemplateId: int | None = None
    siteStatus: str | None = None
    type: str | None = None

    # _validations = (
    #     ("taskTemplateId", "模板id不能为空"),
    #     ("siteStatus", "库位状态不能为空"),
    #     ("type", "操作区域不能为空"),
    # )
    _validations = (
        ("taskTemplateId", "템플릿 ID는 비어있을 수 없습니다"),
        ("siteStatus", "보관위치 상태는 비어있을 수 없습니다"),
        ("type", "작업 구역은 비어있을 수 없습니다"),
    )


class StorageStatusScanEditForm(BaseForm):
    """보관위치 상태 변경(스캐너)."""

    deviceImei: str | None = None
    siteCode: int | None = None
    siteStatus: str | None = None
    deviceType: str | None = None
    actionType: str | None = None

    # _validations = (
    #     ("deviceImei", "设备imei不能为空"),
    #     ("siteCode", "站点code不能为空"),
    #     ("deviceType", "设备类型不能为空"),
    # )
    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("siteCode", "스테이션 코드는 비어있을 수 없습니다"),
        ("deviceType", "장치 유형은 비어있을 수 없습니다"),
    )
