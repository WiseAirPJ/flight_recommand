# 개발 환경

Python 3.14, uv 0.12.19를 사용합니다. `.python-version`은 Python 계열을 지정하고 `pyproject.toml`의 `required-version`은 uv 버전을 지정합니다. 현재 검증 범위는 Python 3.14입니다.

uv 설치는 [공식 안내](https://docs.astral.sh/uv/getting-started/installation/)를 따릅니다. standalone 설치라면 `uv self update 0.12.19`로 버전을 맞출 수 있고, 다른 설치 방식은 해당 패키지 관리자를 사용합니다.

Python 3.14를 기준으로 삼습니다. 3.12에 머물러야 하는 제품 제약은 없으며, [Python 공식 지원 현황](https://devguide.python.org/versions/)에서 3.14는 버그 수정 지원 단계입니다. 기존 고정 버전의 pydantic-core, psycopg2-binary, aiohttp는 3.14 설치용 wheel이 없어 관련 패키지도 함께 갱신했습니다.

모든 명령은 `backend/`에서 실행합니다.

```sh
uv python install
uv sync --locked
make setup-dev
make dev
```

`uv sync --locked`는 커밋된 의존성 잠금 파일을 사용하고 선언과 잠금이 다르면 실패합니다. 개발 도구는 `dev` 그룹에 기본 포함됩니다. `.venv` 활성화 없이 `uv run --locked …`로 실행할 수 있습니다. `.env`가 이미 있다면 `make setup-dev`는 덮어쓰지 않습니다.

## 일상 작업

| 작업 | 명령 |
| --- | --- |
| 서버 | `make dev` |
| 전체 검증 | `make check` |
| 테스트만 | `uv run --locked pytest` |
| 형식 자동 수정 | `make format` |
| DB 마이그레이션 | `make migrate` |
| 수집 worker | `make worker` |
| 예약 수집 | `make beat` |
| 선택적 Git 훅 설치 | `make install-pre-commit` |

`make check`와 CI는 잠금 파일 일치, Black·isort·치명적 flake8 오류, 전체 테스트, 핵심 경로 커버리지 80%를 확인합니다. 선택적인 `make typecheck`와 `make security`는 기존 코드의 추가 점검용이며 CI 통과 기준에 포함되지 않습니다. `make check`는 소스 형식을 자동으로 수정하지 않습니다.

기존 Makefile에 있던 미설치 도구·없는 파일에 의존하는 Docker, Flower, 병렬 테스트, 배포 태그 명령은 제거했습니다. 전체 의존성을 일괄 최신화하거나 자동 푸시하는 동작도 없습니다. 필요한 명령은 `make help`로 확인합니다.

## 의존성 변경

`requirements*.txt`를 직접 관리하지 않습니다. `pyproject.toml`이 의존성 선언의 기준이고 `uv.lock`이 플랫폼별 간접 의존성까지 잠급니다. 두 파일의 변경을 함께 검토·커밋합니다.

```sh
uv add 패키지명
uv add --dev 개발도구명
uv remove 패키지명
# 특정 패키지만 업데이트
uv lock --upgrade-package 패키지명
uv sync --locked
make check
```

고정한 직접 의존성의 버전을 변경하려면 `uv add '패키지명==새버전'`처럼 선언도 갱신합니다. 기본 `uv lock`은 기존 잠금 버전을 우선 유지합니다. Python 3.14 지원에 맞춰 FastAPI·Pydantic·SQLAlchemy·PostgreSQL 드라이버·aiohttp·Celery와 테스트/형식 도구를 갱신했습니다. 잠금 파일 변경은 전체 테스트와 운영 환경 설치로 검증합니다.

pip 입력만 받는 외부 도구에는 `make export-requirements`로 `dist/requirements.txt`를 생성합니다. 이 파일은 배포용 파생 산출물이며 직접 수정하거나 커밋하지 않습니다.

## 운영 의존성만 설치

```sh
uv sync --locked --no-dev
uv run --locked --no-dev uvicorn app.main:app --host 0.0.0.0 --port 8000
```

`uv run`에도 `--no-dev`를 지정해야 개발 그룹을 다시 동기화하지 않습니다. 설정·운영 마이그레이션·공급자 조건은 루트 README를 따릅니다.

## CI

GitHub Actions는 `astral-sh/setup-uv`로 동일한 uv를 설치하고 `backend/uv.lock` 기준으로 다운로드 캐시를 관리합니다. Python은 `backend/.python-version`에 맞춰 설치하고, 설치와 검사 명령에 `--locked`를 사용합니다.

참고: [uv 프로젝트 전환](https://docs.astral.sh/uv/guides/migration/pip-to-project/), [공식 GitHub Actions 연동](https://docs.astral.sh/uv/guides/integration/github/).
