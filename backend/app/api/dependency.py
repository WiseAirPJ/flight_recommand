from app.services.llm_service import LLMService


def get_llm_service() -> LLMService:
    """LLM 서비스 인스턴스 반환"""
    return LLMService()
