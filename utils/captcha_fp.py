#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""滑块验证码的浏览器指纹块（``gpuInfo`` / ``captchaExtraParam``）。

这两个字段在 ``captcha-iframe.js`` 的提交处是（webpack 模块 ``998f``）::

    gpuInfo:           JSON.stringify(Object(Gt["b"])()),
    captchaExtraParam: JSON.stringify(i)          // i = await Ga()

两者都已用 CDP 在真实浏览器的验证码 iframe 页里**直接调到原函数取回真值**
（做法见本模块末尾的「怎么重新抓」）。

--------------------------------------------------------------------------
gpuInfo（4 键）
--------------------------------------------------------------------------
采集器 ``Yc = rc("webglGpu", …)`` 在 bundle 里是明文的::

    var r = { glRenderer:     gl.getParameter(gl.RENDERER),
              glVendor:       gl.getParameter(gl.VENDOR),
              unmaskRenderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "",
              unmaskVendor:   ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL)   : "" };

注意 ``glRenderer`` / ``glVendor`` 是 WebKit 的通用脱敏值，真显卡型号在
``unmask*`` 里（走 ``WEBGL_debug_renderer_info`` 扩展）。

--------------------------------------------------------------------------
captchaExtraParam（65 键，约 2.7KB）
--------------------------------------------------------------------------
``Ga()`` 合并两个采集源，并对命中 ``Ua`` 别名表的键**同一个值存两份**
（所以你会看到 ``canvasGraphFingerPrint`` 与 ``canvasGraph`` 恒等，共 12 对）::

    t = await ua(); c = await va.<collect>(); a = {};
    Object.entries(t).forEach(([k,v]) => { if (k in Ua) a[Ua[k]] = v; a[k] = v; });
    Object.entries(c).forEach(([k,v]) => { a[k] = v; });

各段含义（实测归纳）：

===================  ==========================================================
键                    含义
===================  ==========================================================
ua / userAgent        UA（一个值两份，别名对）
timeZone              形如 ``UTC+8``
cpuCoreCnt            ``navigator.hardwareConcurrency``，**字符串**
riskBrowser 等 6 项   自动化检测结论，正常浏览器全是 ``"false"`` 字符串
plugins               插件列表的哈希
canvas*/webgl*/font*  各类指纹哈希，**统一是 1 + 32 位 hex 的 33 字符**
                      （前导 "1" 是版本位），每对两份
nativeFunc            原生函数完整性校验的哈希
key1                  ``did``（与 cookie 里的 did 一致）
key2                  ``Date.now()`` 毫秒
key3..key6            UA / productSub / language / product
key7..key14           屏幕与窗口尺寸：screenW/H、availW/H、innerH、outerW/H…
key15                 ``"00000111"`` 能力位掩码
key18..key25          各阶段事件耗时（``"0,103,-1,-1,-1,prepare1"`` 这种）
key26                 鼠标/触摸轨迹汇总（key27 是主轨迹数组）
key35/key36           会话级哈希
key37/key38/key39     ``1`` / ``"not support"`` / 逻辑核数
===================  ==========================================================

**指纹哈希与设备强绑定**：默认值取自 2026-08-16 的实测机器（RTX 5060 Ti /
2560x1440 / 20 核）。换机器跑**必须重抓**，否则指纹与其它信号（UA、分辨率）
自相矛盾，反而更容易被判异常。
"""

from __future__ import annotations

import json
import random
import time

# --------------------------------------------------------------------------- #
# 真实浏览器实测值（CDP @ captcha.zt.kuaishou.com/iframe/index.html，2026-08-16）#
# --------------------------------------------------------------------------- #
GPU_INFO = {
    "glRenderer": "WebKit WebGL",
    "glVendor": "WebKit",
    "unmaskRenderer": ("ANGLE (NVIDIA, NVIDIA GeForce RTX 5060 Ti (0x00002D04) "
                       "Direct3D11 vs_5_0 ps_5_0, D3D11)"),
    "unmaskVendor": "Google Inc. (NVIDIA)",
}

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.36")

# Ga() 的完整产物。键序即 JSON.stringify 的输出序，不要重排。
CAPTCHA_EXTRA_PARAM = {
    "ua": _UA,
    "userAgent": _UA,
    "timeZone": "UTC+8",
    "language": "zh-CN",
    "cpuCoreCnt": "20",
    "platform": "Win32",
    # 自动化检测结论：正常浏览器全是字符串 "false"
    "riskBrowser": "false",
    "webDriver": "false",
    "exactRiskBrowser": "false",
    "webDriverDeep": "false",
    "exactRiskBrowser2": "false",
    "webDriverDeep2": "false",
    "battery": "1",
    "plugins": "1a68ba429dd293b14e41a28b6535aa590",
    "resolution": "2560x1440",
    "pixelDepth": "24",
    "colorDepth": "24",
    # 下面这些成对出现的就是 Ua 别名表（同值两份），共 12 对
    "canvasGraphFingerPrint": "1109b083cc4701a442fe7846d074394f1",
    "canvasGraph": "1109b083cc4701a442fe7846d074394f1",
    "canvasTextFingerPrintEn": "12e6f0f06266fb6bc7b5ddb5be6c0be3e",
    "canvasTextEn": "12e6f0f06266fb6bc7b5ddb5be6c0be3e",
    "canvasTextFingerPrintZh": "1cfe96b611a4ada0f3ed6c5d9da0eb406",
    "canvasTextZh": "1cfe96b611a4ada0f3ed6c5d9da0eb406",
    "webglGraphFingerPrint": "1537e3a006691fc8474abd41438c08a5d",
    "webglGraph": "1537e3a006691fc8474abd41438c08a5d",
    "webglGPUFingerPrint": "1192e522040bbe560567d4321fed3c16a",
    "webglGpu": "1192e522040bbe560567d4321fed3c16a",
    "cssFontFingerPrintEn": "1e4c353075d9fe0c911b00a7f7dba2f26",
    "fontListEn": "1e4c353075d9fe0c911b00a7f7dba2f26",
    "cssFontFingerPrintZh": "154ef9bb94c26d3f7b091868f7a41c387",
    "fontListZh": "154ef9bb94c26d3f7b091868f7a41c387",
    "voiceFingerPrint": "1dd96cac4e826abdbbe261dc4f3a08292",
    "audioTriangle": "1dd96cac4e826abdbbe261dc4f3a08292",
    "nativeFunc": "1973dcbb27a04c3a2ee240d9d2549e105",
    # Placeholder only; every request replaces key1 with the session did.
    # Keep no captured device identifier in the published source tree.
    "key1": "web_" + "0" * 32,
    "key2": 1786880034017,                              # Date.now()，运行时会被替换
    "key3": _UA,
    "key4": "20030107",                                 # navigator.productSub
    "key5": "zh-CN",
    "key6": "Gecko",                                    # navigator.product
    "key7": 2560, "key8": 1440,                         # screen.width / height
    "key9": 2560, "key10": 1392,                        # availWidth / availHeight
    "key11": 1215,                                      # innerHeight
    "key12": 2560, "key13": 1392,                       # outerWidth / outerHeight
    "key14": 2560,
    "key15": "00000111",                                # 能力位掩码
    "key16": 1, "key17": 1,
    "key18": ["0,103,-1,-1,-1,prepare1"],
    "key19": {"prepare1": "0,103,-1,-1,-1"},
    "key20": ["0,102,-1,-1,-1,prepare1"],
    "key21": {"prepare1": "0,102,-1,-1,-1"},
    "key22": ["0,102,-1,-1,-1,prepare1"],
    "key23": {"prepare1": "0,102,-1,-1,-1"},
    "key24": ["0,102,-1,-1,-1,prepare1"],
    "key25": {"prepare1": "0,102,-1,-1,-1"},
    "key26": {
        "key27": [
            "0,1,40012,1310,169,prepare1", "1,1,40015,1305,153,prepare1",
            "2,1,40017,1301,140,prepare1", "3,1,40022,1293,119,prepare1",
            "4,1,40026,1284,93,prepare1", "5,1,40030,1278,75,prepare1",
            "6,1,40033,1275,66,prepare1", "7,1,41016,-1,-1,prepare1",
            "8,1,41017,-1,-1,prepare1", "9,1,41022,1385,2,prepare1",
        ],
        "key28": [], "key29": [], "key30": [],
        "key31": {"prepare1": "9,1,41022,1385,2"},
        "key32": {}, "key33": {}, "key34": {},
    },
    "key35": "53b4153471329902b90af6e81a017253",
    "key36": "f22a94013fc94e90e2af2798023a1985",
    "key37": 1,
    "key38": "not support",
    "key39": 20,                                        # 逻辑核数
}


def _session_fields(now_ms: int) -> dict:
    """产出**每次验证都要重算**的会话相关字段。

    这些字段在真实浏览器里是当次采集的，不是常量：

    - ``key18`` ~ ``key25``：各阶段事件耗时（毫秒），四组「数组 + 同值 dict」；
    - ``key26.key27``：鼠标/触摸轨迹数组，格式
      ``"<序号>,<按键>,<时间戳低位>,<x>,<y>,prepare1"``；
    - ``key26.key31``：轨迹的最后一条（同格式，不带序号前缀的那份）；
    - ``key35`` / ``key36``：会话级 32 位 hex 哈希。

    **原样重放上次采集的值 = 每次验证的鼠标轨迹一模一样**，服务端一比就知道是回放，
    直接回 ``350014 anti check err``。实测把这些改成每次现算之后才有戏。

    :param now_ms: 当次的毫秒时间戳（与 key2 保持一致）。
    """
    rnd = random.Random(now_ms ^ random.getrandbits(32))

    def _hex32() -> str:
        return "".join(rnd.choice("0123456789abcdef") for _ in range(32))

    # 事件耗时：真实值在 100ms 上下浮动
    def _timing() -> tuple:
        cost = rnd.randint(88, 132)
        s = f"0,{cost},-1,-1,-1"
        return [s + ",prepare1"], {"prepare1": s}

    k18, k19 = _timing()
    k20, k21 = _timing()
    k22, k23 = _timing()
    k24, k25 = _timing()

    # 鼠标轨迹：进验证码 iframe 后的移动采样。
    # 真实样本形如 "0,1,40012,1310,169,prepare1"，
    # 字段是 序号,按键状态,时间戳低位,x,y。
    base_t = rnd.randint(38000, 46000)
    x, y = rnd.randint(1240, 1400), rnd.randint(120, 210)
    track = []
    for i in range(rnd.randint(8, 14)):
        base_t += rnd.randint(2, 9)
        x += rnd.randint(-9, 3)
        y += rnd.randint(-22, 6)
        if i >= 7 and rnd.random() < 0.4:
            # 真实样本里中间有几条 x/y 是 -1（元素外/未捕获）
            track.append(f"{i},1,{base_t},-1,-1,prepare1")
        else:
            track.append(f"{i},1,{base_t},{x},{y},prepare1")
    last = track[-1].rsplit(",", 1)[0]
    last = ",".join(last.split(",")[0:])          # 保持同格式

    return {
        "key18": k18, "key19": k19,
        "key20": k20, "key21": k21,
        "key22": k22, "key23": k23,
        "key24": k24, "key25": k25,
        "key26": {
            "key27": track,
            "key28": [], "key29": [], "key30": [],
            "key31": {"prepare1": last},
            "key32": {}, "key33": {}, "key34": {},
        },
        "key35": _hex32(),
        "key36": _hex32(),
    }


def gpu_info_json(overrides: dict = None) -> str:
    """产出 ``gpuInfo`` 字段的值（JSON 字符串，键序与采集器一致）。

    :param overrides: 换机器时覆盖其中若干键。
    """
    info = dict(GPU_INFO)
    info.update(overrides or {})
    ordered = {k: info[k] for k in ("glRenderer", "glVendor",
                                    "unmaskRenderer", "unmaskVendor")
               if k in info}
    for key, value in info.items():
        ordered.setdefault(key, value)
    return json.dumps(ordered, separators=(",", ":"), ensure_ascii=False)


def captcha_extra_param_json(overrides: dict = None, did: str = "",
                             now_ms: int = None, fresh_session: bool = True) -> str:
    """产出 ``captchaExtraParam`` 字段的值（JSON 字符串）。

    :param overrides: 覆盖若干键（换机器时把重抓到的指纹整体传进来）。
    :param did: 设备标识；给了就替换 ``key1``，保证与 cookie 里的 did 一致。
    :param now_ms: 毫秒时间戳，默认取当前时间（对应 ``key2``）。
    :param fresh_session: 是否重算会话相关字段（key18~key26 事件耗时与鼠标轨迹、
        key35/key36 会话哈希）。**默认开**——原样重放同一串轨迹会被判成回放，
        实测服务端直接回 ``350014 anti check err``。只做对拍复现时才关掉。
    """
    data = dict(CAPTCHA_EXTRA_PARAM)
    stamp = int(time.time() * 1000) if now_ms is None else int(now_ms)
    if did:
        data["key1"] = did
    data["key2"] = stamp
    if fresh_session:
        data.update(_session_fields(stamp))
    data.update(overrides or {})
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


# --------------------------------------------------------------------------- #
# 怎么重新抓（换机器时照做一遍）                                                 #
# --------------------------------------------------------------------------- #
# 1. 浏览器打开 https://captcha.zt.kuaishou.com/iframe/index.html?captchaSession=probe
# 2. 用 CDP evaluate 跑下面这段：它先拿到 webpack 的 __webpack_require__，
#    再把模块 998f 的工厂源码取出来、在函数体末尾注入一行把内部的 Ga 暴露到
#    window 上，然后重新执行这个工厂。Ga 是模块内的局部函数，没有导出，
#    只能这么够到。gpuInfo 则可以直接从模块 5634 的导出 b() 拿。
capture_js = r"""
async () => {
  let req = null;
  const mk = 'probe_' + Date.now();
  (window.webpackJsonp || []).push([[mk], { [mk]: function (m, e, r) { req = r; } }, [[mk]]]);
  if (!req || !req.m) return { err: 'no webpack require' };

  // gpuInfo：模块 5634 的导出 b()
  const gt = req.c['5634'] && req.c['5634'].exports;
  const gpuInfo = gt && typeof gt.b === 'function' ? gt.b() : null;

  // captchaExtraParam：把模块 998f 的工厂改一改，暴露内部的 Ga
  const src = Function.prototype.toString.call(req.m['998f']);
  const bs = src.indexOf('{'), be = src.lastIndexOf('}');
  const args = (src.slice(0, bs).match(/\(([^)]*)\)/) || [, 'e,n,t'])[1];
  const patched = new Function(args, src.slice(bs + 1, be)
    + ';try{if(typeof Ga!=="undefined")window.__Ga=Ga;}catch(_){};');
  const mod = { exports: {} };
  delete req.c['998f'];
  try { patched.call(mod.exports, mod, mod.exports, req); } catch (e) {}
  req.c['998f'] = mod;

  const extra = typeof window.__Ga === 'function' ? await window.__Ga() : null;
  return { gpuInfo, captchaExtraParam: extra };
}
"""

# 兼容旧名字
capture_gpu_info_js = capture_js
