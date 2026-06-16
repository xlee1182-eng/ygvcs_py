"""User 요청 폼 (Pydantic).

원본 webservice.form.user.UserLoginForm / UserEditForm 의 대체.
원본 @Validation(notes=...) 는 "필수값 검증"이며, 실패 시 JsonResult.fail 을 돌려준다.
여기서는 Pydantic 검증 + 원본과 동일한 check() 동작을 함께 제공한다.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.jsonresult import JsonResult


class UserLoginForm(BaseModel):
    """사용자 로그인 (用户登录)."""

    # userName: str | None = Field(default=None, description="用户名")
    userName: str | None = Field(default=None, description="사용자명")
    # password: str | None = Field(default=None, description="密码")
    password: str | None = Field(default=None, description="비밀번호")

    def check(self) -> JsonResult:
        # 원본 @Validation: 사용자명/비밀번호 필수
        if not self.userName:
            # return JsonResult.fail("1", "用户名不能为空")
            return JsonResult.fail("1", "사용자명은 비어있을 수 없습니다")
        if not self.password:
            # return JsonResult.fail("1", "密码不能为空")
            return JsonResult.fail("1", "비밀번호는 비어있을 수 없습니다")
        return JsonResult.success()

    def param_to_string(self) -> str:
        return f"UserLoginForm(userName={self.userName})"


class UserEditForm(BaseModel):
    """비밀번호 수정 (修改密码)."""

    # userName: str | None = Field(default=None, description="用户名")
    userName: str | None = Field(default=None, description="사용자명")
    # password: str | None = Field(default=None, description="旧密码")
    password: str | None = Field(default=None, description="기존 비밀번호")
    # newPassword: str | None = Field(default=None, description="新密码")
    newPassword: str | None = Field(default=None, description="새 비밀번호")

    def check(self) -> JsonResult:
        if not self.userName:
            # return JsonResult.fail("1", "用户名不能为空")
            return JsonResult.fail("1", "사용자명은 비어있을 수 없습니다")
        if not self.password:
            # return JsonResult.fail("1", "旧密码不能为空")
            return JsonResult.fail("1", "기존 비밀번호는 비어있을 수 없습니다")
        if not self.newPassword:
            # return JsonResult.fail("1", "新密码不能为空")
            return JsonResult.fail("1", "새 비밀번호는 비어있을 수 없습니다")
        return JsonResult.success()

    def param_to_string(self) -> str:
        return f"UserEditForm(userName={self.userName})"
