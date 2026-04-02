from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.device import Device
from app.schemas.auth import DeviceRegister, DeviceResponse, NotificationStatusUpdate

router = APIRouter(prefix="/devices", tags=["devices"])


@router.post("/register", response_model=DeviceResponse, status_code=status.HTTP_201_CREATED)
def register_device(
    payload: DeviceRegister,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Register or update a device for the current user."""
    # Check if device with same FCM token already registered
    if payload.fcm_token:
        existing = db.query(Device).filter(Device.fcm_token == payload.fcm_token).first()
        if existing:
            existing.notification_listener_enabled = payload.notification_listener_enabled
            if payload.device_name:
                existing.device_name = payload.device_name
            db.commit()
            db.refresh(existing)
            return DeviceResponse.model_validate(existing)

    device = Device(
        user_id=current_user.id,
        platform=payload.platform,
        device_name=payload.device_name,
        fcm_token=payload.fcm_token,
        notification_listener_enabled=payload.notification_listener_enabled,
    )
    db.add(device)
    db.commit()
    db.refresh(device)
    return DeviceResponse.model_validate(device)


@router.post("/notification-status")
def update_notification_status(
    payload: NotificationStatusUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """Update notification listener permission status for a device."""
    query = db.query(Device).filter(Device.user_id == current_user.id)
    if payload.device_id:
        query = query.filter(Device.id == payload.device_id)

    device = query.order_by(Device.created_at.desc()).first()
    if not device:
        raise HTTPException(status_code=404, detail="No device found for this user.")

    device.notification_listener_enabled = payload.notification_listener_enabled
    db.commit()

    return {
        "success": True,
        "notification_listener_enabled": device.notification_listener_enabled,
    }
