# 🛡️ GitHub Branch Protection 설정 가이드

GitHub 리포지토리의 코드 품질과 안정성을 보장하기 위한 브랜치 보호 규칙 설정 가이드입니다.

## 📋 목차

- [🎯 보호 대상 브랜치](#-보호-대상-브랜치)
- [🔒 Main 브랜치 보호 규칙](#-main-브랜치-보호-규칙)
- [🚧 Develop 브랜치 보호 규칙](#-develop-브랜치-보호-규칙)
- [⚙️ 설정 방법](#️-설정-방법)
- [👥 권한 관리](#-권한-관리)
- [📋 체크리스트](#-체크리스트)

## 🎯 보호 대상 브랜치

### 🏛️ Main 브랜치 (`main`)
- **목적**: 운영 환경 배포용 안정 브랜치
- **보호 수준**: 최고 (Critical)
- **접근**: 관리자 및 승인된 개발자만

### 🔄 Develop 브랜치 (`develop`)
- **목적**: 개발 통합 브랜치
- **보호 수준**: 높음 (High)
- **접근**: 모든 개발자 (리뷰 필수)

## 🔒 Main 브랜치 보호 규칙

### ✅ 필수 설정

```yaml
Branch Protection Rules for 'main':

✅ Require a pull request before merging
  ✅ Require approvals: 2
  ✅ Dismiss stale PR approvals when new commits are pushed
  ✅ Require review from code owners
  ✅ Restrict pushes that create new files

✅ Require status checks to pass before merging
  ✅ Require branches to be up to date before merging
  ✅ Required status checks:
    - 🔍 Code Quality
    - 🧪 Unit Tests
    - 🔗 Integration Tests
    - 🛡️ Security Scan
    - ⚡ Performance Test (optional)

✅ Require conversation resolution before merging

✅ Require signed commits

✅ Require linear history

✅ Include administrators (관리자도 규칙 적용)

✅ Restrict pushes (직접 푸시 금지)
  ✅ Restrict pushes to specified users/teams:
    - @repository-admins
    - @senior-developers

✅ Require deployments to succeed (배포 환경 설정 시)
  ✅ Required deployment environments:
    - staging
```

### 🏷️ 필수 Status Checks

GitHub Actions의 다음 작업들이 성공해야 합니다:

1. **🔍 Code Quality**
   - Black 포맷팅 검사
   - isort import 정렬 검사
   - Flake8 린팅
   - MyPy 타입 체킹
   - Pydocstyle 문서 검사

2. **🧪 Unit Tests**
   - 모든 단위 테스트 통과
   - 커버리지 80% 이상

3. **🔗 Integration Tests**
   - 통합 테스트 통과
   - API 테스트 통과

4. **🛡️ Security Scan**
   - Bandit 보안 검사
   - 의존성 취약점 검사
   - 비밀정보 노출 검사

## 🚧 Develop 브랜치 보호 규칙

### ✅ 필수 설정

```yaml
Branch Protection Rules for 'develop':

✅ Require a pull request before merging
  ✅ Require approvals: 1
  ✅ Dismiss stale PR approvals when new commits are pushed
  ✅ Require review from code owners (optional)

✅ Require status checks to pass before merging
  ✅ Require branches to be up to date before merging
  ✅ Required status checks:
    - 🔍 Code Quality
    - 🧪 Unit Tests
    - 🔗 Integration Tests

✅ Require conversation resolution before merging

✅ Require linear history (optional)

⬜ Include administrators (관리자는 예외 허용)

✅ Restrict pushes (제한적 직접 푸시 허용)
  ✅ Restrict pushes to specified users/teams:
    - @all-developers
```

## ⚙️ 설정 방법

### 1️⃣ GitHub 웹 인터페이스에서 설정

1. **Repository → Settings → Branches**로 이동
2. **Add rule** 클릭
3. 브랜치 이름 패턴 입력 (`main`, `develop`)
4. 보호 규칙 설정
5. **Create** 클릭

### 2️⃣ 상세 설정 단계

#### 📋 Main 브랜치 설정

```bash
# 1. Repository Settings 페이지로 이동
https://github.com/your-username/flight_recommand/settings/branches

# 2. "Add rule" 클릭

# 3. Branch name pattern: main

# 4. 다음 옵션들 체크:
☑️ Require a pull request before merging
  ☑️ Require approvals (2)
  ☑️ Dismiss stale PR approvals when new commits are pushed
  ☑️ Require review from code owners

☑️ Require status checks to pass before merging
  ☑️ Require branches to be up to date before merging
  Status checks:
    - code-quality
    - unit-tests
    - integration-tests
    - security-scan

☑️ Require conversation resolution before merging
☑️ Require signed commits
☑️ Require linear history
☑️ Include administrators
☑️ Restrict pushes
```

#### 📋 Develop 브랜치 설정

```bash
# Branch name pattern: develop

# 옵션 설정:
☑️ Require a pull request before merging
  ☑️ Require approvals (1)
  ☑️ Dismiss stale PR approvals when new commits are pushed

☑️ Require status checks to pass before merging
  ☑️ Require branches to be up to date before merging
  Status checks:
    - code-quality
    - unit-tests
    - integration-tests

☑️ Require conversation resolution before merging
☐ Include administrators
```

### 3️⃣ CLI를 통한 설정 (GitHub CLI)

```bash
# GitHub CLI 설치 및 로그인
gh auth login

# Main 브랜치 보호 규칙 설정
gh api repos/:owner/:repo/branches/main/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["code-quality","unit-tests","integration-tests","security-scan"]}' \
  --field enforce_admins=true \
  --field required_pull_request_reviews='{"required_approving_review_count":2,"dismiss_stale_reviews":true,"require_code_owner_reviews":true}' \
  --field restrictions='null'

# Develop 브랜치 보호 규칙 설정
gh api repos/:owner/:repo/branches/develop/protection \
  --method PUT \
  --field required_status_checks='{"strict":true,"contexts":["code-quality","unit-tests","integration-tests"]}' \
  --field enforce_admins=false \
  --field required_pull_request_reviews='{"required_approving_review_count":1,"dismiss_stale_reviews":true}' \
  --field restrictions='null'
```

## 👥 권한 관리

### 🏛️ Repository 역할 정의

```yaml
Repository Roles:

👑 Admin:
  - 모든 설정 변경 권한
  - 브랜치 보호 규칙 무시 가능 (긴급 상황)
  - 사용자: @repository-owner, @tech-lead

🔧 Maintainer:
  - 코드 리뷰 승인 권한
  - PR 병합 권한
  - 사용자: @senior-developers

💻 Developer:
  - 코드 기여 권한
  - PR 생성 권한
  - 사용자: @all-developers

👀 Reviewer:
  - 읽기 권한
  - 리뷰 권한
  - 사용자: @external-reviewers
```

### 🔐 CODEOWNERS 파일 설정

`.github/CODEOWNERS` 파일 생성:

```bash
# Global owners
* @repository-owner @tech-lead

# Backend code
/app/ @backend-team @senior-developers
/tests/ @backend-team

# Configuration files
*.yml @devops-team @tech-lead
*.yaml @devops-team @tech-lead
Dockerfile @devops-team

# Documentation
*.md @tech-lead @documentation-team

# GitHub workflows
/.github/ @devops-team @tech-lead

# Sensitive files
.env.example @tech-lead @security-team
requirements*.txt @tech-lead @backend-team
```

## 📋 체크리스트

### ✅ 설정 완료 체크리스트

#### 🏛️ Main 브랜치
- [ ] PR 필수 설정 (2명 승인)
- [ ] Status checks 설정 (4개 필수)
- [ ] 관리자 포함 설정
- [ ] 직접 푸시 금지
- [ ] 서명된 커밋 필수
- [ ] Linear history 필수
- [ ] 대화 해결 필수

#### 🚧 Develop 브랜치
- [ ] PR 필수 설정 (1명 승인)
- [ ] Status checks 설정 (3개 필수)
- [ ] 직접 푸시 제한
- [ ] 대화 해결 필수

#### 👥 권한 관리
- [ ] CODEOWNERS 파일 설정
- [ ] 팀별 권한 할당
- [ ] 외부 리뷰어 설정

#### 🔄 워크플로우
- [ ] GitHub Actions CI/CD 설정
- [ ] Status checks 연동
- [ ] 자동 배포 설정

### 🧪 테스트 체크리스트

#### 📝 Main 브랜치 테스트
- [ ] 직접 푸시 차단 확인
- [ ] PR 없이 병합 차단 확인
- [ ] 승인 없이 병합 차단 확인
- [ ] Status check 실패 시 병합 차단 확인
- [ ] 관리자도 규칙 적용 확인

#### 📝 Develop 브랜치 테스트
- [ ] PR 생성 및 승인 프로세스 확인
- [ ] Status check 연동 확인
- [ ] 기본적인 보호 규칙 적용 확인

## 🚨 긴급 상황 대응

### ⚡ 핫픽스 프로세스

1. **긴급 브랜치 생성**
   ```bash
   git checkout -b hotfix/critical-bug-fix main
   ```

2. **최소한의 수정**
   - 문제만 정확히 수정
   - 테스트 추가

3. **빠른 리뷰 프로세스**
   - 관리자/시니어 개발자 즉시 리뷰
   - CI 통과 확인

4. **긴급 병합**
   - 관리자 권한으로 병합
   - 즉시 배포

### 🔓 임시 보호 해제

```bash
# 긴급 상황 시에만 사용
# 관리자만 실행 가능

# 보호 규칙 임시 비활성화
gh api repos/:owner/:repo/branches/main/protection --method DELETE

# 긴급 작업 수행
git push origin main

# 보호 규칙 즉시 재설정
# (위의 설정 명령어 재실행)
```

## 📈 모니터링 및 감사

### 📊 정기 검토 항목

1. **월간 검토**
   - 브랜치 보호 규칙 준수율
   - 승인 패턴 분석
   - Status check 실패율

2. **분기별 검토**
   - 권한 체계 재검토
   - CODEOWNERS 업데이트
   - 보호 규칙 효과성 분석

3. **감사 로그 확인**
   - 보호 규칙 우회 기록
   - 관리자 권한 사용 내역
   - 긴급 상황 대응 기록

---

**🛡️ 안전한 코드 관리로 더 나은 서비스를 만들어 나가세요!**

설정 과정에서 문제가 있다면 이슈를 생성해주세요.
