"""웹 폼 공통 베이스.

원본 com.ygcloud.ygcommon.web.BaseUserWebForm 의 check() 대체.
원본 check(): @Validation(notes=...) 가 붙은 필드가 비어있으면 그 notes 메시지로
JsonResult.fail("1", notes) 를 반환한다. userName 필드(조작자)를 공통 보유한다.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.core.jsonresult import JsonResult


class BaseForm(BaseModel):
    userName: str | None = None
    userId: str | None = None

    # 하위 폼에서 [(필드명, 비었을 때 메시지), ...] 로 필수 검증 정의
    _validations: tuple[tuple[str, str], ...] = ()

    def check(self) -> JsonResult:
        for field, notes in self._validations:
            value = getattr(self, field, None)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                return JsonResult.fail("1", notes)
        return JsonResult.success()

    def param_to_string(self) -> str:
        data = {k: v for k, v in self.model_dump().items() if v is not None}
        return f"{self.__class__.__name__}({data})"
