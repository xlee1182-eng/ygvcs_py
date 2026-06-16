"""UserTask 서비스 (실작업 조회/취소/초기화).

원본 UserTaskServiceImpl + UserTaskWebService 의 DB 기반 메서드 이식.
- getTaskInfo / getTaskResult / getPickPlaceState / cancelTask / clearTask
- 실작업 송신(addTask/setTask/sendRepeatTask/callDeviceTask) 은 TCP 송신 의존 → 후속.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core import messages
from app.core import redis_constants as rc
from app.core.jsonresult import JsonResult
from app.models.tables import UserTask
from app.repositories.task import user_task_repository
from app.utils import json_util
from app.utils.redis_util import redis_util


class UserTaskService:
    async def get_task_info(self, db: AsyncSession, customer_id: str | None, message_id: str) -> dict | None:
        """원본 getTaskInfo: Redis 캐시 우선, 없으면 messageId 로 DB 조회 후 10초 캐시."""
        cache_key = f"{rc.TASK_STATE}_{message_id}"
        cached = await redis_util.get_str_to_object(cache_key)
        if cached is not None:
            return cached
        entity = await user_task_repository.select_one(db, {"message_id": message_id})
        if entity is not None:
            d = json_util.to_dict(entity)
            await redis_util.set_to_json(cache_key, d, 10)
            return d
        return None

    async def get_task_result(self, db: AsyncSession, customer_id: str | None, message_id: str | None) -> JsonResult:
        """원본 getTaskResult: send_flag 반환."""
        if not message_id:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.MessageIdNotNull"))
        task = await self.get_task_info(db, customer_id, message_id)
        if task is None:
            return JsonResult.fail("1", messages.get_msg("TaskService.getTaskResult.TaskNotExit"))
        msg = JsonResult.success()
        msg.data = task.get("send_flag")
        return msg

    async def get_pick_place_state(self, db: AsyncSession, customer_id: str | None, message_id: str | None) -> JsonResult:
        """원본 getPickPlaceState: pick_place_state 반환."""
        if not message_id:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.MessageIdNotNull"))
        task = await self.get_task_info(db, customer_id, message_id)
        if task is None:
            return JsonResult.fail("1", messages.get_msg("TaskService.getTaskResult.TaskNotExit"))
        msg = JsonResult.success()
        msg.data = task.get("pick_place_state")
        return msg

    async def cancel_task(self, db: AsyncSession, device_imei: int | None) -> JsonResult:
        """원본 cancelTask: 해당 장비의 미실행(send_flag='1') 작업을 취소('7')."""
        if device_imei is None:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.DeviceImeiNotNull"))
        await user_task_repository.update_by_example(
            db,
            {"send_flag": "7", "updated_by": "cancel", "updated_date": datetime.now()},
            {"device_imei": device_imei, "send_flag": "1"},
        )
        await db.commit()
        return JsonResult.success()

    async def clear_task(self, db: AsyncSession) -> JsonResult:
        """원본 clearTask: 전체 작업 삭제(빈 예시 = 전체)."""
        await user_task_repository.delete(db, {})
        await db.commit()
        return JsonResult.success()

    async def add_task(self, db: AsyncSession, form) -> JsonResult:
        """원본 UserTaskServiceImpl.addTask: 외부 작업 송신.

        장비 메모리상태 검증 → 폼 검증 → UserTask 구성 → 프레임 송신/응답파싱 → send_flag='2' 저장.
        """
        from app.models.tables import UserTask
        from app.repositories.site import site_manage_repository
        from app.services.send_task import send_task_service
        from app.services.sequence_service import sequence_service
        from app.tcp.response_parser import is_0xff_or_0x00
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        # 1) 장비 메모리테이블 상태 검증
        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
        if not isinstance(exit_mem, dict) or exit_mem.get("flag") == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        flag = exit_mem.get("flag")
        if flag in ("77", "78", "79"):
            return JsonResult.fail("1", messages.get_msg("TaskService.addTask.unknownPosition"))
        if exit_mem.get("taskFlag", 0) != 0:
            return JsonResult.fail("1", f"{messages.get_msg('device.taskNotMark')}【{exit_mem.get('taskFlag')}】")
        if flag not in ("77", "78", "79", "82", "83", "8E", "8F", "95", "96", "E5"):
            return JsonResult.fail("1", f"{messages.get_msg('device.notSendTaskState')}【{flag}】")
        if exit_mem.get("startSiteCode", 0) == 0 or exit_mem.get("endSiteCode", 0) == 0:
            return JsonResult.fail("1", messages.get_msg("TaskService.addTask.unknownPosition"))
        if exit_mem.get("lockState", 0) == 0:
            return JsonResult.fail("4", messages.get_msg("TaskService.sendTask.ButtonNotLock"))

        # 2) 폼 검증
        if not form.messageId:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.MessageIdNotNull"))
        if form.startSiteCode is None:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.StartCodeNotNull"))
        if form.endSiteCode is not None and form.startSiteCode == form.endSiteCode:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.StartEquallyEnd"))

        # 3) 메시지ID 중복
        dup = await user_task_repository.select_one(db, {"message_id": form.messageId})
        if dup is not None:
            return JsonResult.fail("5", messages.get_msg("TaskService.sendTask.taskIsExists"))

        # 4) 사이트 명칭 조회 (SiteManage)
        start_site = await site_manage_repository.select_one(db, {"site_manage_id": form.startSiteCode})
        if start_site is None:
            return JsonResult.fail("1", f"{messages.get_msg('TaskService.sendTask.CodeNotExit')}【{form.startSiteCode}】")
        end_name = None
        if form.endSiteCode is not None:
            end_site = await site_manage_repository.select_one(db, {"site_manage_id": form.endSiteCode})
            if end_site is None:
                return JsonResult.fail("1", f"{messages.get_msg('TaskService.sendTask.CodeNotExit')}【{form.endSiteCode}】")
            end_name = end_site.site_manage_name

        # 5) UserTask 구성
        way_points = [wp.model_dump() for wp in (form.taskWayPoints or [])]
        ut = UserTask(
            user_task_id=await sequence_service.add_and_get_user_task_id(db),
            message_id=form.messageId,
            device_imei=form.deviceImei,
            fun_code="B2",
            start_site_code=form.startSiteCode,
            end_site_code=form.endSiteCode,
            task_group_id="0",
            start_site_name=start_site.site_manage_name,
            end_site_name=end_name,
            start_handel=form.startHandel if form.startHandel else "0",
            end_handel=form.endHandel if form.endHandel else "0",
            start_storage_height=form.startStorageHeight or 0,
            end_storage_height=form.endStorageHeight or 0,
            is_loop="0",
            created_by="admin",
            created_time=datetime.now(),
            lift_height=form.upDownHeight if form.upDownHeight is not None else 100,
            pick_place_state="0",
            task_is_cancel=form.taskIsCancel if form.taskIsCancel else "1",
            task_type="0",
            way_points=json_util.to_json(way_points) if way_points else None,
        )

        # 6) 프레임 송신 + 응답 파싱
        frames = send_task_service.append_task(ut, form.deviceImei, way_points)
        if not frames:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.DeviceIsBusy"))
        task = TaskModel()
        for frame in frames:
            task.requestMsg = frame
            result = await send_tcp_msg(task)
            if not result.status:
                return JsonResult.fail("1", f"{messages.get_msg('TaskService.sendTask.TaskIsFail')}【{result.msg}】")
            task.funCode = result.msg[24:26]
            task.responseMsg = result.msg
            parsed = is_0xff_or_0x00(task)
            if not parsed.status:
                return JsonResult.fail("1", f"{messages.get_msg('TaskService.sendTask.TaskIsFail')}【{parsed.msg}】")

        # 7) 성공: send_flag='2' 저장
        ut.send_flag = "2"
        await user_task_repository.insert(db, ut)
        await db.commit()
        return JsonResult.success(form.messageId)

    async def call_device_task(self, db: AsyncSession, form) -> JsonResult:
        """원본 callDeviceTask: 장비 호출 작업(taskType=4) 생성. 픽업 대기."""
        from datetime import datetime as _dt

        from app.models.tables import UserTask
        from app.services.sequence_service import sequence_service

        if form.siteCode is None:
            return JsonResult.fail("1", messages.get_msg("device.initLocation.siteCodeBotNull"))
        existing = await user_task_repository.select_by_flags_type(db, ["1", "2"], "4")
        if existing:
            return JsonResult.fail("1", messages.get_msg("TaskService.callDeviceTask.callTaskIsExists"))

        ut = UserTask(
            user_task_id=await sequence_service.add_and_get_user_task_id(db),
            send_flag="1",
            fun_code="B2",
            start_site_code=form.siteCode,
            start_site_name=str(form.siteCode),
            start_handel=form.startHandel if form.startHandel else "0",
            start_storage_height=0,
            is_loop="0",
            task_type="4",
            lift_height=100,
            task_group_id="0",
            pick_place_state="0",
            task_is_cancel="1",
            created_time=_dt.now(),
            created_by=form.userName if form.userName else "system",
        )
        await user_task_repository.insert(db, ut)
        await db.commit()
        return JsonResult.success()

    async def send_points_task(self, db: AsyncSession, form) -> JsonResult:
        """원본 sendPointsTask: 점대점 작업 직접 송신."""
        from datetime import datetime as _dt

        from app.models.tables import UserTask
        from app.services.send_task import send_task_service
        from app.services.sequence_service import sequence_service
        from app.tcp.response_parser import is_0xff_or_0x00
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
        if not isinstance(exit_mem, dict) or exit_mem.get("flag") == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        flag = exit_mem.get("flag")
        if flag in ("77", "78", "79"):
            return JsonResult.fail("1", messages.get_msg("TaskService.addTask.unknownPosition"))
        if exit_mem.get("taskFlag", 0) != 0:
            return JsonResult.fail("1", f"{messages.get_msg('device.taskNotMark')}【{exit_mem.get('taskFlag')}】")
        if flag not in ("10", "77", "78", "79", "82", "83", "8E", "8F", "95", "96", "E5"):
            return JsonResult.fail("1", f"{messages.get_msg('device.notSendTaskState')}【{flag}】")
        if exit_mem.get("startSiteCode", 0) == 0 or exit_mem.get("endSiteCode", 0) == 0:
            return JsonResult.fail("1", messages.get_msg("TaskService.addTask.unknownPosition"))

        ut = UserTask(
            user_task_id=await sequence_service.add_and_get_user_task_id(db),
            device_imei=form.deviceImei,
            fun_code="B2",
            start_site_code=form.startSiteCode,
            start_site_name=form.startSiteName,
            end_site_code=form.endSiteCode,
            end_site_name=form.endSiteName,
            start_handel=form.startHandel if form.startHandel else "0",
            end_handel=form.endHandel if form.endHandel else "0",
            start_storage_height=form.startStorageHeight or 0,
            end_storage_height=form.endStorageHeight or 0,
        )
        frames = send_task_service.append_task(ut, form.deviceImei)
        if exit_mem.get("lockState", 0) == 0:
            frames.insert(0, send_task_service.task_lock(form.deviceImei, 1))

        task = TaskModel()
        for frame in frames:
            task.requestMsg = frame
            result = await send_tcp_msg(task)
            if not result.status:
                return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
            task.funCode = result.msg[24:26]
            task.responseMsg = result.msg
            parsed = is_0xff_or_0x00(task)
            if parsed.status:
                continue
            if task.funCode == "B2":
                return JsonResult.fail("1", messages.get_msg(f"sendTask.UserTaskServiceImpl.flag_B2_{parsed.msg}"))
            return JsonResult.fail("1", f"{messages.get_msg('TaskService.sendTask.TaskIsFail')}【{parsed.msg}】")

        # 성공: 작업 메타 채우고 저장 (원본은 send_flag 미설정)
        ut.is_loop = "0"
        ut.created_by = form.userName
        ut.created_time = _dt.now()
        ut.task_type = "1"
        ut.lift_height = 100
        ut.task_group_id = "0"
        ut.pick_place_state = "0"
        ut.task_is_cancel = "1"
        ut.device_type = "0"
        await user_task_repository.insert(db, ut)
        await db.commit()
        return JsonResult.success()

    async def set_keyboard_lock(self, db: AsyncSession, form) -> JsonResult:
        """원본 setKeyboardLock: 키보드 작업 잠금 명령 송신."""
        from app.services.send_task import send_task_service
        from app.tcp.tcp_client import TaskModel, send_tcp_msg

        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{form.deviceImei}")
        if not isinstance(exit_mem, dict) or exit_mem.get("flag") == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        flag = exit_mem.get("flag")
        if flag in ("77", "78", "79"):
            return JsonResult.fail("1", messages.get_msg("TaskService.addTask.unknownPosition"))
        if exit_mem.get("taskFlag", 0) != 0:
            return JsonResult.fail("1", f"{messages.get_msg('device.taskNotMark')}【{exit_mem.get('taskFlag')}】")
        if flag not in ("10", "82", "83", "8E", "95"):
            return JsonResult.fail("1", f"{messages.get_msg('device.notSendTaskState')}【{flag}】")

        task = TaskModel()
        task.requestMsg = send_task_service.task_lock(form.deviceImei, form.lockState)
        result = await send_tcp_msg(task)
        if not result.status:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.TaskIsFail"))
        return JsonResult.success()

    async def set_task(self, db: AsyncSession, form) -> JsonResult:
        """원본 setTask: 작업 시작/일시정지/종료 제어."""
        from datetime import datetime as _dt

        from app.services.send_task import send_task_service

        tasks = await user_task_repository.select(db, {"message_id": form.messageId})
        if not tasks:
            return JsonResult.fail("1", messages.get_msg("TaskService.getTaskResult.TaskNotExit"))
        t = tasks[0]
        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{t.device_imei}")
        mem = exit_mem if isinstance(exit_mem, dict) else None

        # 종료('3') + 현재 장비가 이 작업을 수행중이 아니면 → DB에서 취소(7)
        if form.taskState == "3" and (mem is None or mem.get("userTaskId") != t.user_task_id):
            t.send_flag = "7"
            t.updated_date = _dt.now()
            await user_task_repository.update_by_pk(db, t)
            await db.commit()
            return JsonResult.success()
        # 장비 모드 2/3(작업/설정) 가 아니면 사용 불가
        if mem is None or mem.get("model") not in (2, 3):
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.DeviceIsBusy"))
        if form.taskState == "3":
            return await send_task_service.terminate_task(t.device_imei)
        if form.taskState in ("1", "2") and mem.get("userTaskId") == t.user_task_id:
            return await send_task_service.start_or_pause_task(t.device_imei, form.taskState)
        return JsonResult.success()

    async def send_repeat_task(self, db: AsyncSession, form) -> JsonResult:
        """원본 sendRepeatTask: 기존 작업을 동일 장비로 재송신."""
        from app.tcp.response_parser import is_0xff_or_0x00
        from app.tcp.tcp_client import TaskModel, send_tcp_msg
        from app.services.send_task import send_task_service

        tasks = await user_task_repository.select(db, {"message_id": form.messageId})
        if not tasks:
            return JsonResult.fail("1", messages.get_msg("TaskService.getTaskResult.TaskNotExit"))
        t = tasks[0]
        exit_mem = await redis_util.get_str_to_object(f"{rc.DEVICE_TASK_TABLE}{t.device_imei}")
        if not isinstance(exit_mem, dict) or exit_mem.get("flag") == "FF":
            return JsonResult.fail("1", messages.get_msg("device.notConnected"))
        flag = exit_mem.get("flag")
        if flag in ("77", "78", "79"):
            return JsonResult.fail("1", messages.get_msg("TaskService.addTask.unknownPosition"))
        if exit_mem.get("taskFlag", 0) != 0:
            return JsonResult.fail("1", f"{messages.get_msg('device.taskNotMark')}【{exit_mem.get('taskFlag')}】")
        if flag not in ("77", "78", "79", "82", "83", "8E", "8F", "95", "96", "E5"):
            return JsonResult.fail("1", f"{messages.get_msg('device.notSendTaskState')}【{flag}】")
        if exit_mem.get("startSiteCode", 0) == 0 or exit_mem.get("endSiteCode", 0) == 0:
            return JsonResult.fail("1", messages.get_msg("TaskService.addTask.unknownPosition"))
        if exit_mem.get("lockState", 0) == 0:
            return JsonResult.fail("4", messages.get_msg("TaskService.sendTask.ButtonNotLock"))

        way_points = json_util.to_list(t.way_points) if t.way_points else []
        frames = send_task_service.append_task(t, t.device_imei, way_points)
        if not frames:
            return JsonResult.fail("1", messages.get_msg("TaskService.sendTask.DeviceIsBusy"))
        task = TaskModel()
        for frame in frames:
            task.requestMsg = frame
            result = await send_tcp_msg(task)
            if not result.status:
                return JsonResult.fail("1", f"{messages.get_msg('TaskService.sendTask.TaskIsFail')}【{result.msg}】")
            task.funCode = result.msg[24:26]
            task.responseMsg = result.msg
            parsed = is_0xff_or_0x00(task)
            if not parsed.status:
                return JsonResult.fail("1", f"{messages.get_msg('TaskService.sendTask.TaskIsFail')}【{parsed.msg}】")

        t.send_flag = "2"
        await user_task_repository.update_by_pk(db, t)
        await db.commit()
        return JsonResult.success()


user_task_service = UserTaskService()
