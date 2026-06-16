"""하트비트 → 장비 메모리테이블 파서.

원본 DeviceMemoryTableServiceImpl.saveOrUpdateDevice(byte[]) 이식.
AGV 하트비트(fun=00) 프레임을 바이트 오프셋으로 디코딩해 Redis 에 저장한다.
이 데이터를 addTask/initLocation/setTask 등이 DEVICE_TASK_TABLE 로 읽는다.

원본은 다수의 텔레메트리(레이더/엔코더/위치/오차)도 파싱하나, 다른 서비스가
실제 소비하는 핵심 필드 위주로 이식한다(오프셋은 원본과 동일).
"""
from __future__ import annotations

import logging

from app.core import redis_constants as rc
from app.tcp import byte_process as bp
from app.utils.redis_util import redis_util

LOGGER = logging.getLogger('app')


def parse_memory_table(reb: bytes) -> dict:
    """하트비트 프레임 → 메모리테이블 dict (원본 바이트 오프셋)."""
    imei = bp.bytes_to_int(bp.split_byte(reb, 8, 12), 4)
    user_task_id = bp.bytes_to_int(bp.split_byte(reb, 4, 8), 4)
    flag = bp.print_hex_string(bp.split_byte(reb, 14, 15))
    flag_byte = bp.bytes_to_int(bp.hex_string_to_bytes(flag), 1)
    model = flag_byte >> 6
    start_site_code = bp.bytes_to_int(bp.split_byte(reb, 15, 18), 3)
    end_site_code = bp.bytes_to_int(bp.split_byte(reb, 18, 21), 3)
    steps = bp.bytes_to_int(bp.split_byte(reb, 21, 24), 3)
    fork_height = bp.bytes_to_int(bp.split_byte(reb, 25, 27), 2)
    task_number = bp.bytes_to_int(bp.split_byte(reb, 27, 29), 2)
    battery_level = bp.bytes_to_int(bp.split_byte(reb, 29, 30), 1)
    fork_status = bp.bytes_to_int(bp.split_byte(reb, 30, 31), 1) & 3
    task_flag = (bp.bytes_to_int(bp.split_byte(reb, 31, 32), 1) >> 4) & 0xFF
    self_consistent = bp.bytes_to_int(bp.split_byte(reb, 120, 121), 1)
    lock_state = (self_consistent >> 3) & 1
    button_number = bp.bytes_to_int(bp.split_byte(reb, 127, 129), 2)
    wifi_strength = bp.bytes_to_int(bp.split_byte(reb, 148, 149), 1)
    floor = bp.bytes_to_int(bp.split_byte(reb, 151, 152), 1)

    return {
        "deviceImei": imei,
        "userTaskId": user_task_id,
        "flag": flag,
        "model": model,
        "startSiteCode": start_site_code,
        "endSiteCode": end_site_code,
        "steps": steps,
        "forkHeight": fork_height,
        "taskNumber": task_number,
        "batteryLevel": battery_level,
        "forkStatus": fork_status,
        "taskFlag": task_flag,
        "lockState": lock_state,
        "buttonNumber": button_number,
        "wifiStrength": wifi_strength,
        "floor": floor,
    }


async def save_or_update_device(reb: bytes) -> dict:
    """원본 saveOrUpdateDevice: 파싱 후 Redis 저장.

    저장:
      - DEVICE_HEART_BEAT+imei = 원본 HEX (3초 TTL)
      - deviceTable_suc_+imei = 메모리테이블
      - DEVICE_TASK_TABLE+imei = 메모리테이블 (소비처가 읽는 키)
    """
    table = parse_memory_table(reb)
    imei = table["deviceImei"]
    await redis_util.set_to_json(f"{rc.DEVICE_HEART_BEAT}{imei}", bp.print_hex_string(reb), 3)
    await redis_util.set_to_str(f"{rc.DEVICE_TABLE_PREXFIX}{imei}", table)
    await redis_util.set_to_str(f"{rc.DEVICE_TASK_TABLE}{imei}", table)
    return table
