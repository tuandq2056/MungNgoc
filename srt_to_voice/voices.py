"""
Quản lý các cấu hình và preset giọng đọc tiếng Việt đa dạng.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class VoiceProfile:
    name: str
    edge_voice: str
    description: str
    gender: str
    pitch: str = "+0Hz"
    rate: str = "+0%"
    volume: str = "+0%"


# Danh sách các preset giọng đọc phong phú
VOICE_PRESETS: dict[str, VoiceProfile] = {
    # Nhóm giọng Nữ
    "nu_chuan": VoiceProfile(
        name="nu_chuan",
        edge_voice="vi-VN-HoaiMyNeural",
        description="Nữ miền Bắc chuẩn, tự nhiên, ấm áp (Mặc định)",
        gender="Female",
        pitch="+0Hz",
        rate="+0%",
    ),
    "nu_tre": VoiceProfile(
        name="nu_tre",
        edge_voice="vi-VN-HoaiMyNeural",
        description="Nữ trẻ, trong trẻo, vui tươi",
        gender="Female",
        pitch="+6Hz",
        rate="+5%",
    ),
    "nu_tram": VoiceProfile(
        name="nu_tram",
        edge_voice="vi-VN-HoaiMyNeural",
        description="Nữ trầm, chững chạc, giàu cảm xúc",
        gender="Female",
        pitch="-5Hz",
        rate="-3%",
    ),
    "nu_co_trang": VoiceProfile(
        name="nu_co_trang",
        edge_voice="vi-VN-HoaiMyNeural",
        description="Nữ phong cách cổ trang, truyền cảm, nhịp nhẹ nhàng",
        gender="Female",
        pitch="+2Hz",
        rate="-5%",
    ),

    # Nhóm giọng Nam
    "nam_thuyet_minh": VoiceProfile(
        name="nam_thuyet_minh",
        edge_voice="vi-VN-NamMinhNeural",
        description="Nam thuyết minh phim, trầm ấm, uy quyền",
        gender="Male",
        pitch="-5Hz",
        rate="-2%",
    ),
    "nam_chuan": VoiceProfile(
        name="nam_chuan",
        edge_voice="vi-VN-NamMinhNeural",
        description="Nam miền Bắc chuẩn, rõ ràng, dứt khoát",
        gender="Male",
        pitch="+0Hz",
        rate="+0%",
    ),
    "nam_tre": VoiceProfile(
        name="nam_tre",
        edge_voice="vi-VN-NamMinhNeural",
        description="Nam trẻ, thanh niên, hiện đại",
        gender="Male",
        pitch="+6Hz",
        rate="+5%",
    ),
    "nam_co_trang": VoiceProfile(
        name="nam_co_trang",
        edge_voice="vi-VN-NamMinhNeural",
        description="Nam phong cách kiếm hiệp, kể chuyện, trầm tĩnh",
        gender="Male",
        pitch="-3Hz",
        rate="-6%",
    ),
}

# Alias tiện lợi
ALIASES: dict[str, str] = {
    "hoaimy": "nu_chuan",
    "female": "nu_chuan",
    "nu": "nu_chuan",
    "namminh": "nam_chuan",
    "male": "nam_thuyet_minh",
    "nam": "nam_thuyet_minh",
}


def get_voice_profile(voice_key: str) -> VoiceProfile:
    """Lấy cấu hình giọng đọc theo tên preset hoặc alias."""
    key = voice_key.lower().strip()
    key = ALIASES.get(key, key)

    if key in VOICE_PRESETS:
        return VOICE_PRESETS[key]

    # Nếu truyền trực tiếp mã giọng Edge-TTS (ví dụ: vi-VN-NamMinhNeural)
    if "vi-vn" in key:
        gender = "Female" if "hoaimy" in key else "Male"
        return VoiceProfile(
            name=key,
            edge_voice=voice_key,
            description=f"Giọng Edge-TTS tùy chỉnh: {voice_key}",
            gender=gender,
        )

    # Mặc định trả về nu_chuan
    return VOICE_PRESETS["nu_chuan"]


def list_available_voices() -> list[dict]:
    """Trả về danh sách tất cả các giọng có sẵn dưới dạng dictionary."""
    results = []
    for key, p in VOICE_PRESETS.items():
        results.append({
            "key": key,
            "description": p.description,
            "gender": p.gender,
            "edge_voice": p.edge_voice,
            "pitch": p.pitch,
            "rate": p.rate,
        })
    return results
