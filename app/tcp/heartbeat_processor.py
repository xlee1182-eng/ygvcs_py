"""차량 메시지 프로세서 (원본 PrimaryMsgProcessor).

primary 서버의 message_handler 로 주입한다. 하트비트(fun=00)면 메모리테이블을
파싱·저장한다(비동기 작업으로 스케줄). 응답(fun!=00)은 채널매니저가 상관 처리한다.
"""
from __future__ import annotations

import asyncio
import logging

from app.tcp import byte_process as bp

LOGGER = logging.getLogger('app')


def message_handler(writer, frame: bytes) -> None:
    """원본 PrimaryMsgProcessor.messageHandler 진입점(동기). fun=00 이면 비동기 저장."""
    try:
        if len(frame) <= 12:
            return
        fun = bp.print_hex_string(bp.split_byte(frame, 12, 13))
        if fun == "00":
            asyncio.create_task(_process_heartbeat(frame))
    except Exception:
        LOGGER.exception("heartbeat 처리 오류")


async def _process_heartbeat(frame: bytes) -> None:
    from app.core.database import get_sessionmaker
    from app.services.device_memory_table import save_or_update_device
    from app.services.send_task import send_task_service

    table = await save_or_update_device(frame)
    # 유휴 상태면 다음 작업을 픽업해 자동 송신 (자동화 루프 마감)
    if send_task_service.should_dispatch(table):
        async with get_sessionmaker()() as db:
            await send_task_service.dispatch_task(db, table)
