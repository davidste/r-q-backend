from datetime import datetime, timedelta
import random
import uuid
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


app = FastAPI(
    title="RQ Mobile API",
    version="2.0.0",
    description="Backend API for RQ Mobile iOS app",
)


# ---------------------------------------------------------------------------
# Mock data (can be replaced later with a real database)
# ---------------------------------------------------------------------------

MOCK_USERS: Dict[str, Dict[str, Any]] = {
    "test@example.com": {
        "id": "user-123",
        "firstName": "טסט",
        "lastName": "משתמש",
        "email": "test@example.com",
        "phone": "+972501234567",
        "subscriptionTier": "premium",
        "preferredLocations": ["תל אביב", "רמת גן"],
        "createdAt": "2025-01-01T00:00:00Z",
    },
    "demo@rq.app": {
        "id": "user-456",
        "firstName": "דמו",
        "lastName": "המשתמש",
        "email": "demo@rq.app",
        "phone": None,
        "subscriptionTier": "free",
        "preferredLocations": [],
        "createdAt": "2025-01-01T00:00:00Z",
    },
}

MOCK_PROPERTIES: List[Dict[str, Any]] = []


def generate_mock_properties() -> None:
    cities = ["תל אביב", "ירושלים", "חיפה", "ראשון לציון", "נתניה"]
    streets = ["הרצל", "דיזנגוף", "אלנבי", "בוגרשוב", "שבזי"]
    property_types = ["apartment", "penthouse", "house"]
    features = ["mamad", "elevator", "parking", "storage", "balcony", "renovated"]

    for i in range(1, 51):
        city = random.choice(cities)
        price = random.randint(1_000_000, 6_000_000)
        size = random.randint(50, 150)
        rooms = random.choice([1.5, 2, 2.5, 3, 3.5, 4, 5])

        prop: Dict[str, Any] = {
            "id": f"property-{i}",
            "title": f"דירה {int(rooms)} חדרים ב{city}",
            "propertyType": random.choice(property_types),
            "address": {
                "street": random.choice(streets),
                "number": str(random.randint(1, 100)),
                "city": city,
                "neighborhood": f"שכונת {random.randint(1, 10)}",
                "latitude": 32.0 + random.random(),
                "longitude": 34.0 + random.random(),
            },
            "price": price,
            "pricePerSqm": price // size,
            "rooms": rooms,
            "sizeSqm": size,
            "floor": random.randint(1, 15),
            "totalFloors": random.randint(3, 20),
            "rqScore": random.randint(40, 95),
            "rqScoreLabel": random.choice(["השקעה מצוינת", "השקעה טובה", "הוגן"]),
            "primaryImageUrl": f"https://picsum.photos/400/300?random={i}",
            "lastUpdatedAt": "2025-01-15T10:30:00Z",
            "features": random.sample(features, random.randint(0, 4)),
        }
        MOCK_PROPERTIES.append(prop)


generate_mock_properties()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    firstName: str
    lastName: str
    email: str
    password: str
    phone: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class RefreshRequest(BaseModel):
    refreshToken: str


class SavePropertyRequest(BaseModel):
    propertyId: str
    alertsEnabled: Optional[bool] = True


class ReceiptVerifyRequest(BaseModel):
    receiptData: str
    productId: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def generate_tokens(user_id: str) -> Dict[str, Any]:
    return {
        "accessToken": f"access-token-{user_id}-{uuid.uuid4().hex[:16]}",
        "refreshToken": f"refresh-token-{user_id}-{uuid.uuid4().hex[:16]}",
        "expiresIn": 3600,
    }


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


@app.get("/health/ping")
def health_ping() -> Dict[str, str]:
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


@app.post("/api/v2/mobile/auth/register")
def register(payload: RegisterRequest) -> Dict[str, Any]:
    if payload.email in MOCK_USERS:
        raise HTTPException(status_code=409, detail={"error": "conflict", "message": "Email already exists"})

    user_id = f"user-{uuid.uuid4().hex[:8]}"
    user = {
        "id": user_id,
        "firstName": payload.firstName,
        "lastName": payload.lastName,
        "email": payload.email,
        "phone": payload.phone,
        "subscriptionTier": "free",
        "preferredLocations": [],
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    MOCK_USERS[payload.email] = user

    tokens = generate_tokens(user_id)
    return {"user": user, "tokens": tokens}


@app.post("/api/v2/mobile/auth/login")
def login(payload: LoginRequest) -> Dict[str, Any]:
    email = payload.email
    password = payload.password

    if email not in MOCK_USERS or password not in {"password123", "demo123"}:
        raise HTTPException(status_code=401, detail={"error": "unauthorized", "message": "Invalid credentials"})

    user = MOCK_USERS[email].copy()
    tokens = generate_tokens(user["id"])
    return {"user": user, "tokens": tokens}


@app.post("/api/v2/mobile/auth/refresh")
def refresh_token(payload: RefreshRequest) -> Dict[str, Any]:
    # In production, validate refresh token and derive user id
    user_id = "user-123"
    return generate_tokens(user_id)


@app.post("/api/v2/mobile/auth/logout")
def logout() -> Dict[str, Any]:
    return {}


@app.post("/api/v2/mobile/auth/verify-device")
def verify_device() -> Dict[str, Any]:
    return {}


# ---------------------------------------------------------------------------
# Properties
# ---------------------------------------------------------------------------


@app.get("/api/v2/mobile/properties/search")
def search_properties(page: int = 1, pageSize: int = 20, query: Optional[str] = None) -> Dict[str, Any]:
    page_size = min(pageSize, 50)
    filtered = list(MOCK_PROPERTIES)

    if query:
        q = query.lower()
        filtered = [
            p
            for p in filtered
            if q in p["address"]["city"].lower() or q in p["title"].lower()
        ]

    start = (page - 1) * page_size
    end = start + page_size
    items = filtered[start:end]

    return {
        "items": items,
        "meta": {
            "page": page,
            "pageSize": page_size,
            "totalPages": (len(filtered) // page_size) + 1,
            "totalItems": len(filtered),
        },
    }


@app.get("/api/v2/mobile/properties/{property_id}")
def get_property(property_id: str) -> Dict[str, Any]:
    prop = next((p for p in MOCK_PROPERTIES if p["id"] == property_id), None)
    if not prop:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Property not found"})

    full_property = prop.copy()
    full_property.update(
        {
            "description": f"{full_property['title']}. דירה מרווחת ומוארת ב{full_property['address']['city']}.",
            "media": {
                "images": [
                    f"https://picsum.photos/600/400?random={property_id}-1",
                    f"https://picsum.photos/600/400?random={property_id}-2",
                    f"https://picsum.photos/600/400?random={property_id}-3",
                ],
                "videos": [],
            },
            "amenities": {
                "mamad": random.choice([True, False]),
                "elevator": random.choice([True, False]),
                "parkingSpots": random.randint(0, 2),
                "storage": random.choice([True, False]),
                "balconySizeSqm": random.randint(0, 20),
                "renovated": random.choice([True, False]),
                "accessible": random.choice([True, False]),
                "ac": random.choice([True, False]),
            },
            "prediction": {
                "forecast12Months": int(full_property["price"] * 1.05),
                "forecast24Months": int(full_property["price"] * 1.08),
                "forecast60Months": int(full_property["price"] * 1.15),
                "expectedIncreasePct": 5.0,
                "annualRoiPct": 2.5,
                "confidencePct": 80,
            },
            "neighborhood": {
                "name": full_property["address"]["neighborhood"],
                "avgPricePerSqm": full_property["price"] // full_property["sizeSqm"]
                + random.randint(-5_000, 5_000),
                "avgRqScore": random.randint(70, 85),
                "propertiesCount": random.randint(50, 200),
                "amenities": {
                    "schools": random.randint(1, 5),
                    "parks": random.randint(1, 3),
                    "transitLines": random.randint(2, 8),
                    "shoppingCenters": random.randint(1, 4),
                },
            },
            "reasons": [
                {"label": "מיקום מרכזי", "sentiment": "positive"},
                {"label": "מחיר תחרותי", "sentiment": "positive"},
            ],
        }
    )

    return full_property


@app.get("/api/v2/mobile/properties/saved")
def get_saved_properties() -> Dict[str, Any]:
    saved: List[Dict[str, Any]] = []
    for prop in MOCK_PROPERTIES[:5]:
        saved.append(
            {
                "id": f"saved-{prop['id']}",
                "property": prop,
                "meta": {
                    "savedAt": (datetime.utcnow() - timedelta(days=random.randint(1, 30))).isoformat()
                    + "Z",
                    "alertsEnabled": random.choice([True, False]),
                    "lastChange": random.choice([None, "המחיר ירד ב-2%", "סטטוס עודכן"]),
                    "daysSaved": random.randint(1, 30),
                },
            }
        )
    return {"items": saved}


@app.post("/api/v2/mobile/properties/saved")
def save_property(payload: SavePropertyRequest) -> Dict[str, Any]:
    prop = next((p for p in MOCK_PROPERTIES if p["id"] == payload.propertyId), None)
    if not prop:
        raise HTTPException(status_code=404, detail={"error": "not_found", "message": "Property not found"})

    return {
        "id": f"saved-{payload.propertyId}",
        "property": prop,
        "meta": {
            "savedAt": datetime.utcnow().isoformat() + "Z",
            "alertsEnabled": payload.alertsEnabled,
            "lastChange": None,
            "daysSaved": 0,
        },
    }


@app.delete("/api/v2/mobile/properties/saved/{saved_id}")
def delete_saved_property(saved_id: str) -> Dict[str, Any]:
    return {}


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


@app.get("/api/v2/mobile/user/profile")
def get_profile() -> Dict[str, Any]:
    # In production, derive user from auth token
    return MOCK_USERS["test@example.com"]


@app.get("/api/v2/mobile/user/subscription")
def get_subscription() -> Dict[str, Any]:
    return {
        "tier": "premium",
        "expiresAt": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
        "autoRenewing": True,
    }


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


@app.get("/api/v2/mobile/notifications")
def get_notifications(page: int = 1, pageSize: int = 10) -> Dict[str, Any]:
    notifications: List[Dict[str, Any]] = []
    for i in range(pageSize):
        notifications.append(
            {
                "id": f"notif-{i}",
                "type": random.choice(["new_property", "price_drop", "rq_change"]),
                "title": "עדכון חדש",
                "body": "המחיר של נכס שמור ירד ב-2%",
                "createdAt": (datetime.utcnow() - timedelta(hours=i)).isoformat() + "Z",
                "readAt": None,
                "propertyId": f"property-{random.randint(1, 50)}",
                "savedSearchId": None,
                "metadata": {
                    "thumbnailUrl": "https://picsum.photos/100/100?random=1",
                    "city": "תל אביב",
                    "rqScore": random.randint(60, 90),
                    "price": random.randint(1_500_000, 4_000_000),
                    "changePercent": random.uniform(-5, 5),
                },
            }
        )

    return {
        "items": notifications,
        "meta": {
            "page": page,
            "pageSize": pageSize,
            "totalPages": 3,
            "totalItems": 25,
        },
    }


@app.put("/api/v2/mobile/notifications/{notification_id}/read")
def mark_notification_read(notification_id: str) -> Dict[str, Any]:
    return {}


# ---------------------------------------------------------------------------
# Billing / IAP
# ---------------------------------------------------------------------------


@app.post("/api/v2/mobile/billing/ios/verify")
def verify_receipt(payload: ReceiptVerifyRequest) -> Dict[str, Any]:
    return {
        "success": True,
        "subscription": {
            "tier": "premium",
            "expiresAt": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
            "autoRenewing": True,
        },
        "message": "Subscription activated",
    }
