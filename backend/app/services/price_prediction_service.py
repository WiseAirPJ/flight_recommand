import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.exceptions import NotFittedError

logger = logging.getLogger(__name__)


class PricePredictionService:
    def __init__(self):
        self.model = None
        self.is_trained = False

    def _get_season_score(self, month: int) -> float:
        scores = {
            1: 0.8,
            2: 0.3,
            3: 0.6,
            4: 0.9,
            5: 1.0,
            6: 0.4,
            7: 0.7,
            8: 0.8,
            9: 0.5,
            10: 0.7,
            11: 0.6,
            12: 0.9,
        }
        return scores.get(month, 0.5)

    def _is_holiday(self, date: datetime) -> bool:
        return (
            (date.month == 4 and date.day >= 29)
            or (date.month == 5 and date.day <= 5)
            or (date.month == 12 and date.day >= 29)
            or (date.month == 1 and date.day <= 3)
        )

    def _get_recommendation(self, days_to_departure: int) -> str:
        if days_to_departure > 60:
            return "아직 예약하기 이릅니다. 30-45일 전에 다시 확인해보세요."
        elif days_to_departure > 30:
            return "예약하기 좋은 시점입니다."
        elif days_to_departure > 14:
            return "가격이 오를 수 있습니다. 빠른 예약을 권장합니다."
        else:
            return "가격이 높을 수 있습니다. 대체 날짜를 고려해보세요."

    def train_model(self) -> bool:
        try:
            data = []
            base_price = 300000

            for _ in range(1000):
                days_to_departure = np.random.randint(1, 90)
                is_weekend = np.random.choice([0, 1], p=[0.7, 0.3])
                is_holiday = np.random.choice([0, 1], p=[0.9, 0.1])
                month = np.random.randint(1, 13)
                season_score = self._get_season_score(month)

                price = base_price
                price *= 1 + (90 - days_to_departure) * 0.01
                price *= 1 + is_weekend * 0.2
                price *= 1 + is_holiday * 0.5
                price *= 1 + season_score * 0.3
                price += np.random.normal(0, 50000)

                data.append(
                    [
                        days_to_departure,
                        is_weekend,
                        is_holiday,
                        month,
                        season_score,
                        max(200000, price),
                    ]
                )

            X = np.array([d[:-1] for d in data])
            y = np.array([d[-1] for d in data])

            self.model = RandomForestRegressor(
                n_estimators=100, random_state=42, max_depth=10
            )
            self.model.fit(X, y)
            self.is_trained = True
            return True

        except (ImportError, ValueError, MemoryError) as e:
            logger.error(f"모델 훈련 실패: {e}")
            return False

    def predict_price(
        self, departure_date: str, current_date: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.is_trained:
            if not self.train_model():
                return {"error": "모델 훈련 실패"}

        try:
            dep_date = datetime.strptime(departure_date, "%Y-%m-%d")
            cur_date = (
                datetime.strptime(current_date, "%Y-%m-%d")
                if current_date
                else datetime.now()
            )

            days_to_departure = (dep_date - cur_date).days
            is_weekend = 1 if dep_date.weekday() >= 5 else 0
            is_holiday = self._is_holiday(dep_date)
            month = dep_date.month
            season_score = self._get_season_score(month)

            features = np.array(
                [[days_to_departure, is_weekend, is_holiday, month, season_score]]
            )
            predicted_price = self.model.predict(features)[0]

            confidence = min(0.95, max(0.6, 1.0 - abs(days_to_departure - 30) / 100))

            return {
                "predicted_price": int(predicted_price),
                "confidence": confidence,
                "features": {
                    "days_to_departure": days_to_departure,
                    "is_weekend": bool(is_weekend),
                    "is_holiday": bool(is_holiday),
                    "season_score": season_score,
                },
                "recommendation": self._get_recommendation(days_to_departure),
            }

        except (ValueError, NotFittedError, TypeError) as e:
            logger.error(f"가격 예측 실패: {e}")
            return {"error": f"예측 실패: {str(e)}"}

    def get_price_trend(self, departure_date: str, days_range: int = 30) -> List[Dict]:
        if not self.is_trained:
            if not self.train_model():
                return []

        try:
            trends = []
            dep_date = datetime.strptime(departure_date, "%Y-%m-%d")

            for i in range(days_range):
                current_date = datetime.now() + timedelta(days=i)
                if current_date >= dep_date:
                    break

                result = self.predict_price(
                    departure_date, current_date.strftime("%Y-%m-%d")
                )

                if "error" not in result:
                    trends.append(
                        {
                            "date": current_date.strftime("%Y-%m-%d"),
                            "days_to_departure": result["features"][
                                "days_to_departure"
                            ],
                            "predicted_price": result["predicted_price"],
                            "confidence": result["confidence"],
                        }
                    )

            return trends

        except (ValueError, TypeError) as e:
            logger.error(f"가격 트렌드 생성 실패: {e}")
            return []
