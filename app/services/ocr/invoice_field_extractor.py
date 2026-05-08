from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class AmountCandidate:
    value: str
    line: str
    score: float
    reason: str


def normalize_ocr_text(raw_text: str) -> str:
    text = str(raw_text or "")
    repl = {
        "：": ":",
        "（": "(",
        "）": ")",
        "￥": "CNY ",
        "¥": "CNY ",
    }
    for old, new in repl.items():
        text = text.replace(old, new)
    text = re.sub(r"人民币", "CNY", text, flags=re.IGNORECASE)
    text = re.sub(r"[，、；;|]+", " ", text)
    text = re.sub(r"(\d),(?=\d{3}(?:\D|$))", r"\1", text)
    text = re.sub(r"[ \t]+", " ", text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip())


def normalize_invoice_date(raw_date: str) -> str:
    value = str(raw_date or "").strip()
    value = re.sub(r"\s+", "", value)
    patterns = (
        r"(?P<y>\d{4})年(?P<m>\d{1,2})月(?P<d>\d{1,2})日",
        r"(?P<y>\d{4})[-/](?P<m>\d{1,2})[-/](?P<d>\d{1,2})",
    )
    for pattern in patterns:
        match = re.search(pattern, value)
        if not match:
            continue
        y, m, d = int(match.group("y")), int(match.group("m")), int(match.group("d"))
        if 1 <= m <= 12 and 1 <= d <= 31:
            return f"{y:04d}-{m:02d}-{d:02d}"
    return ""


def extract_invoice_number(lines: list[str]) -> tuple[str, float]:
    patterns = (
        r"(?:发票号码|发票号)\s*:?\s*([0-9A-Za-z]{8,})",
        r"号码\s*:?\s*([0-9A-Za-z]{8,})",
    )
    for line in lines:
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                return match.group(1).strip(), 0.92
    return "", 0.0


def extract_invoice_date(lines: list[str]) -> tuple[str, float]:
    for line in lines:
        if not re.search(r"(开票日期|日期)", line):
            continue
        normalized = normalize_invoice_date(line)
        if normalized:
            return normalized, 0.9
    for line in lines:
        normalized = normalize_invoice_date(line)
        if normalized:
            return normalized, 0.75
    return "", 0.0


def extract_named_party(lines: list[str], *, party: str) -> tuple[str, float]:
    if party == "buyer":
        keys = (r"购买方", r"购方", r"购买方名称", r"名称")
    else:
        keys = (r"销售方", r"销方", r"销售方名称")
    for idx, line in enumerate(lines):
        if not any(re.search(k, line) for k in keys):
            continue
        inline = line.strip()
        inline = re.sub(
            r"^(?:购买方信息|购买方名称|购买方|购方名称|购方|销售方信息|销售方名称|销售方|销方名称|销方)\s*:?\s*",
            "",
            inline,
        )
        inline = re.sub(r"^名称\s*:?\s*", "", inline).strip()
        inline = re.sub(r"\b(?:税号|纳税人识别号|地址电话|开户行及账号)\b.*$", "", inline).strip()
        if inline and inline not in {"购买方", "销售方", "名称"} and "信息" not in inline:
            return inline, 0.84
        if idx + 1 < len(lines):
            nxt = lines[idx + 1].strip()
            nxt = re.sub(r"^(?:名称)\s*:?\s*", "", nxt)
            nxt = re.sub(r"\b(?:税号|纳税人识别号|地址电话|开户行及账号)\b.*$", "", nxt).strip()
            if nxt and not re.search(r"(税额|金额|日期|号码|信息)", nxt):
                return nxt, 0.78
    # Fallback for OCR that keeps "购买方信息 名称 XXX" in one line.
    compact_text = "\n".join(lines)
    if party == "buyer":
        match = re.search(r"(?:购买方(?:信息)?\s*名称?)\s*:?\s*([^\n]{2,40})", compact_text)
    else:
        match = re.search(r"(?:销售方(?:信息)?\s*名称?)\s*:?\s*([^\n]{2,40})", compact_text)
    if match:
        value = re.sub(r"\b(?:税号|纳税人识别号|地址电话|开户行及账号)\b.*$", "", match.group(1)).strip()
        if value:
            return value, 0.76
    return "", 0.0


def _extract_money_from_line(line: str) -> list[str]:
    matches = re.findall(r"(\d{1,3}(?:,\d{3})*(?:\.\d{1,2})|\d+(?:\.\d{1,2}))", line)
    return [m.replace(",", "") for m in matches]


def extract_amount_candidates(lines: list[str]) -> list[AmountCandidate]:
    candidates: list[AmountCandidate] = []
    for line in lines:
        values = _extract_money_from_line(line)
        if not values:
            continue
        for value in values:
            score = 0.45
            reason = []
            if re.search(r"价税合计", line):
                score += 0.5
                reason.append("价税合计")
            if re.search(r"小写", line):
                score += 0.3
                reason.append("小写")
            if re.search(r"(合计金额|金额|合计)", line):
                score += 0.2
                reason.append("金额词")
            if re.search(r"税额", line):
                score -= 0.45
            if re.search(r"(单价|数量|税率)", line):
                score -= 0.4
            candidates.append(
                AmountCandidate(
                    value=value,
                    line=line,
                    score=max(0.0, min(1.0, score)),
                    reason="+".join(reason) or "generic",
                )
            )
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates


def select_best_total_amount(candidates: list[AmountCandidate]) -> tuple[str, float, bool, str]:
    if not candidates:
        return "", 0.0, True, "未找到金额候选"
    best = candidates[0]
    if len(candidates) == 1:
        return best.value, best.score, best.score < 0.78, ""
    second = candidates[1]
    if best.score - second.score < 0.15:
        return best.value, best.score, True, "金额候选不唯一，需要人工复核"
    return best.value, best.score, best.score < 0.78, ""
