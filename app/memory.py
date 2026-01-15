"""
用户偏好记忆模块
"""
import json
from pathlib import Path
from typing import Optional
from .schemas import UserProfile
from .utils import get_memory_dir, logger


def get_profile_path(user_id: str) -> Path:
    """获取用户配置文件路径"""
    return get_memory_dir() / f"profile_{user_id}.json"


def load_user_profile(user_id: str) -> UserProfile:
    """
    加载用户偏好配置
    
    Args:
        user_id: 用户ID
    
    Returns:
        UserProfile 实例
    """
    profile_path = get_profile_path(user_id)
    
    if profile_path.exists():
        try:
            with open(profile_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.info(f"加载用户配置: {user_id}")
            return UserProfile(**data)
        except Exception as e:
            logger.warning(f"加载用户配置失败: {e}，使用默认配置")
    
    # 返回默认配置
    return UserProfile(user_id=user_id)


def save_user_profile(profile: UserProfile) -> None:
    """
    保存用户偏好配置
    
    Args:
        profile: 用户配置
    """
    profile_path = get_profile_path(profile.user_id)
    
    with open(profile_path, 'w', encoding='utf-8') as f:
        json.dump(profile.model_dump(), f, ensure_ascii=False, indent=2)
    
    logger.info(f"保存用户配置: {profile.user_id} -> {profile_path}")


def update_user_profile(
    user_id: str,
    language: Optional[str] = None,
    output_style: Optional[str] = None,
    format: Optional[str] = None,
    tone: Optional[str] = None
) -> UserProfile:
    """
    更新用户偏好配置
    
    Args:
        user_id: 用户ID
        language: 语言偏好
        output_style: 输出风格
        format: 输出格式
        tone: 语气
    
    Returns:
        更新后的 UserProfile
    """
    profile = load_user_profile(user_id)
    
    if language is not None:
        profile.language = language
    if output_style is not None:
        profile.output_style = output_style
    if format is not None:
        profile.format = format
    if tone is not None:
        profile.tone = tone
    
    save_user_profile(profile)
    return profile


def get_profile_prompt(user_id: str) -> str:
    """
    根据用户偏好生成系统提示
    
    Args:
        user_id: 用户ID
    
    Returns:
        系统提示字符串
    """
    profile = load_user_profile(user_id)
    
    style_map = {
        "简洁": "回答要简洁明了，突出重点",
        "详细": "回答要详细全面，包含必要的解释和示例",
        "学术": "回答要严谨学术，使用专业术语，引用充分"
    }
    
    tone_map = {
        "友好": "使用友好、亲切的语气",
        "专业": "使用专业、客观的语气",
        "正式": "使用正式、严肃的语气"
    }
    
    prompts = [
        f"请使用{profile.language}回答。",
        style_map.get(profile.output_style, style_map["详细"]),
        tone_map.get(profile.tone, tone_map["专业"])
    ]
    
    if profile.format == "markdown":
        prompts.append("请使用 Markdown 格式组织回答，适当使用标题、列表等。")
    
    return " ".join(prompts)

