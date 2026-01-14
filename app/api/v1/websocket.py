"""WebSocket and SSE Endpoints for Real-time Communication"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Request
from fastapi.responses import StreamingResponse
from typing import Dict, Set, Optional, Any
from uuid import UUID
import json
import asyncio
from datetime import datetime

from app.core.security import verify_token
from app.core.database import get_redis
from app.services.task_tracker import TaskTracker
from app.services.execution_websocket_manager import execution_ws_manager
from redis.asyncio import Redis
from app.api.v1.auth import get_current_user
from app.models.user import UserModel
import structlog

logger = structlog.get_logger()

router = APIRouter(tags=["realtime"])


# ============================================================================
# Connection Manager
# ============================================================================

class ConnectionManager:
    """
    Manages WebSocket connections and message broadcasting.
    
    Provides:
    - Connection lifecycle management
    - Subscription management for task updates
    - Broadcast messaging to all connected clients
    
    Validates: Requirements 13.1, 13.2, 13.4, 13.5
    """
    
    def __init__(self):
        """Initialize connection manager"""
        # Active WebSocket connections: {connection_id: websocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # User to connection mapping: {user_id: {connection_id}}
        self.user_connections: Dict[str, Set[str]] = {}
        
        # Task subscriptions: {task_id: {connection_id}}
        self.task_subscriptions: Dict[str, Set[str]] = {}
        
        # Connection metadata: {connection_id: {user_id, connected_at}}
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect(
        self,
        websocket: WebSocket,
        connection_id: str,
        user_id: str
    ) -> None:
        """
        Accept and register a new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
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
            "connected_at": datetime.utcnow().isoformat()
        }
        
        logger.info(
            "websocket_connected",
            connection_id=connection_id,
            user_id=user_id
        )
    
    async def disconnect(self, connection_id: str) -> None:
        """
        Remove and cleanup a WebSocket connection.
        
        Args:
            connection_id: Connection identifier
        
        Validates: Requirements 13.4
        """
        # Remove from active connections
        websocket = self.active_connections.pop(connection_id, None)
        
        if websocket is None:
            return
        
        # Get metadata
        metadata = self.connection_metadata.pop(connection_id, {})
        user_id = metadata.get("user_id")
        
        # Remove from user connections
        if user_id and user_id in self.user_connections:
            self.user_connections[user_id].discard(connection_id)
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
        
        # Remove from all task subscriptions
        for task_id in list(self.task_subscriptions.keys()):
            self.task_subscriptions[task_id].discard(connection_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
        
        logger.info(
            "websocket_disconnected",
            connection_id=connection_id,
            user_id=user_id
        )
    
    async def subscribe_to_task(
        self,
        connection_id: str,
        task_id: str
    ) -> None:
        """
        Subscribe a connection to task status updates.
        
        Args:
            connection_id: Connection identifier
            task_id: Task identifier to subscribe to
        
        Validates: Requirements 13.2
        """
        if task_id not in self.task_subscriptions:
            self.task_subscriptions[task_id] = set()
        
        self.task_subscriptions[task_id].add(connection_id)
        
        logger.info(
            "task_subscription_added",
            connection_id=connection_id,
            task_id=task_id
        )
    
    async def unsubscribe_from_task(
        self,
        connection_id: str,
        task_id: str
    ) -> None:
        """
        Unsubscribe a connection from task status updates.
        
        Args:
            connection_id: Connection identifier
            task_id: Task identifier to unsubscribe from
        """
        if task_id in self.task_subscriptions:
            self.task_subscriptions[task_id].discard(connection_id)
            if not self.task_subscriptions[task_id]:
                del self.task_subscriptions[task_id]
        
        logger.info(
            "task_subscription_removed",
            connection_id=connection_id,
            task_id=task_id
        )
    
    async def send_personal_message(
        self,
        message: Dict[str, Any],
        connection_id: str
    ) -> None:
        """
        Send message to a specific connection.
        
        Args:
            message: Message data
            connection_id: Target connection identifier
        """
        websocket = self.active_connections.get(connection_id)
        
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "failed_to_send_message",
                    connection_id=connection_id,
                    error=str(e)
                )
                # Connection is broken, disconnect it
                await self.disconnect(connection_id)
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message data to broadcast
        
        Validates: Requirements 13.5
        """
        disconnected = []
        
        for connection_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(
                    "failed_to_broadcast",
                    connection_id=connection_id,
                    error=str(e)
                )
                disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
        
        logger.info(
            "message_broadcasted",
            recipient_count=len(self.active_connections) - len(disconnected),
            failed_count=len(disconnected)
        )
    
    async def send_task_update(
        self,
        task_id: str,
        status_data: Dict[str, Any]
    ) -> None:
        """
        Send task status update to all subscribed connections.
        
        Args:
            task_id: Task identifier
            status_data: Task status data
        
        Validates: Requirements 13.2
        """
        subscribers = self.task_subscriptions.get(task_id, set())
        
        if not subscribers:
            return
        
        message = {
            "type": "task_update",
            "task_id": task_id,
            "data": status_data,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        disconnected = []
        
        for connection_id in subscribers:
            websocket = self.active_connections.get(connection_id)
            if websocket:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(
                        "failed_to_send_task_update",
                        connection_id=connection_id,
                        task_id=task_id,
                        error=str(e)
                    )
                    disconnected.append(connection_id)
        
        # Clean up disconnected connections
        for connection_id in disconnected:
            await self.disconnect(connection_id)
        
        logger.info(
            "task_update_sent",
            task_id=task_id,
            recipient_count=len(subscribers) - len(disconnected)
        )


# Global connection manager instance
manager = ConnectionManager()


# ============================================================================
# WebSocket Authentication
# ============================================================================

async def authenticate_websocket(token: str) -> str:
    """
    Authenticate WebSocket connection using JWT token.
    
    Args:
        token: JWT access token
    
    Returns:
        User ID if authentication succeeds
    
    Raises:
        ValueError: If authentication fails
    
    Validates: Requirements 13.1
    """
    try:
        payload = verify_token(token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise ValueError("Invalid token: missing user ID")
        
        return user_id
    
    except Exception as e:
        raise ValueError(f"Authentication failed: {str(e)}")


# ============================================================================
# WebSocket Endpoint
# ============================================================================

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    redis: Redis = Depends(get_redis)
):
    """
    WebSocket endpoint for real-time communication.
    
    Supports:
    - Task status subscriptions
    - Real-time task updates
    - Broadcast messages
    
    Message Format:
    - Client -> Server:
      {
        "action": "subscribe" | "unsubscribe" | "ping",
        "task_id": "uuid" (for subscribe/unsubscribe)
      }
    
    - Server -> Client:
      {
        "type": "task_update" | "broadcast" | "pong" | "error",
        "data": {...},
        "timestamp": "ISO8601"
      }
    
    Validates: Requirements 13.1, 13.2, 13.4
    """
    connection_id = None
    
    # Authenticate connection BEFORE accepting
    if not token:
        logger.debug("websocket_connection_rejected", reason="missing_token")
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    try:
        user_id = await authenticate_websocket(token)
    except ValueError as e:
        logger.debug("websocket_authentication_failed", error=str(e))
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    try:
        
        # Generate connection ID
        import uuid
        connection_id = str(uuid.uuid4())
        
        # Accept and register connection
        await manager.connect(websocket, connection_id, user_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "message": "WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Initialize task tracker
        task_tracker = TaskTracker(redis)
        
        # Message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            action = data.get("action")
            
            if action == "subscribe":
                # Subscribe to task updates
                task_id = data.get("task_id")
                if task_id:
                    await manager.subscribe_to_task(connection_id, task_id)
                    
                    # Send current task status
                    task_info = await task_tracker.get_task_info(UUID(task_id))
                    if task_info:
                        await manager.send_personal_message(
                            {
                                "type": "task_update",
                                "task_id": task_id,
                                "data": task_info,
                                "timestamp": datetime.utcnow().isoformat()
                            },
                            connection_id
                        )
                    
                    await websocket.send_json({
                        "type": "subscribed",
                        "task_id": task_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif action == "unsubscribe":
                # Unsubscribe from task updates
                task_id = data.get("task_id")
                if task_id:
                    await manager.unsubscribe_from_task(connection_id, task_id)
                    
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "task_id": task_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif action == "ping":
                # Respond to ping
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                # Unknown action
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info("websocket_client_disconnected", connection_id=connection_id)
    
    except Exception as e:
        logger.error(
            "websocket_error",
            connection_id=connection_id,
            error=str(e)
        )
    
    finally:
        # Clean up connection
        if connection_id:
            await manager.disconnect(connection_id)


# ============================================================================
# Server-Sent Events (SSE) Endpoint
# ============================================================================

@router.get("/events")
async def sse_endpoint(
    request: Request,
    task_id: Optional[str] = None,
    redis: Redis = Depends(get_redis)
):
    """
    Server-Sent Events endpoint for real-time event streaming.
    
    Query Parameters:
    - task_id: Optional task ID to subscribe to specific task updates
    
    Event Format:
    - event: task_update | broadcast | heartbeat
    - data: JSON string
    
    Validates: Requirements 13.3
    """
    # Verify authentication
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid authorization header"
        )
    
    token = auth_header.split(" ")[1]
    
    try:
        user_id = await authenticate_websocket(token)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    
    async def event_generator():
        """Generate SSE events"""
        task_tracker = TaskTracker(redis)
        
        # Send initial connection event
        yield f"event: connected\n"
        yield f"data: {json.dumps({'message': 'SSE connection established', 'user_id': user_id})}\n\n"
        
        try:
            while True:
                # Check if client disconnected
                if await request.is_disconnected():
                    break
                
                # If subscribed to specific task, check for updates
                if task_id:
                    task_info = await task_tracker.get_task_info(UUID(task_id))
                    if task_info:
                        yield f"event: task_update\n"
                        yield f"data: {json.dumps(task_info)}\n\n"
                
                # Send heartbeat every 15 seconds
                yield f"event: heartbeat\n"
                yield f"data: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
                
                # Wait before next check
                await asyncio.sleep(15)
        
        except asyncio.CancelledError:
            logger.info("sse_connection_cancelled", user_id=user_id, task_id=task_id)
        
        except Exception as e:
            logger.error("sse_error", user_id=user_id, task_id=task_id, error=str(e))
            yield f"event: error\n"
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable nginx buffering
        }
    )


# ============================================================================
# Broadcast API (Admin Only)
# ============================================================================

@router.post("/broadcast")
async def broadcast_message(
    message: Dict[str, Any],
    current_user: UserModel = Depends(get_current_user)
):
    """
    Broadcast message to all connected WebSocket clients.
    
    This endpoint is restricted to admin users only for sending
    system-wide notifications.
    
    Request Body:
    {
        "type": "announcement" | "alert" | "notification",
        "message": "string",
        "data": {...}
    }
    
    Validates: Requirements 13.5
    """
    # Check if user is admin
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can broadcast messages"
        )
    
    # Prepare broadcast message
    broadcast_data = {
        "type": "broadcast",
        "message": message,
        "timestamp": datetime.utcnow().isoformat(),
        "sender": str(current_user.id),
        "sender_username": current_user.username
    }
    
    # Broadcast to all connections
    await manager.broadcast(broadcast_data)
    
    return {
        "status": "success",
        "message": "Broadcast sent",
        "recipient_count": len(manager.active_connections)
    }


# ============================================================================
# Helper function for task updates (to be called by Celery tasks)
# ============================================================================

async def notify_task_update(task_id: str, status_data: Dict[str, Any]) -> None:
    """
    Notify all subscribed WebSocket clients about task status update.
    
    This function should be called by Celery tasks when status changes.
    
    Args:
        task_id: Task identifier
        status_data: Task status data
    
    Validates: Requirements 13.2
    """
    await manager.send_task_update(task_id, status_data)



# ============================================================================
# Execution WebSocket Endpoint
# ============================================================================

@router.websocket("/ws/executions")
async def execution_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = None,
    redis: Redis = Depends(get_redis)
):
    """
    WebSocket endpoint for real-time execution updates and log streaming.
    
    This endpoint provides real-time communication for MCP tool executions,
    including status updates, progress tracking, and log streaming.
    
    Message Format:
    - Client -> Server:
      {
        "action": "subscribe" | "unsubscribe" | "ping",
        "execution_id": "uuid" (for subscribe/unsubscribe)
      }
    
    - Server -> Client:
      {
        "type": "status_update" | "log_entry" | "execution_complete" | "error" | "pong",
        "execution_id": "uuid",
        "data": {...},
        "timestamp": "ISO8601"
      }
    
    Status Update Message:
      {
        "type": "status_update",
        "execution_id": "uuid",
        "status": "queued" | "running" | "completed" | "failed" | "cancelled",
        "progress": 0-100 (optional),
        "metadata": {...} (optional),
        "timestamp": "ISO8601"
      }
    
    Log Entry Message:
      {
        "type": "log_entry",
        "execution_id": "uuid",
        "timestamp": "ISO8601",
        "level": "info" | "warning" | "error" | "debug",
        "message": "log message",
        "metadata": {...} (optional)
      }
    
    Execution Complete Message:
      {
        "type": "execution_complete",
        "execution_id": "uuid",
        "status": "success" | "failed" | "cancelled" | "timeout",
        "result": {...} (optional),
        "error": "error message" (optional),
        "timestamp": "ISO8601"
      }
    
    Validates: Requirements 3.1, 3.2, 3.3, 13.1, 13.4
    """
    connection_id = None
    
    # Authenticate connection BEFORE accepting
    if not token:
        logger.debug("execution_websocket_rejected", reason="missing_token")
        await websocket.close(code=1008, reason="Missing authentication token")
        return
    
    try:
        user_id = await authenticate_websocket(token)
    except ValueError as e:
        logger.debug("execution_websocket_auth_failed", error=str(e))
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    try:
        # Generate connection ID
        import uuid
        connection_id = str(uuid.uuid4())
        
        # Accept and register connection
        await execution_ws_manager.connect(websocket, connection_id, user_id)
        
        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "connection_id": connection_id,
            "message": "Execution WebSocket connection established",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Message handling loop
        while True:
            # Receive message from client
            data = await websocket.receive_json()
            
            action = data.get("action")
            
            if action == "subscribe":
                # Subscribe to execution updates
                execution_id = data.get("execution_id")
                if execution_id:
                    await execution_ws_manager.subscribe_to_execution(
                        connection_id,
                        execution_id
                    )
                    
                    # Get current execution status from Redis
                    status_key = f"execution:{execution_id}:status"
                    current_status = await redis.get(status_key)
                    
                    if current_status:
                        # Send current status
                        status_data = json.loads(current_status)
                        await websocket.send_json({
                            "type": "status_update",
                            "execution_id": execution_id,
                            "status": status_data.get("status"),
                            "progress": status_data.get("progress"),
                            "metadata": status_data.get("metadata"),
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    await websocket.send_json({
                        "type": "subscribed",
                        "execution_id": execution_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing execution_id",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif action == "unsubscribe":
                # Unsubscribe from execution updates
                execution_id = data.get("execution_id")
                if execution_id:
                    await execution_ws_manager.unsubscribe_from_execution(
                        connection_id,
                        execution_id
                    )
                    
                    await websocket.send_json({
                        "type": "unsubscribed",
                        "execution_id": execution_id,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Missing execution_id",
                        "timestamp": datetime.utcnow().isoformat()
                    })
            
            elif action == "ping":
                # Respond to ping
                await websocket.send_json({
                    "type": "pong",
                    "timestamp": datetime.utcnow().isoformat()
                })
            
            else:
                # Unknown action
                await websocket.send_json({
                    "type": "error",
                    "message": f"Unknown action: {action}",
                    "timestamp": datetime.utcnow().isoformat()
                })
    
    except WebSocketDisconnect:
        logger.info(
            "execution_websocket_client_disconnected",
            connection_id=connection_id
        )
    
    except Exception as e:
        logger.error(
            "execution_websocket_error",
            connection_id=connection_id,
            error=str(e),
            exc_info=True
        )
    
    finally:
        # Clean up connection
        if connection_id:
            await execution_ws_manager.disconnect(connection_id)


# ============================================================================
# Execution WebSocket Stats Endpoint (Admin Only)
# ============================================================================

@router.get("/ws/executions/stats")
async def get_execution_websocket_stats(
    current_user: UserModel = Depends(get_current_user)
):
    """
    Get statistics about execution WebSocket connections.
    
    This endpoint is restricted to admin users for monitoring purposes.
    
    Returns:
    {
        "active_connections": int,
        "unique_users": int,
        "active_subscriptions": int,
        "total_subscription_count": int
    }
    
    Validates: Requirements 13.4
    """
    # Check if user is admin
    if not current_user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can view WebSocket statistics"
        )
    
    stats = execution_ws_manager.get_connection_stats()
    
    return {
        "status": "success",
        "data": stats,
        "timestamp": datetime.utcnow().isoformat()
    }


# ============================================================================
# Helper Functions for Execution Updates
# ============================================================================

async def notify_execution_status_update(
    execution_id: str,
    status: str,
    progress: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Notify all subscribed WebSocket clients about execution status update.
    
    This function should be called by execution services when status changes.
    
    Args:
        execution_id: Execution identifier
        status: Current execution status
        progress: Optional progress percentage (0-100)
        metadata: Optional additional metadata
    
    Returns:
        Number of clients notified
    
    Validates: Requirements 3.1, 3.2
    """
    return await execution_ws_manager.send_status_update(
        execution_id,
        status,
        progress,
        metadata
    )


async def notify_execution_log_entry(
    execution_id: str,
    log_level: str,
    message: str,
    timestamp: Optional[datetime] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> int:
    """
    Stream log entry to all subscribed WebSocket clients.
    
    This function should be called by execution services when logs are generated.
    
    Args:
        execution_id: Execution identifier
        log_level: Log level (info, warning, error, debug)
        message: Log message
        timestamp: Optional log timestamp
        metadata: Optional additional metadata
    
    Returns:
        Number of clients notified
    
    Validates: Requirements 3.3
    """
    return await execution_ws_manager.send_log_entry(
        execution_id,
        log_level,
        message,
        timestamp,
        metadata
    )


async def notify_execution_complete(
    execution_id: str,
    status: str,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None
) -> int:
    """
    Notify all subscribed WebSocket clients about execution completion.
    
    This function should be called by execution services when execution completes.
    
    Args:
        execution_id: Execution identifier
        status: Final execution status
        result: Optional execution result
        error: Optional error message
    
    Returns:
        Number of clients notified
    
    Validates: Requirements 3.1, 3.2
    """
    return await execution_ws_manager.send_execution_complete(
        execution_id,
        status,
        result,
        error
    )
