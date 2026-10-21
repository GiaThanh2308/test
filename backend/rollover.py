"""Chuyển năm học: lớp 10→11, 11→12, lớp 12 ra trường (ẩn, giữ lịch sử).
Chỉ tính kế hoạch ở đây (không đụng cơ sở dữ liệu) để xem trước và kiểm thử được."""
import re
from collections import Counter
from datetime import date
from typing import Optional

CLASS_RE = re.compile(r"^\s*(\d{1,2})(.*)$")


def next_class(class_name: Optional[str]) -> tuple[str, Optional[str]]:
    """→ ("promote", lớp mới) | ("graduate", None) | ("skip", None) nếu tên lớp không đúng dạng khối 10–12."""
    m = CLASS_RE.match(class_name or "")
    if not m:
        return "skip", None
    khoi, rest = int(m.group(1)), m.group(2).rstrip()  # giữ nguyên khoảng trắng: "10 Tin" → "11 Tin"
    if khoi == 12:
        return "graduate", None
    if khoi in (10, 11):
        return "promote", f"{khoi + 1}{rest}"
    return "skip", None


def next_school_year(label: str) -> str:
    a, b = (int(x) for x in label.split("-"))
    return f"{a + 1}-{b + 1}"


def default_school_year(week1_start: date) -> str:
    return f"{week1_start.year}-{week1_start.year + 1}"


def plan_rollover(students: list[dict]) -> dict:
    """students: [{id, class_name}] đang học. Trả về kế hoạch + số liệu xem trước."""
    promote, graduate, skip = [], [], []
    for s in students:
        action, new_class = next_class(s["class_name"])
        if action == "promote":
            promote.append({"id": s["id"], "old": s["class_name"], "new": new_class})
        elif action == "graduate":
            graduate.append({"id": s["id"], "old": s["class_name"]})
        else:
            skip.append({"id": s["id"], "class_name": s["class_name"]})
    mapping = Counter((p["old"], p["new"]) for p in promote)
    return {
        "promote": promote, "graduate": graduate, "skip": skip,
        "summary": {
            "promote": len(promote), "graduate": len(graduate), "skip": len(skip),
            "class_map": [{"from": a, "to": b, "students": n} for (a, b), n in sorted(mapping.items())],
            "graduate_classes": sorted(Counter(g["old"] for g in graduate).items()),
            "skip_classes": sorted({s["class_name"] for s in skip if s["class_name"]}),
        },
    }
