"""
Execution WebSocket Manager for Real-time Updates

This module provides WebSocket connection management for execution status updates
and log streaming. It extends the existing WebSocket infrastructure to support
execution-specific real-time communication.

Validates: Requirements 3.1, 3.2, 3.3, 13.1, 13.4
"""

from typing import Dict, Set, Optional, Any, List
from uuid import UUID
from datetime import datetime
from fastapi import WebSocket
import structlog
import json

logger = structlog.get_logger()


class ExecutionWebSocketManager:
    """
    Manages WebSocket connections for execution status updates and log streaming.
    
    Features:
    - Connection lifecycle management with authentication
    - Subscription management for execution updates
    - Status update broadcasting to subscribed clients
    - Real-time log streaming
    - Connection cleanup and error handling
    
    Validates: Requirements 3.1, 3.2, 3.3, 13.1, 13.4
    """
    
    def __init__(self):
        """Initialize the execution WebSocket manager"""
        # Active WebSocket connections: {connection_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User to connection mapping: {user_id: {connection_id}}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Execution subscriptions: {execution_id: {connection_id}}
        self.execution_subscriptions: Dict[str, Set[str]] = {}
        
        # Connection metadata: {connection_id: {user_id, connected_at, subscriptions}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
        
        logger.info("execution_websocket_manager_initialized")
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str
    ) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection instance
            connection_id: Unique connection identifier
            user_id: Authenticated user ID
        
        Validates: Requirements 13.1
        """
        await websocket.accept()
        
        self.active_connections[connection_id] = websocket
        
        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(connection_id)
        
        # Store metadata
        self.connection_metadata[connection_id] = {
            "user_id": user_id,
            "connected_at": datetime.utcnow().isoformat(),
            "subscriptions": set()
        }
        
        logger.info(
            "execution_websocket_connected",
            connection_id=connection_id,
            user_id=user_id
        )
    
    async def disconnect(self, connection_id: str) -> None:
        """
        Remove and cleanup a WebSocket connection.
        
        Args:
            connection_id: Connection identifier to disconnect
        
        Validates: Requirements 13.4
        """
        # Remove from active connections
        websocket = self.active_connections.pop(connection_id, None)
        
        if websocket is None:
            return
        
        # Get metadata
        metadata = self.connection_metadata.pop(connection_id, {})
        user_id = metadata.get("user_id")
        subscriptions = metadata.get("subscriptions", set())
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from all execution subscriptions
        for execution_id in subscriptions:
            if execution_id in self.execution_subscriptions:
                self.execution_subscriptions[execution_id].discard(connection_id)
                if not self.execution_subscriptions[execution_id]:
                    del self.execution_subscriptions[execution_id]
        
        logger.info(
            "execution_websocket_disconnected",
            connection_id=connection_id,
            user_id=user_id,
            subscription_count=len(subscriptions)
        )
    
    async def subscribe_to_execution(
        self,
        connection_id: str,
        execution_id: str
    ) -> None:
        """
        Subscribe a connection to execution status updates and log streaming.
        
        Args:
            connection_id: Connection identifier
            execution_id: Execution identifier to subscribe to
        
        Validates: Requirements 3.1, 3.2, 3.3
        """
        if execution_id not in self.execution_subscriptions:
            self.execution_subscriptions[execution_id] = set()
        
        self.execution_subscriptions[execution_id].add(connection_id)
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscriptions"].add(execution_id)
        
        logger.info(
            "execution_subscription_added",
            connection_id=connection_id,
            execution_id=execution_id
        )
    
    async def unsubscribe_from_execution(
        self,
        connection_id: str,
        execution_id: str
    ) -> None:
        """
        Unsubscribe a connection from execution updates.
        
        Args:
            connection_id: Connection identifier
            execution_id: Execution identifier to unsubscribe from
        """
        if execution_id in self.execution_subscriptions:
            self.execution_subscriptions[execution_id].discard(connection_id)
            if not self.execution_subscriptions[execution_id]:
                del self.execution_subscriptions[execution_id]
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscriptions"].discard(execution_id)
        
        logger.info(
            "execution_subscription_removed",
            connection_id=connection_id,
            execution_id=execution_id
        )
    
    async def send_personal_message(
        self,
        message: Dict[str, Any],
        connection_id: str
    ) -> bool:
        """
        Send message to a specific connection.
        
        Args:
            message: Message data to send
            connection_id: Target connection identifier
        
        Returns:
            True if message sent successfully, False otherwise
        """
        websocket = self.active_connections.get(connection_id)
        
        if websocket:
            try:
                await websocket.send_json(message)
                return True
            except Exception as e:
                logger.error(
                    "failed_to_send_execution_message",
                    connection_id=connection_id,
                    error=str(e)
                )
                # Connection is broken, disconnect it
                await self.disconnect(connection_id)
                return False
        
        return False
    
    async def send_status_update(
        self,
        execution_id: str,
        status: str,
        progress: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Send execution status update to all subscribed connections.
        
        Args:
            execution_id: Execution identifier
            status: Current execution status
            progress: Optional progress percentage (0-100)
            metadata: Optional additional metadata
        
        Returns:
            Number of clients that received the update
        
        Validates: Requirements 3.1, 3.2
        """
        subscribers = self.execution_subscriptions.get(execution_id, set())
        
        if not subscribers:
            logger.debug(
                "no_subscribers_for_execution",
                execution_id=execution_id
            )
            return 0
        
        message = {
            "type": "status_update",
            "execution_id": execution_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if progress is not None:
            message["progress"] = progress
        
        if metadata:
            message["metadata"] = metadata
        
        sent_count = 0
        disconnected = []
        
        for connection_id in subscribers:
            success = await self.send_personal_message(message, connection_id)
            if success:
                sent_count += 1
            else:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
        
        logger.info(
            "execution_status_update_sent",
            execution_id=execution_id,
            status=status,
            recipient_count=sent_count,
            failed_count=len(disconnected)
        )
        
        return sent_count
    
    async def send_log_entry(
        self,
        execution_id: str,
        log_level: str,
        message: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Stream log entry to all subscribed connections.
        
        Args:
            execution_id: Execution identifier
            log_level: Log level (info, warning, error, debug)
            message: Log message
            timestamp: Optional log timestamp (defaults to now)
            metadata: Optional additional metadata
        
        Returns:
            Number of clients that received the log entry
        
        Validates: Requirements 3.3
        """
        subscribers = self.execution_subscriptions.get(execution_id, set())
        
        if not subscribers:
            return 0
        
        log_message = {
            "type": "log_entry",
            "execution_id": execution_id,
            "timestamp": (timestamp or datetime.utcnow()).isoformat(),
            "level": log_level,
            "message": message
        }
        
        if metadata:
            log_message["metadata"] = metadata
        
        sent_count = 0
        disconnected = []
        
        for connection_id in subscribers:
            success = await self.send_personal_message(log_message, connection_id)
            if success:
                sent_count += 1
            else:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
        
        if sent_count > 0:
            logger.debug(
                "execution_log_entry_sent",
                execution_id=execution_id,
                log_level=log_level,
                recipient_count=sent_count
            )
        
        return sent_count
    
    async def send_execution_complete(
        self,
        execution_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None
    ) -> int:
        """
        Send execution completion notification to all subscribed connections.
        
        Args:
            execution_id: Execution identifier
            status: Final execution status (success, failed, cancelled, timeout)
            result: Optional execution result data
            error: Optional error message if execution failed
        
        Returns:
            Number of clients that received the notification
        
        Validates: Requirements 3.1, 3.2
        """
        subscribers = self.execution_subscriptions.get(execution_id, set())
        
        if not subscribers:
            return 0
        
        message = {
            "type": "execution_complete",
            "execution_id": execution_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if result:
            message["result"] = result
        
        if error:
            message["error"] = error
        
        sent_count = 0
        disconnected = []
        
        for connection_id in subscribers:
            success = await self.send_personal_message(message, connection_id)
            if success:
                sent_count += 1
            else:
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
        
        logger.info(
            "execution_complete_notification_sent",
            execution_id=execution_id,
            status=status,
            recipient_count=sent_count
        )
        
        return sent_count
    
    def get_subscriber_count(self, execution_id: str) -> int:
        """
        Get the number of subscribers for an execution.
        
        Args:
            execution_id: Execution identifier
        
        Returns:
            Number of active subscribers
        """
        return len(self.execution_subscriptions.get(execution_id, set()))
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about active connections and subscriptions.
        
        Returns:
            Dictionary with connection statistics
        """
        return {
            "active_connections": len(self.active_connections),
            "unique_users": len(self.user_connections),
            "active_subscriptions": len(self.execution_subscriptions),
            "total_subscription_count": sum(
                len(subs) for subs in self.execution_subscriptions.values()
            )
        }


# Global execution WebSocket manager instance
execution_ws_manager = ExecutionWebSocketManager()
