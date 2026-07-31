"""Notifications port - Protocol for native OS notifications."""

from typing import Protocol, Optional
from dataclasses import dataclass


@dataclass
class NotificationData:
    """Data for a track change notification."""
    
    title: str
    artist: Optional[str] = None
    album: Optional[str] = None
    cover_data: Optional[bytes] = None


class NotificationsPort(Protocol):
    """Protocol for notification adapters.
    
    Implementations must send native OS notifications
    with track information and optional cover art.
    """

    def send_track_change(self, data: NotificationData) -> bool:
        """Send a track change notification.
        
        Args:
            data: Notification data with track info.
        
        Returns:
            True if notification was sent successfully, False otherwise.
        """
        ...

    def is_supported(self) -> bool:
        """Check if notifications are supported on this system.
        
        Returns:
            True if notifications can be sent.
        """
        ...

    def request_permission(self) -> bool:
        """Request notification permission if needed.
        
        Returns:
            True if permission granted, False otherwise.
        """
        ...
