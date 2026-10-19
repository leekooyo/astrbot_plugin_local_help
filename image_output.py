"""把插件的文字回复用 AstrBot 当前图片模板呈现。"""

import html
import re

from astrbot.api import html_renderer, logger
from astrbot.core.message.components import Image, Plain
from astrbot.core.message.message_event_result import ResultContentType


FAILURE_TEXT = "图片生成失败，请稍后重试。"

# 这些命令的返回值会被用户复制到下一条命令，或本身就是应保留的正文。
TEXT_COMMANDS = {
    "总结", "bv", "BiliVideo", "视频总结", "最新视频", "latest",
    "总结模型", "bvmodel", "模型列表", "切换模型",
    "订阅列表", "sublist", "subs", "订阅列表查看",
    "推送列表", "pushls", "push_list", "推送目标",
    "群管配置", "群管设置", "查看群文件", "上传群文件",
    "群列表", "好友列表", "抽查", "群精华", "查看群精华",
    "群公告", "查看群公告", "meme详情", "表情详情", "meme信息",
    "meme黑名单", "gate", "plugin", "model", "persona", "history",
}
TEXT_MEME_SUBCOMMANDS = {
    "参数", "设置", "查看图库", "绑定图库", "图库绑定", "收集目标",
    "同步状态", "清理超额",
}
ACTIONABLE_TEXT = re.compile(
    r"https?://|(?:BV[0-9A-Za-z]{10})|(?:\d{5,})|"
    r"(?:[A-Za-z]:\\)|(?:[\w.-]+[/\\][\w./\\-]+)|(?:astrbot_plugin_[\w-]+)|"
    r"(?:^|\s)/[\w\u4e00-\u9fff-]+|"
    r"(?:Traceback|Exception|错误详情|原始错误|\bflag\s*[:=])",
    re.IGNORECASE | re.MULTILINE,
)


def _keep_text(event, result):
    if getattr(result, "use_t2i_", None) is False:
        return True
    # 图片、转发、@ 等混合消息保持原有结构，避免改变申请审批和预览消息。
    if len(result.chain) != 1 or not isinstance(result.chain[0], Plain):
        return True
    message = getattr(event, "get_message_str", lambda: "")().strip()
    if re.search(r"https?://|\bBV[0-9A-Za-z]{10}\b", message, re.IGNORECASE):
        return True
    parts = message.removeprefix("/").split()
    if parts:
        command = parts[0]
        if command in TEXT_COMMANDS:
            return True
        if command == "表情管理" and len(parts) > 1 and parts[1] in TEXT_MEME_SUBCOMMANDS:
            return True
    reply = result.chain[0].text
    if "图片生成失败" in reply:
        return True
    # 复读必须仍是原文；自动通知、推送若含链接或操作标识也保留文字。
    return bool(reply == message or ACTIONABLE_TEXT.search(reply))


async def _render(text, config):
    output = await html_renderer.render_t2i(
        html.escape(text),
        return_url=True,
        use_network=config.get("t2i_strategy") == "remote",
        template_name=config.get("t2i_active_template"),
    )
    return Image.fromURL(output) if output.startswith("http") else Image.fromFileSystem(output)


async def convert_result(event, result, config):
    """只改普通结果里的文字组件；模型回复、语音和其他组件保留。"""
    if result is None or not isinstance(getattr(result, "chain", None), list):
        return result
    if getattr(result, "result_content_type", None) in {
        ResultContentType.LLM_RESULT,
        ResultContentType.AGENT_RUNNER_ERROR,
        ResultContentType.STREAMING_RESULT,
        ResultContentType.STREAMING_FINISH,
    }:
        return result
    if not any(isinstance(part, Plain) and part.text.strip() for part in result.chain):
        return result
    if _keep_text(event, result):
        return result
    converted = []
    text_parts = []

    async def flush_text():
        if text_parts:
            value = "".join(text_parts)
            text_parts.clear()
            if value.strip():
                converted.append(await _render(value, config))

    try:
        for part in result.chain:
            if isinstance(part, Plain):
                text_parts.append(part.text)
            else:
                await flush_text()
                converted.append(part)
        await flush_text()
        result.chain[:] = converted
    except Exception:
        logger.exception("插件文字回复生成图片失败")
        result.chain[:] = [Plain(FAILURE_TEXT)]
    return result


def wrap_direct_send(event, config):
    """同一条事件的直接发送也经过相同转换；每个事件只包裹一次。"""
    if getattr(event, "_local_help_image_send_wrapped", False):
        return
    original_send = event.send

    async def send_with_image(result, *args, **kwargs):
        await convert_result(event, result, config)
        return await original_send(result, *args, **kwargs)

    event.send = send_with_image
    event._local_help_image_send_wrapped = True
