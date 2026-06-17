"""Device 요청 폼/DTO (Pydantic).

원본 webservice.form.device.* 및 dto.device.* 이식.
@Validation(notes) 는 _validations 로 옮겨 원본 check() 동작을 보존한다.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.base_form import BaseForm


class DeviceInfoForm(BaseForm):
    """장비 목록 조회 — 필수값 없음(원본 check 항상 통과)."""


class DeviceAddForm(BaseForm):
    """장비 추가."""

    deviceImei: str | None = None
    ipStr: str | None = None
    deviceName: str | None = None
    type: str | None = None
    isEnable: str | None = None
    codeAct: str | None = None
    action: str | None = None

    # _validations = (
    #     ("deviceImei", "imei不能为空"),
    #     ("deviceName", "名称不能为空"),
    #     ("type", "设备类型不能为空"),
    #     ("isEnable", "是否启用不能为空"),
    # )
    _validations = (
        ("deviceImei", "IMEI는 비어있을 수 없습니다"),
        ("deviceName", "이름은 비어있을 수 없습니다"),
        ("type", "장치 유형은 비어있을 수 없습니다"),
        ("isEnable", "활성화 여부는 비어있을 수 없습니다"),
    )


class DeviceEditForm(BaseForm):
    """장비 수정."""

    deviceImei: str | None = None
    deviceName: str | None = None
    isEnable: str | None = None
    codeAct: str | None = None
    action: str | None = None

    # _validations = (("deviceImei", "imei不能为空"),)
    _validations = (("deviceImei", "IMEI는 비어있을 수 없습니다"),)


class DeviceDelForm(BaseForm):
    """장비 삭제."""

    deviceImei: str | None = None

    # _validations = (("deviceImei", "imei不能为空"),)
    _validations = (("deviceImei", "IMEI는 비어있을 수 없습니다"),)


class DeviceInitForm(BaseForm):
    """위치 초기화 (web). deviceImei + siteCode 필수."""

    deviceImei: int | None = None
    siteCode: int | None = None

    # _validations = (
    #     ("deviceImei", "设备imei不能为空"),
    #     ("siteCode", "站点位置不能为空"),
    # )
    _validations = (
        ("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),
        ("siteCode", "스테이션 위치는 비어있을 수 없습니다"),
    )


class DeviceTerminateForm(BaseForm):
    """작업 종료 (web). deviceImei 필수."""

    deviceImei: int | None = None

    # _validations = (("deviceImei", "设备imei不能为空"),)
    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceHeartBeat(BaseModel):
    """dto.device.DeviceHeartBeat."""

    deviceImei: int | None = None
    command: str | None = None


class DeviceInfoDto(BaseModel):
    """dto.device.DeviceInfoDto — 타입별 장비 목록."""

    deviceAGV: list[dict[str, Any]] | None = None
    deviceCamera: list[dict[str, Any]] | None = None
    deviceCall: list[dict[str, Any]] | None = None
    deviceScan: list[dict[str, Any]] | None = None


# ──────────────────────────────────────────────
# DeviceWebService 용 추가 폼 (web_router)
# ──────────────────────────────────────────────

class DeviceWifiInitForm(BaseForm):
    """wifi 재시작 임계값 설정 (web/setWifiRestartValue)."""

    deviceImei: int | None = None
    wifiRestartValue: int | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)


class DeviceParamsSetForm(BaseForm):
    """포크리프트 파라미터 설정 (web/setDeviceParams)."""

    deviceImei: int | None = None
    palletWidth: float | None = None
    noCargoHeight: float | None = None
    liftHeight: float | None = None
    haveCargoHeight: float | None = None

    _validations = (("deviceImei", "장치 IMEI는 비어있을 수 없습니다"),)
