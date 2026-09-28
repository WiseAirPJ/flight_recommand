# Flight map backend

Python 3.12 + FastAPI. 실행, 설정, API 계약, 마이그레이션, Celery와 검증 방법은 [루트 README](../README.md)를 따릅니다.

이 디렉터리에서 `uvicorn app.main:app --reload`로 실행하고 `pytest`로 테스트합니다. 개발용 `.env`는 루트의 `.env.example`을 이 디렉터리로 복사합니다. 기본 설정은 유료 공급자 호출과 예시 가격 반환을 모두 비활성화합니다.
