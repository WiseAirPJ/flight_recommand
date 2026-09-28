import secrets
import string


def generate_secret_key(length=64):
    """안전한 SECRET_KEY 생성"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_multiple_keys():
    """여러 환경용 키 생성"""
    keys = {
        "development": generate_secret_key(64),
        "test": generate_secret_key(64),
        "production": generate_secret_key(64),
    }

    print("🔐 안전한 SECRET_KEY 생성 완료!")
    print("=" * 70)

    for env, key in keys.items():
        print(f"\n📝 {env.upper()} 환경:")
        print(f"SECRET_KEY={key}")

    print("\n" + "=" * 70)
    print("⚠️  주의사항:")
    print("- 각 환경마다 다른 키를 사용하세요")
    print("- 운영 환경의 키는 절대 공개하지 마세요")
    print("- 키는 최소 32자 이상이어야 합니다")
    print("- 정기적으로 키를 교체하세요")

    return keys


if __name__ == "__main__":
    keys = generate_multiple_keys()

    # .env 파일 예시 생성
    print("\n📁 .env 파일 예시:")
    print("-" * 40)
    print(f"SECRET_KEY={keys['development']}")
    print("DEBUG=true")
    print("ENVIRONMENT=development")
