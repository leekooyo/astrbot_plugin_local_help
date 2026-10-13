"""本地图片帮助：按插件展示简短目录和完整指令。"""

import functools
import inspect

from astrbot.api import html_renderer, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import Image
from astrbot.core.star import command_management
from astrbot.core.star.filter.command import CommandFilter
from astrbot.core.star.filter.command_group import CommandGroupFilter
from astrbot.core.star.filter.event_message_type import EventMessageType, EventMessageTypeFilter
from astrbot.core.star.star_handler import star_handlers_registry


USAGE = {
    "help": "/help [插件名]",
    "llm": "/llm",
    "gate": "/gate [子指令]",
    "persona": "/persona [子指令]",
    "plugin": "/plugin <子指令>",
    "表情管理": "/表情管理 <子指令>",
    "总结": "/总结 <视频链接或BV号>",
    "最新视频": "/最新视频 <UID或昵称>",
    "订阅": "/订阅 <UID或昵称>",
    "取消订阅": "/取消订阅 <UID或昵称>",
    "总结模型": "/总结模型 [模型标识或默认]",
    "加审批员": "/加审批员 <@QQ号>",
    "减审批员": "/减审批员 <@QQ号>",
    "群列表": "/群列表",
    "好友列表": "/好友列表",
    "退群": "/退群 <群号或序号> [更多目标]",
    "删好友": "/删好友 <QQ号或序号> [更多目标]",
    "加好友": "/加好友 <QQ号> [验证消息] [备注] [答案]",
    "加群": "/加群 <群号> [答案]",
    "戳": "/戳 [@QQ号或我] [次数]",
}
PARAMETER = {
    "qq": "QQ号", "admin_id": "QQ号", "count": "数量", "times": "次数",
    "plugin_name": "插件名", "plugin_repo": "仓库地址", "group_id": "群号",
    "keyword": "名称", "meme_name": "名称", "idx_or_name": "序号或名称",
}
PERMISSION = {
    "admin": "机器人管理员",
    "member": "所有用户",
    "everyone": "所有用户",
    "group_admin": "群管理员或机器人管理员",
    "shared_group_admin": "群管理员或机器人管理员",
}
OLD_LABELS = {
    "astrbot_plugin_error_pro": "错误提示管理",
    "builtin_commands_extension": "内置指令扩展",
}


def _walk(commands):
    for command in commands:
        yield command
        yield from _walk(command.get("sub_commands", []))


def _usage(command, handler):
    name = command["effective_command"]
    if name in USAGE:
        return USAGE[name]
    parts = ["/" + name]
    try:
        params = list(inspect.signature(handler.handler).parameters.values())
    except (AttributeError, TypeError, ValueError):
        return parts[0]
    skip = 1 if isinstance(handler.handler, functools.partial) or inspect.ismethod(handler.handler) else 2
    for param in params[skip:]:
        label = PARAMETER.get(param.name, param.name.replace("_", " "))
        opening, closing = ("<", ">") if param.default is inspect.Parameter.empty else ("[", "]")
        parts.append(f"{opening}{label}{closing}")
    return " ".join(parts)


def format_index(plugins):
    lines = ["# 插件目录", "发送 `/help 插件名` 查看完整用法。", ""]
    lines.extend(f"- /{plugin['label']}" for plugin in plugins)
    return "\n".join(lines)


def format_detail(plugin, commands, extra_help=""):
    lines = [f"# {plugin['label']}", f"插件标识：`{plugin['name']}`"]
    if not plugin["activated"]:
        lines.append("当前状态：已停用")
    if description := plugin["description"].strip().split("\n", 1)[0]:
        lines.append(description)
    if commands:
        lines.extend(["", "## 使用方法"])
        for command, handler, names in commands:
            name = command["effective_command"]
            aliases = sorted({"/" + candidate for candidate in names if candidate != name})
            description = (command.get("description") or "").strip().split("\n", 1)[0]
            detail = [f"### /{name}", f"用法：{_usage(command, handler)}",
                      f"权限：{PERMISSION.get(command.get('permission'), '所有用户')}"]
            if aliases:
                detail.append("别名：" + "、".join(aliases))
            if description:
                detail.append("说明：" + description)
            group_only = plugin["name"] == "astrbot_plugin_qqadmin" or any(
                isinstance(f, EventMessageTypeFilter)
                and not (f.event_message_type & EventMessageType.PRIVATE_MESSAGE)
                for f in handler.event_filters
            )
            if group_only:
                detail.append("场景：仅群聊可用")
            lines.extend(["", "  \n".join(detail)])
    else:
        lines.extend(["", "此插件没有需要手动输入的指令。"])
    if extra_help:
        lines.extend(["", "## 补充用法", extra_help.replace("\n", "  \n")])
    return "\n".join(lines)


@register("astrbot_plugin_local_help", "local", "本地图片帮助和插件简称", "1.0.0")
class LocalHelp(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.config = config

    def _catalog(self):
        short_names = {}
        for entry in self.config.get("short_names", []):
            if isinstance(entry, str) and ":" in entry:
                plugin_id, label = entry.split(":", 1)
                if plugin_id.strip() and label.strip():
                    short_names[plugin_id.strip()] = label.strip()
        plugins = []
        for meta in self.context.get_all_stars():
            name = getattr(meta, "name", "") or ""
            if not name or name == "astrbot":
                continue
            display_name = (getattr(meta, "display_name", "") or name).strip()
            plugins.append({
                "name": name,
                "label": short_names.get(name, display_name),
                "display_name": display_name,
                "activated": bool(getattr(meta, "activated", False)),
                "description": getattr(meta, "desc", "") or "",
            })
        return sorted(plugins, key=lambda item: item["label"].casefold())

    def _find_plugin(self, query, catalog):
        query = query.strip().casefold()
        for plugin in catalog:
            names = {plugin["name"], plugin["label"], plugin["display_name"]}
            if old_label := OLD_LABELS.get(plugin["name"]):
                names.add(old_label)
            if query in {name.casefold() for name in names}:
                return plugin
        return None

    def _extra_help(self, plugin_name):
        if plugin_name != "gatekeeper":
            return ""
        metadata = self.context.get_registered_star(plugin_name)
        instance = getattr(metadata, "star_cls", None)
        method = getattr(instance, "_help_text", None)
        return method() if callable(method) else ""

    async def _image_result(self, event, content):
        cfg = self.context.get_config(umo=event.unified_msg_origin)
        try:
            output = await html_renderer.render_t2i(
                content,
                return_url=True,
                use_network=cfg.get("t2i_strategy") == "remote",
                template_name=cfg.get("t2i_active_template"),
            )
            image = Image.fromURL(output) if output.startswith("http") else Image.fromFileSystem(output)
            return event.chain_result([image])
        except Exception:
            logger.exception("本地帮助图片生成失败")
            return event.plain_result("帮助图片生成失败，请稍后重试。")

    @filter.command("help", alias={"helps", "帮助", "菜单", "功能", "幫助", "菜單"}, priority=99997)
    async def help(self, event: AstrMessageEvent):
        """查看插件目录；发送 /help 插件名 查看详细用法。"""
        words = event.get_message_str().strip().split(maxsplit=1)
        query = words[1].strip() if len(words) > 1 else ""
        catalog = self._catalog()
        if not query:
            content = format_index(catalog)
        elif plugin := self._find_plugin(query, catalog):
            rows = []
            for command in _walk(await command_management.list_commands()):
                if command.get("plugin") != plugin["name"] or not command.get("enabled"):
                    continue
                handler = star_handlers_registry.get_handler_by_full_name(command["handler_full_name"])
                if handler is None:
                    continue
                command_filter = next((f for f in handler.event_filters if isinstance(f, (CommandFilter, CommandGroupFilter))), None)
                names = command_filter.get_complete_command_names() if command_filter else [command["effective_command"]]
                rows.append((command, handler, names))
            content = format_detail(plugin, rows, self._extra_help(plugin["name"]))
        else:
            content = f"# 未找到插件\n没有找到「{query}」。发送 `/help` 查看插件目录。"
        result = await self._image_result(event, content)
        event.stop_event()
        yield result
