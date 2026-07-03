"""
API Keys 관리 라우터

외부 서비스(네이버 검색 API) 키를 config/api-keys.json에 저장·조회하고
서버 시작 시 os.environ으로 로드한다. (구 routers/settings.py에서 분리)
경로는 기존과 동일하게 /api/settings/api-keys 를 유지한다.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
from pathlib import Path
import logging
import json
import os
from app.dependencies import verify_api_key_dependency
from app.config import Config

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_api_keys_path() -> str:
    """API 키 설정 파일 경로"""
    config_dir = str(Path(Config.STOCK_CONFIG_PATH).parent)
    return os.path.join(config_dir, "api-keys.json")


def _load_api_keys() -> Dict[str, str]:
    """api-keys.json에서 API 키 로드"""
    keys_path = _get_api_keys_path()
    if not os.path.exists(keys_path):
        return {}
    try:
        with open(keys_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load api-keys.json: {e}")
        return {}


def _save_api_keys(keys: Dict[str, str]):
    """api-keys.json에 API 키 저장"""
    keys_path = _get_api_keys_path()
    config_dir = os.path.dirname(keys_path)
    if not os.path.exists(config_dir):
        os.makedirs(config_dir, exist_ok=True)
    with open(keys_path, "w", encoding="utf-8") as f:
        json.dump(keys, f, indent=2, ensure_ascii=False)


def load_api_keys_to_env():
    """저장된 API 키를 os.environ에 로드 (서버 시작 시 호출)"""
    keys = _load_api_keys()
    count = 0
    for key, value in keys.items():
        if value and not value.startswith("your_"):
            os.environ[key] = value
            count += 1
    if count > 0:
        logger.info(f"Loaded {count} API keys from api-keys.json")
        # Config 클래스 속성도 업데이트
        if "NAVER_CLIENT_ID" in keys:
            Config.NAVER_CLIENT_ID = keys["NAVER_CLIENT_ID"]
        if "NAVER_CLIENT_SECRET" in keys:
            Config.NAVER_CLIENT_SECRET = keys["NAVER_CLIENT_SECRET"]


class ApiKeysUpdate(BaseModel):
    """API 키 업데이트 요청 모델"""
    NAVER_CLIENT_ID: Optional[str] = None
    NAVER_CLIENT_SECRET: Optional[str] = None


@router.get("/api-keys")
async def get_api_keys(raw: bool = False) -> Dict[str, Any]:
    """
    저장된 API 키 조회

    **Query Parameters:**
    - raw: true면 원본 값 반환, false면 마스킹 처리 (기본: false)

    **Status Codes:**
    - 200: Success
    """
    keys = _load_api_keys()

    result = {}
    for key in ["NAVER_CLIENT_ID", "NAVER_CLIENT_SECRET"]:
        value = keys.get(key, "") or os.getenv(key, "")
        if value and not value.startswith("your_"):
            result[key] = value if raw else value[:4] + "*" * max(0, len(value) - 4)
        else:
            result[key] = ""

    has_naver = bool(result["NAVER_CLIENT_ID"] and result["NAVER_CLIENT_SECRET"])

    return {
        "keys": result,
        "configured": {
            "naver": has_naver,
        }
    }


@router.put("/api-keys")
async def update_api_keys(
    data: ApiKeysUpdate,
    api_key: str = Depends(verify_api_key_dependency)
) -> Dict[str, Any]:
    """
    API 키 저장 및 즉시 적용

    **Request Body:**
    - NAVER_CLIENT_ID: 네이버 API Client ID
    - NAVER_CLIENT_SECRET: 네이버 API Client Secret

    **Status Codes:**
    - 200: Successfully saved
    - 500: Server error
    """
    try:
        # 현재 저장된 키 로드
        current_keys = _load_api_keys()

        # 업데이트할 키만 갱신 (None이면 기존 값 유지)
        update_dict = data.model_dump(exclude_unset=True)
        for key, value in update_dict.items():
            if value is not None:
                current_keys[key] = value

        # 파일에 저장
        _save_api_keys(current_keys)

        # os.environ에 즉시 반영 (실행 중인 서비스가 바로 사용할 수 있도록)
        for key, value in current_keys.items():
            if value and not value.startswith("your_"):
                os.environ[key] = value
                logger.info(f"Updated env key: {key}")

        # Config 클래스 속성 업데이트
        if "NAVER_CLIENT_ID" in current_keys:
            Config.NAVER_CLIENT_ID = current_keys["NAVER_CLIENT_ID"]
        if "NAVER_CLIENT_SECRET" in current_keys:
            Config.NAVER_CLIENT_SECRET = current_keys["NAVER_CLIENT_SECRET"]

        logger.info("API keys saved and applied successfully")
        return {"message": "API 키가 저장되었습니다", "updated": list(update_dict.keys())}

    except Exception as e:
        logger.error(f"Failed to save API keys: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to save API keys")
