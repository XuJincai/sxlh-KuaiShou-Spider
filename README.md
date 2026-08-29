<div align="center">

# 🎵 KuaiShou-Spider

<a href="https://www.python.org/">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python 3.10+">
</a>
<a href="https://nodejs.org/">
  <img src="https://img.shields.io/badge/nodejs-18%2B-green" alt="Node.js 18+">
</a>
<a href="https://github.com/cv-cat/KuaiShou-Spider">
  <img src="https://img.shields.io/badge/transport-Chrome%20TLS%2FHTTP-orange" alt="Chrome TLS/HTTP transport">
</a>

**快手 Web 数据采集、直播监听与创作者发布的纯代码客户端**

</div>

## 为什么需要这个项目？

快手 Web 端没有提供覆盖完整运营场景的公开接口。数据采集、直播间实时消息和
创作者发布都依赖一组会随页面状态变化的 Cookie、设备指纹、签名和上传流程。

本项目把这些浏览器请求收敛为一个 Python 会话：二维码登录或用户 CK 进入
`KuaishouAuth` 后，www 和 CP 请求共享正确的会话状态；Live 站点仍需按当前页面
合同单独刷新专属票据。短期 webweapon
Cookie、设备票据、`__NS_hxfalcon`、`__NS_sig3`/`sig4` 和上传 ID 都由当前进程
实时生成。业务请求不启动浏览器、不读取浏览器配置目录，也不复制 Chrome Cookie。

```text
二维码 / 用户 CK
        │
        ▼
  KuaishouAuth  ──► www 数据接口
        │          ├► Live REST + WebSocket（弹幕 / 礼物监听）
        │          └► CP 上传 / 审核 / 发布
        │
        └──► webweapon、设备指纹、TLS/HTTP、Cookie 与签名状态
```

**⚠️ 本项目仅供学习、测试和技术研究使用。请遵守快手平台规则与当地法律，
不要用于骚扰、批量刷量、绕过风控或发布违法违规内容。上传和发布接口会产生
真实外部副作用，请只对自己有权操作的账号和素材使用。**

## ✨ 已实现功能

| 模块 | 功能 | 状态 |
|------|------|------|
| **统一认证** | 用户 CK 初始化 | ✅ |
| | 程序内二维码登录、www/CP 会话初始化 | ✅ |
| | Live 专属会话刷新 | ✅ 监听前自动补齐 |
| | 会话导出、恢复和短期 webweapon Cookie 续期 | ✅ |
| **www 数据** | 作品详情、短视频详情（已知作品链接或 photoId） | ✅ |
| | 推荐流自动发现 | ⚠️ 当前线上 feed/hot 可能返回 400，需按版本重新取证 |
| | 用户主页、作品列表、喜欢/收藏/私密列表 | ⚠️ 部分用户页合同受当前 Network 证据限制 |
| | 搜索作品、搜索用户、评论和分页 | ✅ |
| | 点赞数据及其动态令牌 | ✅ |
| **直播 Live** | 首页房间发现、房间状态、主播资料 | ✅ |
| | 礼物、表情、评论列表等 REST 数据 | ✅ |
| | WebSocket 实时接收弹幕、礼物、点赞和系统通知 | ✅ |
| | 心跳、断线重连、protobuf 编解码 | ✅ |
| | 发送直播间弹幕 | ⏳ 当前版本未接入 |
| **创作者 CP** | 创作者权限检查 | ✅ |
| | 视频 `resume → fragment → complete` 上传并发布 | ✅ |
| | 单张图文上传、审核并发布（网络统一 PNG 合同） | ✅ |
| | 多图、多分片图文上传 | ⛔ 当前版本按合同门禁拒绝；底层单图入口会统一把非 PNG 图片转为 PNG |
| **传输与安全** | Chrome 风格 TLS/HTTP、请求头和 Cookie 顺序 | ✅ |
| | `kww` / `kwfv1` / `kwscode` / `kwssectoken` 动态生成 | ✅ |
| | 未取证接口 fail-closed，不猜字段、不重放登录态 | ✅ |

## 🛠️ 快速开始

### 运行环境

- Python 3.10+
- Node.js 18+
- 建议使用 `curl_cffi` 提供的 Chrome TLS/HTTP 传输

### 安装依赖

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1

pip install -r requirements.txt
```

Node.js 只用于执行仓库内必要的 webweapon/令牌桥接脚本，不需要 `npm install`。

### 配置登录

复制配置模板：

```powershell
Copy-Item .env.example .env
```

有自己的登录 CK 时，在 `.env` 填入完整 Cookie：

```dotenv
KS_COOKIES='did=...; userId=...; kuaishou.server.webday7_st=...'
```

也可以不填 `KS_COOKIES`，由程序申请二维码并等待手机确认。登录入口会在同一个
`KuaishouAuth` 对象中完成扫码回调、www/CP STS、文档引导和设备指纹初始化。

```python
from builder.auth import KuaishouAuth
from ks_apis.kuaishou_api import KuaishouAPI

# 有 CK：直接恢复并按需续期 webweapon Cookie
auth = KuaishouAuth().initialize("did=...; userId=...; ...")

# 无 CK：申请二维码并等待扫码
# auth = KuaishouAuth().initialize("")

feed = KuaishouAPI.get_feed_hot(auth)
print(feed)
```

也支持手机号验证码登录。先由程序申请短信（遇到官方验证码/风控挑战时，
请在快手页面完成验证），再把用户自己收到的验证码传入同一个 `auth` 对象；
登录接口会自动接着完成 www/CP STS、文档 Cookie 和设备指纹初始化：

```python
from builder.auth import KuaishouAuth

auth = KuaishouAuth().initialize("", login_if_empty=False)
auth.request_mobile_code(phone="你的手机号")
sms_code = input("输入短信验证码（不会写入仓库）: ").strip()
auth.login_by_mobile_code(phone="你的手机号", sms_code=sms_code)
```

手机号、短信验证码、Cookie 和登录票据只应由调用者在本地提供；不要写入 Git、
日志或公开 issue。

登录成功后可以保存程序自己的状态（不要提交到 Git）：

```python
state = auth.export_state()
auth2 = KuaishouAuth().initialize_state(state)
```

### 快速验证：扫码/手机号登录后发布一条作品

根目录的 `quick_publish.py` 是最小可运行示例。先编辑文件顶部的“用户配置”区，
再直接运行脚本；不需要记命令行参数。它只使用项目自己的请求、签名、webweapon
和上传链，不启动浏览器。发布默认是“仅自己可见”，但仍然会产生真实上传和发布
副作用，请只使用自己的账号与素材。

```python
# quick_publish.py 顶部配置示例
LOGIN_MODE = "qr"                 # qr / phone / cookie
MEDIA_TYPE = "auto"               # auto、image 或 video
MEDIA_PATH = r"D:\\media\\cover.jpg"
CAPTION = ""
```

改完后运行：

```bash
python quick_publish.py
```

`MEDIA_TYPE="auto"` 会按常见扩展名、MIME 和文件头识别图片或视频；图文 API 会在上传链
内部把非 PNG 图片临时转换为 PNG，然后按已验证的 `image/png` 合同上传，转换文件会在
请求结束后删除。demo 本身不处理 MIME 或转换逻辑，业务代码直接调用
`publish_atlas_images` 时也会得到同样的行为。
如果是无法识别扩展名的素材，可直接把 `MEDIA_TYPE` 改成 `image` 或 `video`；视频会按原
文件走视频上传链路（容器是否被快手接受仍由服务端决定）。手机号登录时填写顶部 `PHONE`；
`SMS_CODE` 留空则在终端交互输入。Cookie 登录时可
填写顶部 `COOKIES`，也可以使用环境变量 `KS_COOKIES`。这些值只应保存在本地，
不要提交到 Git。脚本会在扫码等待期间生成临时 `qrcode.png`，结束后自动删除。当前已验证的
发布合同是单张图文（统一为 PNG）以及空描述、立即发布、仅自己可见的视频；多图、公开视频
和视频自定义描述仍会在出网前明确拒绝。

### 运行数据采集示例

```bash
python main.py
```

`main.py` 是最小入口示例，会把媒体和 Excel 输出到本地 `datas/` 目录；该目录
属于运行时输出，不纳入清理分支。由于当前 `feed/hot` 合同在部分线上会返回 400，
首次运行可能需要改用已知作品详情或搜索示例。实际项目中可直接调用 `KuaishouAPI`，
按需选择推荐、搜索、个人页、作品详情和评论接口。

### 监听直播间弹幕和礼物

```python
from builder.auth import KuaishouAuth
from ks_apis.login_api import KuaishouLoginAPI, SID_LIVE
from ks_apis.live_api import KuaishouLiveAPI
from ks_apis.live_ws import LiveDanmakuClient

auth = KuaishouAuth().initialize("did=...; userId=...; ...")
if not KuaishouLoginAPI.refresh_site_session(
        auth, SID_LIVE, KuaishouLiveAPI.live_url):
    raise RuntimeError("Live 会话刷新失败")

client = LiveDanmakuClient(auth, eid="直播间 eid")
client.on("SC_FEED_PUSH", lambda message: print(message["payload"]))
client.run()                 # 一直监听；也可传 duration=300
```

客户端会自动完成房间发现、WebSocket 握手、进房、心跳、protobuf 解码和有限次
重连。`SC_FEED_PUSH` 的 payload 中包含评论、礼物、点赞等数组。若服务端返回
`result=2`，表示账号或 IP 处于直播风控状态，需要先在官方页面完成验证；这不是
客户端可以通过伪造字段解决的普通签名错误。

二维码登录自动补齐 www/CP 会话，但当前 Live 首页使用独立的站点票据。
`LiveDanmakuClient.prepare()` 会在监听前自动检查并刷新
`kuaishou.live.web_st` / `kuaishou.live.web_ph`；也可以直接提供包含 Live 票据的完整 CK。
如果业务代码需要提前显式刷新，仍可调用
`KuaishouLoginAPI.refresh_site_session(auth, SID_LIVE, KuaishouLiveAPI.live_url)`。

### 纯代码上传并发布

业务代码可以直接调用 `KuaishouPublishAPI` 的 `publish_media_file`，由底层自动选择
图文或视频链路；也可以分别调用 `publish_video_file` 或 `publish_atlas_images`。
根目录 `quick_publish.py` 只是这个统一入口的薄示例，展示登录、CP 会话切换、权限检查、
上传、审核和提交链路；不会保存登录态或测试素材。

## 🔐 认证与浏览器请求对齐

### 一个 Auth 管理所有站点状态

`KuaishouAuth` 负责：

- www、Live、CP 和 onvideo 的站点切换与 Cookie 页面状态；
- `did`、`didv`、服务端 `wid` 等设备票据；
- 当前页面冻结的 `kww` 与 Cookie 中 `kwfv1` 的独立生命周期；
- 6 分钟有效的 `kwscode`、`kwssectoken` 续期；
- 登录状态导出/恢复，以及服务端 Set-Cookie 的有序合并。

用户显式提供的 Cookie 始终优先；没有 Cookie 时只通过官方二维码登录流程取得
服务端会话。项目不会根据 Cookie 猜造 `wid`，也不会把一个站点的 Cookie 直接
复用到另一个站点。

### webweapon 与签名

`/s/w/c` 返回本次会话指定的脚本地址和 `secToken`，Node 桥接脚本执行官方
webweapon 代码，产出 `kwfv1`、`kwscode` 和 `kwssectoken`。签名层按接口分别使用
`__NS_hxfalcon`、`__NS_sig3` 或 `sig4`；缺少当前成功请求证据的变体会在出网前
拒绝，而不是使用旧字段“试一下”。这里的“纯代码”指不依赖 Chrome/浏览器页面；
webweapon 本身仍需要 Node.js 执行官方 JS，不能表述为纯 Python 算法实现。

### HTTP/TLS 与 Cookie

传输层使用 `curl_cffi` 的 Chrome impersonation，并保留当前请求实际需要的
`Origin`、`Referer`、`Accept`、`Content-Type`、`Content-Length`、Cookie 顺序和
站点专属 webweapon profile。Live WebSocket 还会发送正确的 Origin 和 User-Agent。

## 📁 项目结构

```text
KuaiShou-Spider/
├── builder/
│   ├── auth.py                 # 统一认证、Cookie 和页面状态
│   ├── header.py               # 浏览器风格请求头
│   └── params.py               # query/body/签名参数
├── ks_apis/
│   ├── kuaishou_api.py         # www 数据接口
│   ├── live_api.py             # Live REST 接口
│   ├── live_ws.py              # Live 弹幕/礼物 WebSocket
│   ├── login_api.py            # 二维码、STS、设备指纹
│   └── publish_api.py          # CP 上传、审核和发布
├── utils/
│   ├── transport.py            # TLS/HTTP 传输
│   ├── live_proto.py           # Live protobuf 编解码
│   ├── ksuploader.py           # 分片上传器
│   ├── gdfp_*.py               # 设备指纹上报
│   └── sign/                   # webweapon、sig3、falcon 等签名
├── quick_publish.py            # 登录后发布一条私密图文或视频的快速验证
├── reverse/
│   ├── bundles/weapon/         # 运行时需要的官方 webweapon 变体
│   ├── js/cp-kwf.js            # CP kwf 运行时脚本
│   ├── fixtures/               # Live 协议和令牌预言机所需脱敏证据
│   └── tools/                  # webweapon/令牌 Node 桥
├── main.py                     # 数据采集入口示例
├── .env.example                # 登录配置模板
├── requirements.txt
└── README.md
```

## 🧹 清理分支说明

`feat/kuaishou` 只保留运行所需源码、脱敏协议材料和 webweapon 资产。旧的发布
测试脚本、会话快照、临时二维码、测试媒体和本地 IDE 配置不属于仓库内容。

本地的 `.venv`、`node_modules` 和 `reverse/secrets` 不属于提交内容：前两者是
运行依赖，后者可能包含用户自己的会话 Cookie，均由 `.gitignore` 排除。发布前
请检查 `git status --ignored`，确认没有把这些文件强制加入版本库。

## 🗝️ 注意事项

- Cookie 具有时效性；失效后请重新输入 CK 或重新扫码。
- 运行发布示例前，确认素材路径、账号和可见性，发布请求不可视为离线测试。
- 单张图文（网络统一为 PNG）是当前验证过的稳定分支；多图和未取证格式会主动拒绝。
- 直播监听依赖房间当前在播、WebSocket token 和账号/IP 风控状态。
- 当前版本没有发送直播间弹幕接口；WebSocket 仅负责接收弹幕、礼物和点赞。
- 不要把 `.env`、二维码、`reverse/secrets`、浏览器 Cookie 或原始抓包上传到公共仓库。
- 平台接口可能随前端版本变化；遇到合同漂移时应重新抓取并更新实现，不要放宽门禁。

## 🍥 更新日志

| 日期 | 说明 |
|------|------|
| 2026-08-29 | 整理 `feat/kuaishou` 运行分支，加入根目录 `quick_publish.py` 快速验证示例，移除会话快照和旧测试脚本。 |
| 2026-08-29 | 完成 Python 二维码登录、www/CP 会话、设备指纹、视频发布和单张图文发布链路。 |
| 2026-08-28 | 接入 Live WebSocket protobuf 解码、弹幕/礼物/点赞监听、心跳和断线重连。 |
| 2026-08-27 | 完成 webweapon、TLS/HTTP、Cookie 顺序和多站点 Auth 状态对齐。 |

## 🤝 贡献

欢迎提交文档改进、兼容性修复和新的脱敏请求合同。请不要提交账号 Cookie、二维码、
会话状态或未经脱敏的浏览器抓包；涉及真实发布接口的改动请同时说明副作用和验证
范围。
