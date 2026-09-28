# 🚀 Pull Request

## 📋 요약 (Summary)

<!-- PR의 주요 내용을 간단히 설명해주세요 -->

### 🎯 변경 유형 (Type of Change)
- [ ] 🐛 Bug fix (non-breaking change which fixes an issue)
- [ ] ✨ New feature (non-breaking change which adds functionality)
- [ ] 💥 Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] 📚 Documentation update (문서 업데이트)
- [ ] 🔧 Refactoring (코드 개선, 기능 변경 없음)
- [ ] 🧪 Test (테스트 추가 또는 수정)
- [ ] 🔒 Security (보안 관련 수정)
- [ ] ⚡ Performance (성능 개선)

## 🔗 관련 이슈 (Related Issues)

<!-- 관련 이슈가 있다면 링크해주세요 -->
- Closes #(issue_number)
- Fixes #(issue_number)
- Related to #(issue_number)

## 📝 변경 내용 (Changes Made)

### 🎯 주요 변경사항
<!-- 주요 변경사항을 bullet point로 나열해주세요 -->
-
-
-

### 📁 영향받는 파일들
<!-- 변경된 주요 파일들을 나열해주세요 -->
- `app/`
- `tests/`
- `docs/`

## 🧪 테스트 계획 (Test Plan)

### ✅ 완료된 테스트
- [ ] 단위 테스트 통과 (`make test-unit`)
- [ ] 통합 테스트 통과 (`make test-integration`)
- [ ] API 테스트 통과 (`make test-api`)
- [ ] 코드 품질 검사 통과 (`make lint`)
- [ ] 타입 체킹 통과 (`make typecheck`)
- [ ] 보안 검사 통과 (`make security`)
- [ ] Pre-commit 훅 통과

### 🔍 추가 테스트 사항
<!-- 리뷰어가 확인해야 할 특별한 테스트 사항이 있다면 적어주세요 -->
- [ ]
- [ ]
- [ ]

## 📸 스크린샷 / 데모 (Screenshots/Demo)

<!-- API 변경사항이나 UI 관련 변경이 있다면 스크린샷이나 데모를 첨부해주세요 -->

### API 응답 예시 (API Response Example)
```json
{
  "success": true,
  "message": "...",
  "data": {}
}
```

## 🔄 배포 고려사항 (Deployment Considerations)

### 📋 배포 전 체크리스트
- [ ] 환경변수 변경 필요성 확인
- [ ] 데이터베이스 마이그레이션 필요성 확인
- [ ] 캐시 초기화 필요성 확인
- [ ] 외부 API 의존성 확인
- [ ] 백그라운드 작업 영향도 확인

### ⚠️ 주의사항
<!-- 배포 시 주의해야 할 사항이 있다면 적어주세요 -->
-
-

## 📚 문서 업데이트 (Documentation Updates)

- [ ] README.md 업데이트 필요
- [ ] API.md 업데이트 필요
- [ ] DEVELOPMENT.md 업데이트 필요
- [ ] 인라인 코드 주석 추가/수정

## 🔍 리뷰 요청사항 (Review Focus Areas)

<!-- 리뷰어가 특별히 집중해서 봐주었으면 하는 부분이 있다면 적어주세요 -->
- [ ] 로직의 정확성
- [ ] 성능 최적화
- [ ] 보안 취약점
- [ ] 코드 가독성
- [ ] 테스트 커버리지
- [ ] API 설계
- [ ] 에러 처리
- [ ] 기타: ___

## 📋 체크리스트 (Checklist)

### 🧑‍💻 개발자 체크리스트
- [ ] 코드가 프로젝트의 스타일 가이드를 따름
- [ ] 스스로 코드 리뷰를 완료함
- [ ] 새로운 코드에 적절한 주석을 추가함
- [ ] 변경사항에 대한 테스트를 작성함
- [ ] 모든 테스트가 통과함
- [ ] 기존 테스트가 깨지지 않음
- [ ] 변경사항이 문서에 반영됨

### 🔧 코드 품질 체크리스트
- [ ] Black 포맷팅 적용 (`make format`)
- [ ] Import 정렬 (isort) 적용
- [ ] Flake8 린팅 통과
- [ ] MyPy 타입 체킹 통과
- [ ] Bandit 보안 검사 통과
- [ ] Pre-commit 훅 모두 통과

### 🧪 테스트 체크리스트
- [ ] 단위 테스트 커버리지 80% 이상 유지
- [ ] 새로운 기능에 대한 테스트 작성
- [ ] Edge case 테스트 포함
- [ ] API 테스트 포함 (해당하는 경우)
- [ ] 오류 상황 테스트 포함

## 🚀 배포 후 계획 (Post-Deployment Plan)

- [ ] 로그 모니터링
- [ ] 성능 지표 확인
- [ ] 에러율 모니터링
- [ ] 사용자 피드백 수집

## 📝 추가 정보 (Additional Information)

<!-- 기타 추가적으로 공유하고 싶은 정보가 있다면 적어주세요 -->

---

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
