"""保存并读取帮助指令分类；模型输出只能引用已注册指令。"""

import hashlib
import json
from pathlib import Path


def _fingerprint(names, revision=""):
    payload = json.dumps([revision, sorted(set(names))], ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse_classification(answer, names):
    text = answer.strip()
    if text.startswith("```") and text.endswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("模型结果不是对象")
    common, advanced = data.get("common"), data.get("advanced")
    if not isinstance(common, list) or not isinstance(advanced, list):
        raise ValueError("模型结果缺少常用或高级列表")
    if not all(isinstance(name, str) for name in common + advanced):
        raise ValueError("指令名必须是文字")
    provided = common + advanced
    if len(provided) != len(set(provided)) or set(provided) != set(names):
        raise ValueError("模型结果遗漏、重复或增加了指令")
    return set(advanced)


def _read(path):
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def save_selection(path, plugin_name, names, advanced, revision=""):
    path = Path(path)
    data = _read(path)
    plugins = data.get("plugins")
    if not isinstance(plugins, dict):
        plugins = {}
    plugins[plugin_name] = {
        "fingerprint": _fingerprint(names, revision),
        "advanced": sorted(set(advanced)),
    }
    data["plugins"] = plugins
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def load_selection(path, plugin_name, names, revision=""):
    record = _read(path).get("plugins", {}).get(plugin_name, {})
    if not isinstance(record, dict) or record.get("fingerprint") != _fingerprint(names, revision):
        return set()
    advanced = record.get("advanced", [])
    return set(advanced) & set(names) if isinstance(advanced, list) else set()


def has_record(path, plugin_name):
    plugins = _read(path).get("plugins", {})
    return isinstance(plugins, dict) and plugin_name in plugins
