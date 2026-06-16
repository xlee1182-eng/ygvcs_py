"""Device 서비스.

원본 DeviceServiceImpl 이식.
- CRUD(addDevice/editDevice/delDevice/getDeviceInfo) + getAgvHeartList: 완전 이식.
- initLocation/terminateTask: 라이브 TCP 송신 의존 → TCP 서버 milestone에서 완성(스텁).
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core import redis_constants as rc
from app.core.jsonresult import JsonResult
from app.repositories.device import (
    device_repository,
    storage_device_relation_repository,
    task_temp_device_repository,
)
from app.schemas.device import (
    DeviceAddForm,
    DeviceDelForm,
    DeviceEditForm,
    DeviceHeartBeat,
    DeviceInfoDto,
    DeviceInfoForm,
)
from app.tcp import byte_process as bp
from app.utils import json_util
from app.utils.redis_util import redis_util


def _device_dict(d) -> dict:
    """yg_device 엔티티 -> camelCase 응답 dict (원본 DeviceEntity JSON 포맷 일치)."""
    return {
        "deviceImei": d.device_imei,
        "deviceName": d.device_name,
        "type": d.type,
        "flag": d.flag,
        "codeAct": d.code_act,
        "ipStr": d.ip_str,
        "action": d.action,
        "isEnable": d.is_enable,
        "callType": d.call_type,
        "createdBy": d.created_by,
        "createdDate": d.created_date,
        "updatedBy": d.updated_by,
        "updatedDate": d.updated_date,
        "deviceHeartBeat": None,
    }


class DeviceService:
    async def get_device_info(self, db: AsyncSession, form: DeviceInfoForm) -> JsonResult:
        """원본 getDeviceInfo: 전체 장비를 type별로 묶고 Redis 상태를 합성."""
        devices = await device_repository.select_all(db)
        if not devices:
            return JsonResult.success()

        prod: dict[str, list[dict]] = {}
        for d in devices:
            prod.setdefault(d.type, []).append(_device_dict(d))

        dto = DeviceInfoDto()

        # type "1": AGV — 메모리테이블 flag + 하트비트
        agv = prod.get("1")
        if agv is not None:
            for item in agv:
                imei = item["deviceImei"]
                mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TABLE_PREXFIX}{imei}")
                item["flag"] = "FF" if mem is None else mem.get("flag")
                hb = await redis_util.get_str_to_object(f"{rc.DEVICE_HEART_BEAT}{imei}", str)
                item["deviceHeartBeat"] = hb.replace('"', "") if hb else None
            dto.deviceAGV = agv

        # type "3": 호출박스
        call = prod.get("3")
        if call is not None:
            for item in call:
                imei = item["deviceImei"]
                val = await redis_util.get_str_to_object(f"{rc.CALL_BOX_TABLE}{imei}", str)
                item["flag"] = "FF" if val is None else val
            dto.deviceCall = call

        dto.deviceCamera = prod.get("2")
        dto.deviceScan = prod.get("4")
        return JsonResult.success(dto.model_dump())

    async def add_device(self, db: AsyncSession, form: DeviceAddForm) -> JsonResult:
        """원본 addDevice."""
        exists = await device_repository.select_by_pk(db, form.deviceImei)
        if exists is not None:
            return JsonResult.fail("1", messages.get_msg("device.addDevice.imeiExists"))

        dup = await device_repository.select(db, {"device_name": form.deviceName})
        if dup:
            return JsonResult.fail("1", messages.get_msg("device.addDevice.nameExists"))

        if form.type == "2" and not (form.action and form.action.strip()):
            return JsonResult.fail("1", messages.get_msg("device.addDevice.actionNotNull"))

        from app.models.tables import Device

        entity = Device(
            device_imei=form.deviceImei,
            device_name=form.deviceName,
            type=form.type,
            is_enable=form.isEnable,
            code_act=form.codeAct,
            action=form.action if (form.action and form.action.strip()) else "2",
            created_by=form.userName,
            created_date=datetime.now(),
        )
        await device_repository.insert(db, entity)
        await db.commit()
        await redis_util.set_to_str(f"{rc.DEVICE_}{entity.device_imei}", json_util.to_dict(entity))
        return JsonResult.success()

    async def edit_device(self, db: AsyncSession, form: DeviceEditForm) -> JsonResult:
        """원본 editDevice."""
        entity = await device_repository.select_by_pk(db, form.deviceImei)
        if entity is None:
            return JsonResult.fail("1", messages.get_msg("device.editDevice.noDevice"))

        entity.code_act = form.codeAct
        if form.deviceName and form.deviceName.strip():
            dup = await device_repository.select(db, {"device_name": form.deviceName})
            if dup:
                return JsonResult.fail("1", messages.get_msg("device.addDevice.nameExists"))
            entity.device_name = form.deviceName
            # 연결된 보관위치 관계의 장비명도 갱신 (updateByConditionSelective)
            await storage_device_relation_repository.update_by_example(
                db, {"device_name": form.deviceName}, {"device_imei": entity.device_imei}
            )
        if form.isEnable and form.isEnable.strip():
            entity.is_enable = form.isEnable
        if form.action and form.action.strip():
            entity.action = form.action
        entity.updated_by = form.userName
        entity.updated_date = datetime.now()
        await device_repository.update_by_pk(db, entity)
        await db.commit()
        await redis_util.set_to_str(f"{rc.DEVICE_}{entity.device_imei}", json_util.to_dict(entity))
        return JsonResult.success()

    async def del_device(self, db: AsyncSession, form: DeviceDelForm) -> JsonResult:
        """원본 delDevice: 장비 + 관계 + 임시작업장비 삭제, Redis 정리."""
        await device_repository.delete_by_pk(db, form.deviceImei)
        await redis_util.delete_by_key(f"{rc.DEVICE_}{form.deviceImei}")
        await storage_device_relation_repository.delete(db, {"device_imei": form.deviceImei})
        if form.deviceImei is not None and form.deviceImei.lstrip("-").isdigit():
            await task_temp_device_repository.delete(db, {"device_imei": int(form.deviceImei)})
        await db.commit()
        await redis_util.delete_by_key(f"{rc.DEVICE_}{form.deviceImei}")
        return JsonResult.success()

    async def get_agv_heart_list(self, form: DeviceInfoForm) -> JsonResult:
        """원본 DeviceWarpWebService.getAgvHeartList: 하트비트 키들에서 imei/command 추출."""
        msg = JsonResult.success()
        keys = await redis_util.wildcard_key(f"{rc.DEVICE_HEART_BEAT}*")
        result: list[dict] = []
        for key in keys or []:
            redis_table = await redis_util.get_str_to_object(key, str)
            if not redis_table or not redis_table.strip():
                continue
            hb = DeviceHeartBeat(
                deviceImei=bp.bytes_to_int(bp.hex_string_to_bytes(redis_table[17:25]), 4),
                command=redis_table.replace('"', ""),
            )
            result.append(hb.model_dump())
        msg.data = result
        return msg

    async def init_location(self, db: AsyncSession, form) -> JsonResult:
        """원본 initLocation: 장비 상태 확인 → 회차라인 조회 → 위치초기화 프레임 송신.

        form: deviceImei(int), siteCode(int).
        """
        import random

        from app.services.forklift_line import forklift_line_service
        from app.tcp import constants
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        # 1) 장비 메모리테이블 상태 확인
        exit_mem = await redis_util.get_str_to_object(
            f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}"
        )
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        # 유휴 상태(77/78/83/79)만 허용
        if flag not in ("77", "78", "83", "79"):
            return JsonResult.fail("1", messages.get_msg("device.notIdle"))

        # 2) 회차 라인(학습 데이터) 조회
        lines = await forklift_line_service.get_line_to_init(
            db, form.deviceImei, site_code=form.siteCode
        )
        if not lines:
            return JsonResult.fail("1", messages.get_msg("site.initLocation.siteCodeLineNotLearn"))

        # 3) 위치초기화 프레임 구성 (원본 contant)
        mem_imei = exit_mem.get("deviceImei", form.deviceImei)
        parts = ["40BF807F"]
        parts.append(bp.print_hex_string(bp.int_to_bytes(random.randint(1, 999999), 4)))
        parts.append(bp.print_hex_string(bp.int_to_bytes(int(mem_imei), 4)))
        parts.append(constants.FUN_CODES[71])
        parts.append("0007")
        parts.append(bp.print_hex_string(bp.int_to_bytes(form.siteCode, 3)))
        first = lines[0]
        if first.get("returnLineId"):
            parts.append("00")
            parts.append(bp.print_hex_string(bp.int_to_bytes(int(first["returnLineId"]), 3)))
        elif first.get("returnParentId"):
            parts.append("00")
            parts.append(bp.print_hex_string(bp.int_to_bytes(int(first["returnParentId"]), 3)))
        else:
            parts.append("00")
            parts.append(bp.print_hex_string(bp.int_to_bytes(0, 3)))

        task = TaskModel()
        task.requestMsg = bp.get_crc_to_send("".join(parts), "123456789")
        result = await send_tcp_msg(task)
        if not result.status:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        return JsonResult.success()

    async def terminate_task(self, db: AsyncSession, form) -> JsonResult:
        """원본 terminateTask: 장비 연결 확인 후 종료 작업 송신(SendTask)."""
        from app.services.send_task import send_task_service

        exit_mem = await redis_util.get_str_to_object(
            f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}"
        )
        flag = exit_mem.get("flag") if isinstance(exit_mem, dict) else None
        if exit_mem is None or flag == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        return await send_task_service.terminate_task(form.deviceImei)


device_service = DeviceService()
