#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""快手快速验证：登录后发布一条私密图文或视频。

用户只需修改本文件顶部的配置，然后运行 ``python quick_publish.py``。
脚本不读取浏览器、不保存 Cookie/Token/验证码；发布默认仅自己可见。
图文请求继续使用已验证的 ``image/png`` 合同；常见图片由底层发布 API 临时转成
PNG，视频则按视频上传链路原文件发送。
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from builder.auth import KuaishouAuth
from ks_apis.publish_api import KuaishouPublishAPI as Publish


# Read an optional local .env without ever writing credentials back to disk.
load_dotenv()


# ============================== 用户配置 ============================== #
# 直接修改下面几项，然后运行：python quick_publish.py
LOGIN_MODE = "qr"                 # "qr"、"phone" 或 "cookie"
MEDIA_TYPE = "auto"               # "auto"、"image" 或 "video"
# 改成自己的图片或视频路径；auto 会按扩展名识别类型。
MEDIA_PATH = r"D:\media\cover.jpg"
CAPTION = ""                      # 视频当前必须为空
PHONE = ""                        # 手机号登录；留空时运行中输入
SMS_CODE = ""                     # 留空时运行中输入，不写入文件
COOKIES = ""                      # 可选：本地 CK；不要提交或公开
QR_PATH = "qrcode.png"            # 二维码临时文件，流程结束自动删除


def _validate_config() -> None:
    if LOGIN_MODE not in {"qr", "phone", "cookie"}:
        raise ValueError("LOGIN_MODE 必须是 qr、phone 或 cookie")
    if MEDIA_TYPE not in {"auto", "image", "video"}:
        raise ValueError("MEDIA_TYPE 必须是 auto、image 或 video")
    if not str(MEDIA_PATH).strip():
        raise ValueError("MEDIA_PATH 不能为空")
    path = Path(MEDIA_PATH).expanduser()
    if not path.is_file():
        raise ValueError(f"MEDIA_PATH 文件不存在：{path}")


def login() -> KuaishouAuth:
    auth = KuaishouAuth()
    if LOGIN_MODE == "cookie":
        cookie = (COOKIES or os.environ.get("KS_COOKIES", "")).strip()
        if not cookie:
            raise RuntimeError("COOKIE 模式需要填写顶部 COOKIES，或设置环境变量 KS_COOKIES")
        print("正在用本地 CK 初始化会话……")
        auth.initialize(cookie)
        return auth

    if LOGIN_MODE == "phone":
        phone = (PHONE or input("手机号：")).strip()
        if not phone:
            raise RuntimeError("手机号不能为空")
        print("正在初始化设备和 webweapon……", flush=True)
        auth.initialize("", login_if_empty=False)
        print("正在申请短信验证码……", flush=True)
        response = auth.request_mobile_code(phone)
        print(f"短信申请返回 result={response.get('result')!r}", flush=True)
        if response.get("result") != 1:
            raise RuntimeError(
                f"短信申请失败 result={response.get('result')!r}；请检查官方页面风控提示")
        code = (SMS_CODE or input("短信验证码：")).strip()
        if not code:
            raise RuntimeError("短信验证码不能为空")
        print("正在提交验证码并初始化业务会话……", flush=True)
        auth.login_by_mobile_code(phone, code)
        print("手机号登录完成。", flush=True)
        return auth

    qr_path = str(Path(QR_PATH).expanduser().resolve())
    print("正在申请二维码；请用快手 App 扫描下方文件：")
    try:
        auth.initialize(
            "", qr_path=qr_path, timeout=600.0,
            on_qr=lambda path, url: print(
                f"二维码：{Path(path).resolve()}\n二维码 URL：{url}", flush=True),
        )
    finally:
        # 二维码只在等待扫码期间存在，完成或失败后都不留在仓库。
        try:
            Path(qr_path).unlink(missing_ok=True)
        except OSError:
            pass
    return auth


def publish(auth: KuaishouAuth) -> dict:
    path = Path(MEDIA_PATH).expanduser().resolve()
    print(f"上传并发布媒体：{path}")
    return Publish.publish_media_file(
        auth, str(path), caption=CAPTION, media_type=MEDIA_TYPE,
        photo_status=Publish.PHOTO_STATUS_PRIVATE, publish_time=0,
        on_progress=lambda done, total: print(f"  进度 {done}/{total}"),
    )


def main() -> int:
    try:
        print(f"使用脚本：{Path(__file__).resolve()}")
        _validate_config()
        auth = login()
        print("登录成功，正在执行 CP 发布权限检查……")
        result = publish(auth)
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
    except Exception as exc:  # noqa: BLE001
        print(f"快速验证失败：{type(exc).__name__}: {exc}")
        return 1

    print(f"发布完成：result={result.get('result')!r}（默认仅自己可见）")
    if result.get("result") != 1:
        print(result)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
