"""Site/Storage REST API.

원본 SiteWarpWebService(/service/warp/site),
     StroageDeviceWarpWebService(/service/warp/storageDevice) 이식.
작업생성 의존 엔드포인트(editStorageStatus/editAreaStatus/editScanStorageStatus)는
Task 도메인 이식 후 추가한다.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core.database import get_db
from app.core.jsonresult import JsonResult
from app.schemas.site import (
    AreaStatusEditForm,
    SiteEditForm,
    SiteInfoForm,
    StorageDeviceAddForm,
    StorageDeviceDelForm,
    StorageDeviceInfoForm,
    StorageStatusEditForm,
    StorageStatusScanEditForm,
)
from app.services.storage import storage_device_relation_service, storage_service

LOGGER = logging.getLogger('app')

# site_router = APIRouter(prefix="/service/warp/site", tags=["站点管理"])
site_router = APIRouter(prefix="/service/warp/site", tags=["스테이션 관리"])
# storage_device_router = APIRouter(prefix="/service/warp/storageDevice", tags=["库位设备管理"])
storage_device_router = APIRouter(prefix="/service/warp/storageDevice", tags=["보관위치 장치 관리"])


def _param_err(msg: JsonResult) -> JsonResult:
    return msg.set_result_msg(f"【{msg.resultMsg}】{messages.get_msg('api.paramNotEmpty')}")


@site_router.post("/getSiteInfo", response_model=JsonResult)
async def get_site_info(form: SiteInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.get_site_info(db, form)
    except Exception:
        # LOGGER.exception("获取站点列表接口出现异常！")
        LOGGER.exception("스테이션 목록 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/getSiteByDevice", response_model=JsonResult)
async def get_site_by_device(form: StorageDeviceInfoForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.get_site_by_device(db, form)
    except Exception:
        # LOGGER.exception("根据设备获取已绑定的库位接口出现异常！")
        LOGGER.exception("장치 기준 바인딩된 보관위치 조회 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editStorage", response_model=JsonResult)
async def edit_storage(form: SiteEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_storage(db, form)
    except Exception:
        # LOGGER.exception("修改库位接口出现异常！")
        LOGGER.exception("보관위치 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@storage_device_router.post("/editStorageDevice", response_model=JsonResult)
async def edit_storage_device(form: StorageDeviceAddForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_device_relation_service.edit_storage_device(db, form)
    except Exception:
        # LOGGER.exception("绑定库位设备接口出现异常！")
        LOGGER.exception("보관위치 장치 바인딩 인터페이스 예외 발생!")
        return JsonResult.syserr()


@storage_device_router.post("/delStorageDevice", response_model=JsonResult)
async def del_storage_device(form: StorageDeviceDelForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_device_relation_service.del_storage_device(db, form)
    except Exception:
        # LOGGER.exception("解绑库位设备接口出现异常！")
        LOGGER.exception("보관위치 장치 바인딩 해제 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editStorageStatus", response_model=JsonResult)
async def edit_storage_status(form: StorageStatusEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 editStorageStatus: 수동 상태변경 (deviceImei="0")."""
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_storage_status(
            db, "0", "0", form.siteCode, form.siteStatus, form.actionType
        )
    except Exception:
        # LOGGER.exception("修改库位状态接口出现异常！")
        LOGGER.exception("보관위치 상태 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editScanStorageStatus", response_model=JsonResult)
async def edit_scan_storage_status(form: StorageStatusScanEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 editScanStorageStatus: 스캐너 상태변경."""
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_scan_storage_status(db, form)
    except Exception:
        # LOGGER.exception("扫码修改库位状态接口出现异常！")
        LOGGER.exception("바코드 스캔 보관위치 상태 수정 인터페이스 예외 발생!")
        return JsonResult.syserr()


@site_router.post("/editAreaStatus", response_model=JsonResult)
async def edit_area_status(form: AreaStatusEditForm, db: AsyncSession = Depends(get_db)) -> JsonResult:
    """원본 editAreaStatus: 구역 일괄 상태변경(일괄 창고 정리)."""
    try:
        msg = form.check()
        if not msg.is_success():
            return _param_err(msg)
        return await storage_service.edit_area_status(db, form)
    except Exception:
        # LOGGER.exception("一键清满库接口出现异常！")
        LOGGER.exception("일괄 창고 정리 인터페이스 예외 발생!")
        return JsonResult.syserr()
