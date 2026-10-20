"""Danh sách loại lỗi cờ đỏ chọn khi quét + ánh xạ sang MÃ LỖI trong sổ thi đua (DANH MUC LOI).

Muốn đổi lỗi hoặc đổi mã tương ứng: chỉ sửa VIOLATION_TYPES bên dưới (code = None nếu sổ không có lỗi tương ứng).
"""

# (tên lỗi hiển thị cho cờ đỏ, mã lỗi trong sổ thi đua hoặc None)
VIOLATION_TYPES: list[tuple[str, str | None]] = [
    ("Không đồng phục",       "L04"),
    ("Đi trễ",                "L03"),
    ("Dùng điện thoại",       "L06"),
    ("Không đeo thẻ",         None),
    ("Không đội mũ bảo hiểm", "L19"),
    ("Gây mất trật tự",       "L02"),
    ("Khác",                  None),
]

TYPE_NAMES = [name for name, _ in VIOLATION_TYPES]
TYPE_TO_CODE = dict(VIOLATION_TYPES)

# Điểm trừ theo Phụ lục 01 (sheet DANH MUC LOI). L25/L26: nhập tay 20–30 nên để None.
CODE_POINTS: dict[str, int | None] = {
    "L01": 1, "L02": 1, "L03": 2, "L04": 2, "L05": 2, "L06": 2, "L07": 5, "L08": 5, "L09": 5,
    "L10": 10, "L11": 10, "L12": 10, "L13": 10, "L14": 10, "L15": 10, "L16": 10, "L17": 10,
    "L18": 20, "L19": 20, "L20": 20, "L21": 20, "L22": 20, "L23": 20, "L24": 20,
    "L25": None, "L26": None,
}
