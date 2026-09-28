"""보안 관련 유틸리티 (JWT, 비밀번호 해싱)"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")


def create_access_token(
    data: Dict[str, Any], expires_delta: Optional[timedelta] = None
) -> str:
    """
    JWT 액세스 토큰 생성

    Args:
        data: 토큰에 포함할 데이터 (예: {"sub": user_id})
        expires_delta: 토큰 만료 시간 (None이면 기본값 사용)

    Returns:
        str: 인코딩된 JWT 토큰

    Example:
        >>> token = create_access_token({"sub": "user123"})
        >>> # 만료시간 커스터마이징
        >>> token = create_access_token(
        ...     {"sub": "user123"},
        ...     expires_delta=timedelta(hours=1)
        ... )
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    JWT 토큰 검증 및 디코딩

    Args:
        token: 검증할 JWT 토큰

    Returns:
        Dict[str, Any] | None: 디코딩된 페이로드 (실패시 None)

    Example:
        >>> payload = verify_token(token)
        >>> if payload:
        ...     user_id = payload.get("sub")
    """
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        return payload
    except JWTError:
        return None


def get_password_hash(password: str) -> str:
    """
    비밀번호 해싱

    Args:
        password: 평문 비밀번호

    Returns:
        str: 해싱된 비밀번호

    Example:
        >>> hashed = get_password_hash("mypassword123")
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증

    Args:
        plain_password: 입력된 평문 비밀번호
        hashed_password: 저장된 해시 비밀번호

    Returns:
        bool: 비밀번호 일치 여부

    Example:
        >>> is_valid = verify_password("mypassword123", stored_hash)
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """
    리프레시 토큰 생성 (장기간 유효)

    Args:
        data: 토큰에 포함할 데이터

    Returns:
        str: 리프레시 토큰

    Example:
        >>> refresh_token = create_refresh_token({"sub": "user123"})
    """
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 7일 유효
    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM
    )
    return encoded_jwt


def decode_token(token: str) -> Optional[str]:
    """
    토큰에서 사용자 ID 추출

    Args:
        token: JWT 토큰

    Returns:
        Optional[str]: 사용자 ID (sub 클레임)

    Example:
        >>> user_id = decode_token(token)
    """
    payload = verify_token(token)
    if payload:
        return payload.get("sub")
    return None
