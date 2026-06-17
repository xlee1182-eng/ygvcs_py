"""Device REST API.

원본 DeviceWarpWebService(@RequestMapping /service/warp/device) 이식.
엔드포인트: getDeviceInfo, addDevice, editDevice, delDevice, getAgvHeartList.
공통 패턴: 진입 로그 → form.check() → 서비스 호출 → 예외 시 syserr().
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.device import (
    DeviceAddForm,
    DeviceDelForm,
    DeviceEditForm,
    DeviceInfoForm,
    DeviceInitForm,
    DeviceParamsSetForm,
    DeviceTerminateForm,
    DeviceWifiInitForm,
)
from app.services.device import device_service

LOGGER = logging.getLogger('app')

# router = APIRouter(prefix="/service/warp/device", tags=["设备管理"])
router = APIRouter(prefix="/service/warp/device", tags=["장치 관리"])
# web_router = APIRouter(prefix="/service/web/device", tags=["设备管理(web)"])
web_router = APIRouter(prefix="/service/web/device", tags=["장치 관리(web)"])


def _param_err(msg: JsonResult) -> JsonResult:
    return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")


@router.post("/getDeviceInfo", response_model=JsonResult)
async def get_device_info(form: DeviceInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        # LOGGER.warning("获取设备列表接口入口,参数为：%s", form.param_to_string())
        LOGGER.info("장치 목록 조회 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.get_device_info(db, form)
    except Exception:
        # LOGGER.exception("获取设备列表接口出现异常！")
        LOGGER.exception("장치 목록 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/addDevice", response_model=JsonResult)
async def add_device(form: DeviceAddForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        # LOGGER.warning("新增设备接口入口,参数为：%s", form.param_to_string())
        LOGGER.info("장치 추가 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.add_device(db, form)
    except Exception:
        # LOGGER.exception("新增设备接口出现异常！")
        LOGGER.exception("장치 추가 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/editDevice", response_model=JsonResult)
async def edit_device(form: DeviceEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        # LOGGER.warning("修改设备接口入口,参数为：%s", form.param_to_string())
        LOGGER.info("장치 수정 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.edit_device(db, form)
    except Exception:
        # LOGGER.exception("修改设备接口出现异常！")
        LOGGER.exception("장치 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/delDevice", response_model=JsonResult)
async def del_device(form: DeviceDelForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        # LOGGER.warning("删除设备接口入口,参数为：%s", form.param_to_string())
        LOGGER.info("장치 삭제 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.del_device(db, form)
    except Exception:
        # LOGGER.exception("删除设备接口出现异常！")
        LOGGER.exception("장치 삭제 인터페이스 예외 발생!")
        return JsonResult.syserr()


@router.post("/getAgvHeartList", response_model=JsonResult)
async def get_agv_heart_list(form: DeviceInfoForm) -> JsonResult:
    try:
        # LOGGER.warning("获取所有设备心跳接口入口,参数为：%s", form.param_to_string())
        LOGGER.info("전체 장치 하트비트 조회 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.get_agv_heart_list(form)
    except Exception:
        # LOGGER.exception("获取所有设备心跳接口出现异常！")
        LOGGER.exception("전체 장치 하트비트 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/initLocation", response_model=JsonResult)
async def init_location(form: DeviceInitForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 DeviceWebService.initLocation."""
    try:
        # LOGGER.warning("初始化位置(对外)接口入口,参数为：%s", form.param_to_string())
        LOGGER.info("위치 초기화(외부) 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.init_location(db, form)
    except Exception:
        # LOGGER.exception("初始化位置(对外)接口出现异常！")
        LOGGER.exception("위치 초기화(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/terminateTask", response_model=JsonResult)
async def terminate_task(form: DeviceTerminateForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 DeviceWebService.terminateTask."""
    try:
        LOGGER.info("작업 종료(외부) 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.terminate_task(db, form)
    except Exception:
        LOGGER.exception("작업 종료(외부) 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/setWifiRestartValue", response_model=JsonResult)
async def set_wifi_restart_value(form: DeviceWifiInitForm) -> JsonResult:
    """원본 DeviceWebService.setWifiRestartValue."""
    try:
        LOGGER.info("wifi 재시작 임계값 설정 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.set_wifi_restart_value(form)
    except Exception:
        LOGGER.exception("wifi 재시작 임계값 설정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@web_router.post("/setDeviceParams", response_model=JsonResult)
async def set_device_params(form: DeviceParamsSetForm) -> JsonResult:
    """원본 DeviceWebService.setDeviceParams."""
    try:
        LOGGER.info("장치 파라미터 설정 인터페이스 진입, 파라미터: %s", form.param_to_string())
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await device_service.set_device_params(form)
    except Exception:
        LOGGER.exception("장치 파라미터 설정 인터페이스 예외 발생!")
        return JsonResult.syserr()
