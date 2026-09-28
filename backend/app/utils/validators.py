from datetime import date, datetime


def validate_date_format(date_str: str, allow_past: bool = False) -> str:
    try:
        parsed_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        if not allow_past and parsed_date <= date.today():
            raise ValueError("날짜는 오늘 이후여야 합니다.")

        return date_str
    except ValueError as e:
        if "does not match format" in str(e):
            raise ValueError(
                "날짜 형식이 올바르지 않습니다. YYYY-MM-DD 형식으로 입력해주세요."
            )
        raise


def validate_iata_code(iata_code: str) -> str:
    if not iata_code or len(iata_code) != 3:
        raise ValueError("IATA 코드는 3자리여야 합니다.")

    if not (iata_code.isascii() and iata_code.isalpha()):
        raise ValueError("IATA 코드는 영문자만 포함해야 합니다.")

    return iata_code.upper()


def validate_duration(duration: int, min_days: int = 2, max_days: int = 30) -> int:
    if duration < min_days:
        raise ValueError(f"여행 기간은 최소 {min_days}일 이상이어야 합니다.")

    if duration > max_days:
        raise ValueError(f"여행 기간은 최대 {max_days}일까지 가능합니다.")

    return duration


def validate_passenger_count(count: int, max_count: int = 9) -> int:
    if count < 1:
        raise ValueError("승객 수는 최소 1명 이상이어야 합니다.")

    if count > max_count:
        raise ValueError(f"승객 수는 최대 {max_count}명까지 가능합니다.")

    return count
