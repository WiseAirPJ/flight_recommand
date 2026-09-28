from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.price_prediction_service import PricePredictionService

router = APIRouter()
service = PricePredictionService()


class PricePredictionRequest(BaseModel):
    departure_date: str
    current_date: Optional[str] = None


class PriceTrendRequest(BaseModel):
    departure_date: str
    days_range: int = 30


def validate_date(date_str: str) -> None:
    datetime.strptime(date_str, "%Y-%m-%d")


@router.post("/predict")
async def predict_price(request: PricePredictionRequest):
    try:
        validate_date(request.departure_date)
        if request.current_date:
            validate_date(request.current_date)

        result = service.predict_price(request.departure_date, request.current_date)

        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])

        return {"success": True, "data": result}

    except ValueError:
        raise HTTPException(
            status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"예측 실패: {str(e)}")


@router.post("/trend")
async def get_price_trend(request: PriceTrendRequest):
    try:
        validate_date(request.departure_date)
        trends = service.get_price_trend(request.departure_date, request.days_range)
        return {"success": True, "data": trends}

    except ValueError:
        raise HTTPException(
            status_code=400, detail="날짜 형식이 올바르지 않습니다 (YYYY-MM-DD)"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"트렌드 예측 실패: {str(e)}")


@router.get("/model-status")
async def get_model_status():
    return {
        "success": True,
        "data": {
            "is_trained": service.is_trained,
            "model_type": "RandomForestRegressor",
        },
    }


@router.post("/train")
async def train_model():
    try:
        if service.train_model():
            return {"success": True, "data": {"is_trained": service.is_trained}}
        else:
            raise HTTPException(status_code=500, detail="모델 훈련 실패")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"훈련 실패: {str(e)}")
