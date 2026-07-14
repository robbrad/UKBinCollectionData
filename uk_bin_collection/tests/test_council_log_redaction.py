"""Package-wide regression checks for sensitive diagnostic output."""

from __future__ import annotations

import ast
from pathlib import Path

CORE_DIRECTORY = Path(__file__).resolve().parents[1] / "uk_bin_collection"
COUNCILS_DIRECTORY = CORE_DIRECTORY / "councils"
HOME_ASSISTANT_DIRECTORY = (
    Path(__file__).resolve().parents[2] / "custom_components" / "uk_bin_collection"
)
AUDITED_FILES = (
    tuple(sorted(COUNCILS_DIRECTORY.glob("*.py")))
    + tuple(sorted(CORE_DIRECTORY.glob("*.py")))
    + tuple(sorted(HOME_ASSISTANT_DIRECTORY.glob("*.py")))
)
LOG_METHODS = {"critical", "debug", "error", "exception", "info", "warning"}
SAFE_STATE_SUFFIXES = (
    "_count",
    "_found",
    "_length",
    "_matched",
    "_present",
    "_status",
    "_status_code",
    "_total",
)
SAFE_STATE_NAMES = {
    "council_key",
    "http_status",
    "manual_refresh",
    "response_status",
    "status",
    "status_code",
    "timeout",
    "update_interval",
    "update_interval_hours",
}
SENSITIVE_NAME_PARTS = (
    "address",
    "bin",
    "collection",
    "data",
    "date",
    "html",
    "markup",
    "mapping",
    "month",
    "option",
    "output",
    "page_source",
    "paon",
    "postcode",
    "result",
    "raw",
    "response",
    "service",
    "tag",
    "text",
    "uprn",
    "usrn",
    "waste",
    "web_driver",
)
SENSITIVE_EXACT_NAMES = {
    "body",
    "item",
    "key",
    "page",
    "payload",
    "row",
    "soup",
    "url",
    "value",
}
SENSITIVE_ATTRIBUTES = {
    "_attribute_type",
    "_bin_type",
    "content",
    "data",
    "page_source",
    "url",
}


def _diagnostic_sinks(tree: ast.AST):
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            yield node
        elif isinstance(node.func, ast.Attribute) and node.func.attr in LOG_METHODS:
            yield node


def _exception_names(tree: ast.AST) -> set[str]:
    return {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ExceptHandler) and isinstance(node.name, str)
    }


def _root_name(node: ast.AST) -> str | None:
    while isinstance(node, (ast.Attribute, ast.Call, ast.Subscript)):
        if isinstance(node, ast.Attribute):
            node = node.value
        elif isinstance(node, ast.Call):
            node = node.func
        else:
            node = node.value
    return node.id if isinstance(node, ast.Name) else None


def _is_sensitive_name(name: str) -> bool:
    lowered = name.lower()
    if lowered in SAFE_STATE_NAMES or lowered.endswith(SAFE_STATE_SUFFIXES):
        return False
    if lowered in SENSITIVE_EXACT_NAMES:
        return True
    if lowered.startswith("url_") or lowered.endswith("_url"):
        return True
    return any(part in lowered for part in SENSITIVE_NAME_PARTS)


def _is_safe_summary(node: ast.AST, exception_names: set[str]) -> bool:
    if (
        isinstance(node, ast.Attribute)
        and node.attr == "__name__"
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "type"
        and len(node.value.args) == 1
        and isinstance(node.value.args[0], ast.Name)
        and node.value.args[0].id in exception_names
    ):
        return True
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "len"
        and len(node.args) == 1
    ):
        return True
    return isinstance(node, ast.Attribute) and node.attr == "status_code"


def _expression_findings(
    node: ast.AST,
    exception_names: set[str],
    tainted_names: set[str],
) -> set[str]:
    if _is_safe_summary(node, exception_names):
        return set()

    findings = set()
    if isinstance(node, ast.Name):
        if node.id.lower() in SAFE_STATE_NAMES or node.id.lower().endswith(
            SAFE_STATE_SUFFIXES
        ):
            return findings
        if node.id in exception_names:
            findings.add(f"raw exception '{node.id}'")
        if node.id in tainted_names or _is_sensitive_name(node.id):
            findings.add(f"sensitive value '{node.id}'")
        return findings

    if isinstance(node, ast.Call):
        if isinstance(node.func, ast.Attribute):
            findings.update(
                _expression_findings(node.func.value, exception_names, tainted_names)
            )
        for argument in node.args:
            findings.update(
                _expression_findings(argument, exception_names, tainted_names)
            )
        for keyword in node.keywords:
            findings.update(
                _expression_findings(keyword.value, exception_names, tainted_names)
            )
        return findings

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        if "http://" in node.value.lower() or "https://" in node.value.lower():
            findings.add("literal URL")
        return findings

    if isinstance(node, ast.Attribute):
        root = (_root_name(node) or "").lower()
        if node.attr in SENSITIVE_ATTRIBUTES:
            findings.add(f"sensitive attribute '.{node.attr}'")
        elif node.attr in {"name", "summary"} and any(
            marker in root for marker in ("calendar", "entity", "event")
        ):
            findings.add(f"sensitive attribute '.{node.attr}'")
        elif node.attr == "text" and any(
            marker in root
            for marker in ("address", "dropdown", "html", "option", "page", "response")
        ):
            findings.add("sensitive attribute '.text'")

    for child in ast.iter_child_nodes(node):
        findings.update(_expression_findings(child, exception_names, tainted_names))
    return findings


def _assignment_value(node: ast.AST) -> ast.AST | None:
    if isinstance(node, (ast.Assign, ast.AnnAssign, ast.NamedExpr)):
        return node.value
    return None


def _assignment_targets(node: ast.AST):
    targets = []
    if isinstance(node, ast.Assign):
        targets = node.targets
    elif isinstance(node, (ast.AnnAssign, ast.NamedExpr)):
        targets = [node.target]
    pending = list(targets)
    while pending:
        target = pending.pop()
        if isinstance(target, ast.Name):
            yield target.id
        elif isinstance(target, (ast.List, ast.Tuple)):
            pending.extend(target.elts)
        elif isinstance(target, ast.Starred):
            pending.append(target.value)


def _tainted_names(tree: ast.AST, exception_names: set[str]) -> set[str]:
    tainted = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and _is_sensitive_name(node.id)
    }
    assignments = [
        node for node in ast.walk(tree) if _assignment_value(node) is not None
    ]
    changed = True
    while changed:
        changed = False
        for assignment in assignments:
            value = _assignment_value(assignment)
            if value is None or not _expression_findings(
                value, exception_names, tainted
            ):
                continue
            for target in _assignment_targets(assignment):
                if (
                    target.lower() not in SAFE_STATE_NAMES
                    and not target.lower().endswith(SAFE_STATE_SUFFIXES)
                    and target not in tainted
                ):
                    tainted.add(target)
                    changed = True
    return tainted


def _tree_violations(tree: ast.AST, source_name: str):
    exception_names = _exception_names(tree)
    tainted_names = _tainted_names(tree, exception_names)
    violations = []
    for sink in _diagnostic_sinks(tree):
        findings = _expression_findings(sink, exception_names, tainted_names)
        if any(
            keyword.arg in {"exc_info", "stack_info"}
            and not (
                isinstance(keyword.value, ast.Constant)
                and keyword.value.value in {False, None}
            )
            for keyword in sink.keywords
        ) or (
            isinstance(sink.func, ast.Attribute)
            and sink.func.attr == "exception"
            and (_root_name(sink.func.value) or "").lower()
            in {"logger", "logging", "_logger"}
        ):
            findings.add("raw traceback output")
        if findings:
            violations.append((source_name, sink.lineno, sorted(findings)))
    return violations


def test_sensitive_values_do_not_flow_to_diagnostics():
    """Normal print and logger diagnostics must contain summaries only."""
    violations = []
    for source_path in AUDITED_FILES:
        tree = ast.parse(
            source_path.read_text(encoding="utf-8"), filename=str(source_path)
        )
        violations.extend(_tree_violations(tree, source_path.name))

    assert violations == [], violations


def test_gate_detects_sensitive_and_allows_summary_diagnostics():
    """Exercise each protected source class and each supported safe summary."""
    unsafe_samples = (
        "try:\n pass\nexcept Exception as exc:\n print(f'{exc}')\n",
        "print(driver.page_source)\n",
        "print(html)\n",
        "logger.error('URL: %s', response.url)\n",
        "print('https://council.invalid/private')\n",
        "print(postcode, paon, uprn, usrn)\n",
        "selected = address_options[0].text\nlogger.info('%s', selected)\n",
        "print(dict_data, bin_data, collection, raw_text)\n",
        "logger.debug('artifact: %s', json.dumps(data))\n",
        "print(bin_type, collection_date, waste_service)\n",
        "logger.warning('%s', icon_color_mapping)\n",
        "logger.debug('%s', config_entry.data)\n",
        "logger.info('%s', event.summary)\n",
        "print(raw_name, month_txt, start_tag, key, value, payload, row)\n",
        "logger.info('%s', entity._bin_type)\n",
        "logger.exception('collection failed')\n",
        "try:\n pass\nexcept Exception:\n logger.error('failed', exc_info=True)\n",
    )
    safe_samples = (
        "try:\n pass\nexcept Exception as exc:\n print(type(exc).__name__)\n",
        "print(f'Found {len(address_options)} address options')\n",
        "logger.info('HTTP %s', response.status_code)\n",
        "print('Address selected successfully')\n",
        "logger.error('failed', exc_info=False)\n",
    )

    for index, source in enumerate(unsafe_samples):
        tree = ast.parse(source, filename=f"unsafe_{index}.py")
        assert _tree_violations(tree, f"unsafe_{index}.py"), source

    for index, source in enumerate(safe_samples):
        tree = ast.parse(source, filename=f"safe_{index}.py")
        assert _tree_violations(tree, f"safe_{index}.py") == [], source
