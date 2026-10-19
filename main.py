"""本地图片帮助：按插件展示目录、常用与高级指令。"""

import functools
import html
import inspect

from astrbot.api import html_renderer, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import Image
from astrbot.core.star import command_management
from astrbot.core.star.star_tools import StarTools
from astrbot.core.star.filter.command import CommandFilter
from astrbot.core.star.filter.command_group import CommandGroupFilter
from astrbot.core.star.filter.event_message_type import EventMessageType, EventMessageTypeFilter
from astrbot.core.star.star_handler import star_handlers_registry

from . import classification
from .image_output import convert_result, wrap_direct_send


USAGE = {
    "help": "/help [插件名] [高级]",
    "help 归类": "/help 归类 <插件名>",
    "llm": "/llm",
    "gate": "/gate [子指令]",
    "persona": "/persona [子指令]",
    "plugin": "/plugin <子指令>",
    "表情管理": "/表情管理 <子指令>",
    "总结": "/总结 <视频链接或BV号>",
    "最新视频": "/最新视频 <UID、空间链接或昵称>",
    "订阅": "/订阅 <UID、空间链接或昵称>",
    "取消订阅": "/取消订阅 <UID、空间链接或昵称>",
    "总结模型": "/总结模型 [模型标识或默认]",
    "添加推送群": "/添加推送群 <群号>",
    "添加推送号": "/添加推送号 <QQ号>",
    "移除推送": "/移除推送 <群号或QQ号>",
    "加审批员": "/加审批员 <@QQ号>",
    "减审批员": "/减审批员 <@QQ号>",
    "群列表": "/群列表 [页码]",
    "好友列表": "/好友列表 [页码]",
    "退群": "/退群 <群号、序号或区间> [更多目标]",
    "删好友": "/删好友 <QQ号、序号或区间> [更多目标]",
    "加好友": "/加好友 <QQ号> [验证消息] [备注] [答案]",
    "加群": "/加群 <群号> [答案]",
    "戳": "/戳 [@QQ号或我] [次数]",
    "禁言": "/禁言 <秒数> @群友",
    "解禁": "/解禁 @群友",
    "撤回": "/撤回 [@群友] [消息数量]",
    "踢了": "/踢了 @群友",
    "申请头衔": "/申请头衔 <新头衔>",
    "全禁": "/全禁 <开|关>",
    "改名": "/改名 <新昵称> @群友",
    "改头衔": "/改头衔 <新头衔> @群友",
    "群拉黑": "/群拉黑 @群友",
    "上管": "/上管 @群友",
    "下管": "/下管 @群友",
    "设精": "/设精",
    "移精": "/移精",
    "设置群头像": "/设置群头像",
    "设置群名": "/设置群名 <新群名>",
    "发布群公告": "/发布群公告 <文字内容>",
    "设置禁词": "/设置禁词 <词语或+词语/-词语>",
    "进群白词": "/进群白词 [关键词，用空格分隔]",
    "进群黑词": "/进群黑词 [关键词，用空格分隔]",
    "进群黑名单": "/进群黑名单 <QQ号或+QQ号/-QQ号>",
    "进群欢迎": "/进群欢迎 <欢迎语或清空>",
    "群管配置": "/群管配置 [群号] [配置串]",
    "群管重置": "/群管重置 [群号或all]",
    "批准": "/批准 [附加信息]",
    "驳回": "/驳回 [附加信息]",
    "清理群友": "/清理群友 [未发言天数] [群等级]",
    "上传群文件": "/上传群文件 <文件名或路径>",
    "删除群文件": "/删除群文件 <文件名或路径>",
    "查看群文件": "/查看群文件 [文件名或路径]",
    "表情管理 添加表情": "/表情管理 添加表情 [类别名称]",
    "表情管理 参数": "/表情管理 参数 [参数名]",
    "表情管理 设置": "/表情管理 设置 <参数名> <值或默认>",
    "gate list": "/gate list [页码]",
    "gate on": "/gate on",
    "gate off": "/gate off",
    "gate mode": "/gate mode <群号或all> <mute|llm|plugin|both>",
    "gate plugin": "/gate plugin <群号或all> <插件名或all> <on|off>",
}
DESCRIPTION = {
    "总结帮助": "查看视频总结插件的完整说明。",
    "识别开关": "切换自动识别视频链接的状态。",
    "总结状态": "查看视频总结插件的运行状态。",
    "总结清缓存": "清除已保存的视频总结缓存。",
    "总结模型": "查看或切换视频总结使用的模型。",
    "B站登录": "通过扫码登录 B 站账号。",
    "B站登出": "退出当前 B 站账号。",
    "YT登录": "登录 YouTube 账号。",
    "YT登出": "退出当前 YouTube 账号。",
    "总结": "总结一个视频。",
    "最新视频": "查看 UP 主的最新视频。",
    "订阅": "订阅 UP 主的新视频。",
    "取消订阅": "取消一个 UP 主的订阅。",
    "订阅列表": "查看当前订阅。",
    "检查更新": "立即检查订阅的更新。",
    "添加推送群": "把群加入推送目标。",
    "添加推送号": "把 QQ 用户加入推送目标。",
    "推送列表": "查看当前推送目标。",
    "移除推送": "移除一个推送目标。",
}
SCENE_HINT = {
    "设精": "先引用要设为精华的消息。",
    "移精": "先引用要移出精华的消息。",
    "设置群头像": "先引用要设置为群头像的图片。",
    "发布群公告": "需要图片时，先引用图片。",
    "撤回": "也可以引用消息后发送 /撤回。",
    "批准": "先引用对应的入群申请通知。",
    "驳回": "先引用对应的入群申请通知。",
    "同意": "先引用对应的申请通知。",
    "拒绝": "先引用对应的申请通知。",
    "拉黑": "先引用对应的申请通知。",
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
PLUGIN_DESCRIPTION = {
    "astrbot_plugin_bilivideo": "总结视频，订阅 UP 主并接收新视频提醒。",
    "astrbot_plugin_error_pro": "处理机器人回复失败时的提示。",
    "astrbot_plugin_local_help": "查看插件目录、常用和高级指令。",
    "astrbot_plugin_memelite": "按名称和素材制作表情图。",
    "astrbot_plugin_pokepro": "戳一戳群友或回应别人戳机器人。",
    "astrbot_plugin_qqadmin": "管理 QQ 群成员、消息和群设置。",
    "astrbot_plugin_relationship": "管理好友、群聊和申请。",
    "astrbot_plugin_reread": "在群聊中参与复读并处理刷屏。",
    "astrbot_plugin_wakepro": "控制机器人在群聊中何时回应。",
    "builtin_commands_extension": "管理对话、模型和插件。",
    "gatekeeper": "设置各群可以使用的聊天与插件功能。",
    "meme_manager": "管理表情图库和表情发送。",
}
CURATED_COMMON = {
    "astrbot_plugin_bilivideo": {"总结", "最新视频", "订阅", "取消订阅", "订阅列表"},
    "astrbot_plugin_error_pro": {"重新加载完成标记提示"},
    "astrbot_plugin_local_help": {"help"},
    "astrbot_plugin_memelite": {"meme列表", "meme详情"},
    "astrbot_plugin_pokepro": {"戳"},
    "astrbot_plugin_qqadmin": {"禁言", "解禁", "撤回", "踢了", "群友信息", "群公告", "申请头衔"},
    "astrbot_plugin_relationship": {"群列表", "好友列表", "同意", "拒绝", "退群", "删好友"},
    "builtin_commands_extension": {"llm", "model", "ls", "switch", "history", "persona", "plugin ls"},
    "gatekeeper": {"gate list", "gate on", "gate off", "gate mode"},
    "meme_manager": {"表情包", "表情管理 查看图库", "表情管理 添加表情", "表情管理 图库统计"},
}
GATE_COMMANDS = (
    ("gate list", "刷新并查看群功能策略", "everyone"),
    ("gate on", "开启群功能总控", "admin"),
    ("gate off", "关闭群功能总控", "admin"),
    ("gate mode", "设置群模式：mute 全禁、llm 只聊天、plugin 只插件、both 全开", "admin"),
    ("gate plugin", "设置指定群的插件开关", "admin"),
)
REVIEW_COMMANDS = {"同意", "拒绝", "拉黑"}


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


def _description(plugin_name, command):
    name = command["effective_command"]
    fallback = DESCRIPTION.get(name, "") if plugin_name == "astrbot_plugin_bilivideo" else ""
    return (command.get("description") or fallback).strip().split("\n", 1)[0]


def format_index(plugins):
    lines = ["# 插件目录", "发送 `/help 插件名` 查看常用指令。", ""]
    lines.extend(f"- {plugin['label']}" + ("（已停用）" if not plugin["activated"] else "") for plugin in plugins)
    return "\n".join(lines)


def format_detail(plugin, commands, section="common", has_advanced=False,
                  no_access=False):
    lines = [f"# {plugin['label']}"]
    if not plugin["activated"]:
        lines.append("当前已停用，下列指令暂不可用。")
    if description := PLUGIN_DESCRIPTION.get(plugin["name"], plugin["description"].strip().split("\n", 1)[0]):
        lines.append(description)
    if commands:
        lines.extend(["", "## 高级指令" if section == "advanced" else "## 常用指令"])
        permissions = {PERMISSION.get(command.get("permission"), "所有用户") for command, _, _ in commands}
        shared_permission = next(iter(permissions)) if len(permissions) == 1 else None
        if shared_permission and shared_permission != "所有用户":
            lines.append(f"权限：{shared_permission}")
        for command, handler, names in commands:
            name = command["effective_command"]
            aliases = sorted({"/" + candidate for candidate in names if candidate != name})
            description = _description(plugin["name"], command)
            detail = [f"### {html.escape(_usage(command, handler))}"]
            if not shared_permission and command.get("permission") not in ("everyone", "member"):
                detail.append(f"权限：{PERMISSION.get(command.get('permission'), '所有用户')}")
            if aliases:
                detail.append("别名：" + "、".join(aliases))
            if description:
                detail.append(description)
            if name in ("退群", "删好友"):
                detail.append("多个目标可用空格分隔。")
            if name == "加好友":
                detail.append("私聊使用时建议填写验证消息；备注和答案按顺序选填。")
            if name == "gate mode":
                detail.append("例：/gate mode <GROUP_ID> both（该群允许聊天和插件）。")
            if name == "gate plugin":
                detail.append("例：/gate plugin <GROUP_ID> all off（关闭该群所有插件）。")
            if hint := SCENE_HINT.get(name):
                detail.append(hint)
            group_only = (plugin["name"] == "astrbot_plugin_qqadmin" and
                          name not in {"批准", "驳回"}) or any(
                isinstance(f, EventMessageTypeFilter)
                and not (f.event_message_type & EventMessageType.PRIVATE_MESSAGE)
                for f in handler.event_filters
            )
            if group_only:
                detail.append("请在群内使用。")
            lines.extend(["", "  \n".join(detail)])
    else:
        message = ("当前身份没有可用指令。" if no_access else
                   "当前没有高级指令。" if section == "advanced" else
                   "当前没有可显示的常用指令。" if has_advanced else
                   "此插件没有需要手动输入的指令。")
        lines.extend(["", message])
    if section == "common" and has_advanced:
        lines.extend(["", f"更多指令：`/help {plugin['label']} 高级`"])
    return "\n".join(lines)


@register("astrbot_plugin_local_help", "local", "本地图片帮助和插件简称", "1.1.0")
class LocalHelp(Star):
    def __init__(self, context: Context, config):
        super().__init__(context)
        self.config = config

    @filter.event_message_type(EventMessageType.ALL, priority=1000000)
    async def prepare_image_replies(self, event: AstrMessageEvent):
        """让本条事件中的直接文字发送也使用默认图片模板。"""
        config = self.context.get_config(umo=event.unified_msg_origin)
        wrap_direct_send(event, config)

    @filter.on_decorating_result(priority=-999999)
    async def image_text_result(self, event: AstrMessageEvent):
        """发送前把普通文字回复转为图片；普通模型聊天保持原样。"""
        result = event.get_result()
        if result is not None:
            if result.is_model_result():
                # 核心的长文本转图在此钩子之后运行，需要明确关闭本条模型回复的转图。
                result.use_t2i(False)
                return
            config = self.context.get_config(umo=event.unified_msg_origin)
            await convert_result(event, result, config)

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
                "version": str(getattr(meta, "version", "") or ""),
            })
        return sorted(plugins, key=lambda item: item["label"].casefold())

    def _find_plugin(self, query, catalog):
        query = query.strip().removeprefix("/").casefold()
        for plugin in catalog:
            names = {plugin["name"], plugin["label"], plugin["display_name"]}
            if old_label := OLD_LABELS.get(plugin["name"]):
                names.add(old_label)
            if query in {name.casefold() for name in names}:
                return plugin
        return None

    def _state_path(self):
        return StarTools.get_data_dir("astrbot_plugin_local_help") / "classification.json"

    async def _registered_rows(self, plugin_name):
        rows = []
        for command in _walk(await command_management.list_commands()):
            if command.get("plugin") != plugin_name or not command.get("enabled"):
                continue
            if command.get("sub_commands"):
                continue
            handler = star_handlers_registry.get_handler_by_full_name(command["handler_full_name"])
            if handler is None:
                continue
            if plugin_name == "gatekeeper" and command["effective_command"] == "gate":
                for name, description, permission in GATE_COMMANDS:
                    virtual = dict(command, effective_command=name, description=description,
                                   permission=permission)
                    rows.append((virtual, handler, [name]))
                continue
            if plugin_name == "astrbot_plugin_local_help" and command["effective_command"] == "help":
                rows.append((command, handler, ["help"]))
                virtual = dict(command, effective_command="help 归类",
                               description="让已配置的模型重新划分常用与高级指令",
                               permission="admin")
                rows.append((virtual, handler, ["help 归类"]))
                continue
            command_filter = next(
                (f for f in handler.event_filters if isinstance(f, (CommandFilter, CommandGroupFilter))),
                None,
            )
            names = command_filter.get_complete_command_names() if command_filter else [command["effective_command"]]
            rows.append((command, handler, names))
        return rows

    def _selection(self, plugin, rows):
        names = list(dict.fromkeys(command["effective_command"] for command, _, _ in rows))
        path = self._state_path()
        if classification.has_record(path, plugin["name"]):
            return classification.load_selection(path, plugin["name"], names,
                                                 revision=plugin.get("version", ""))
        common = CURATED_COMMON.get(plugin["name"])
        advanced = set(names) - common if common is not None else set()
        classification.save_selection(path, plugin["name"], names, advanced,
                                      revision=plugin.get("version", ""))
        return advanced

    @staticmethod
    def _is_group_admin(event):
        group = getattr(getattr(event, "message_obj", None), "group", None)
        if group is None:
            return False
        sender = str(event.get_sender_id())
        return (sender == str(getattr(group, "group_owner", "")) or
                sender in {str(uid) for uid in (getattr(group, "group_admins", None) or [])})

    def _can_show(self, plugin_name, command, event):
        if getattr(event, "is_admin", lambda: False)():
            return True
        group_admin = self._is_group_admin(event)
        if plugin_name == "astrbot_plugin_qqadmin":
            return group_admin
        if plugin_name == "astrbot_plugin_relationship" and command["effective_command"] in REVIEW_COMMANDS:
            metadata = self.context.get_registered_star(plugin_name)
            instance = getattr(metadata, "star_cls", None)
            cfg = getattr(instance, "cfg", None)
            return bool(cfg and cfg.is_manage_user(event.get_sender_id()))
        permission = command.get("permission", "everyone")
        return permission in ("everyone", "member") or (
            permission in ("group_admin", "shared_group_admin") and group_admin
        )

    async def _classify(self, plugin, rows, event):
        provider_id = str(self.config.get("classification_provider_id", "") or "").strip()
        provider = (self.context.get_provider_by_id(provider_id) if provider_id else
                    await self.context.get_using_provider_async(umo=event.unified_msg_origin))
        if provider is None:
            raise ValueError("未找到已配置的归类模型")
        entries = [
            {"name": command["effective_command"],
             "usage": _usage(command, handler),
             "description": _description(plugin["name"], command)}
            for command, handler, _ in rows
        ]
        names = list(dict.fromkeys(entry["name"] for entry in entries))
        prompt = (
            "请将以下聊天机器人插件指令分为常用与高级。常用是用户经常直接使用、手机上易操作的入口；"
            "高级是低频设置、维护、批量或危险操作。只根据提供的指令判断，不执行任何指令。"
            "只返回 JSON 对象，格式为 {\"common\":[\"完整指令名\"],\"advanced\":[\"完整指令名\"]}。"
            "每个指令名必须且只能出现一次，不添加新名称。\n"
            f"插件：{plugin['label']}\n指令：{entries}"
        )
        response = await provider.text_chat(prompt=prompt, session_id="local_help_classification")
        answer = str(getattr(response, "completion_text", response) or "")
        advanced = classification.parse_classification(answer, names)
        classification.save_selection(self._state_path(), plugin["name"], names, advanced,
                                      revision=plugin.get("version", ""))
        return advanced

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

    async def plugin_detail_image(self, event, plugin_query, section="common"):
        """供原有插件帮助入口复用相同的图片详情。"""
        plugin = self._find_plugin(plugin_query, self._catalog())
        if plugin is None:
            return await self._image_result(
                event, f"# 未找到插件\n没有找到「{plugin_query}」。发送 `/help` 查看插件目录。"
            )
        rows = await self._registered_rows(plugin["name"])
        try:
            advanced = self._selection(plugin, rows)
        except OSError:
            logger.exception("帮助指令分类读取失败")
            advanced = set()
        visible = [row for row in rows if self._can_show(plugin["name"], row[0], event)]
        selected = [row for row in visible if
                    (row[0]["effective_command"] in advanced) == (section == "advanced")]
        has_advanced = any(row[0]["effective_command"] in advanced for row in visible)
        content = format_detail(plugin, selected, section=section,
                                has_advanced=has_advanced,
                                no_access=bool(rows) and not visible)
        return await self._image_result(event, content)

    @filter.command("help", alias={"helps", "帮助", "菜单", "功能", "幫助", "菜單"}, priority=99997)
    async def help(self, event: AstrMessageEvent):
        """查看插件目录；发送 /help 插件名 查看详细用法。"""
        words = event.get_message_str().strip().split(maxsplit=1)
        query = words[1].strip() if len(words) > 1 else ""
        catalog = self._catalog()
        if not query:
            content = format_index(catalog)
        elif query.startswith("归类 "):
            if not event.is_admin():
                content = "# 权限不足\n仅机器人管理员可以重新归类指令。"
            elif plugin := self._find_plugin(query.removeprefix("归类 "), catalog):
                rows = await self._registered_rows(plugin["name"])
                try:
                    advanced = await self._classify(plugin, rows, event)
                    visible = [row for row in rows if self._can_show(plugin["name"], row[0], event)]
                    common = [row for row in visible if row[0]["effective_command"] not in advanced]
                    content = (f"归类完成：常用 {len(rows) - len(advanced)} 条，高级 {len(advanced)} 条。\n\n"
                               + format_detail(plugin, common, has_advanced=bool(advanced),
                                               no_access=bool(rows) and not visible))
                except Exception:
                    logger.exception("帮助指令归类失败")
                    content = (f"# 归类失败\n{plugin['label']} 的指令暂未重新归类。"
                               "可稍后再次发送 `/help 归类 插件名`。")
            else:
                content = "# 未找到插件\n发送 `/help` 查看插件目录。"
        else:
            section = "advanced" if query.endswith(" 高级") else "common"
            plugin_query = query.removesuffix(" 高级") if section == "advanced" else query
            result = await self.plugin_detail_image(event, plugin_query, section)
            event.stop_event()
            yield result
            return
        result = await self._image_result(event, content)
        event.stop_event()
        yield result
