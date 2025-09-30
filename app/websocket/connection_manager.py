"""WebSocket Connection Manager for real-time job updates"""

from typing import Dict, Set, List
from fastapi import WebSocket
from datetime import datetime
import json
import asyncio
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates"""

    def __init__(self):
        # Active connections: client_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}

        # Job subscriptions: job_id -> Set[client_id]
        self.job_subscriptions: Dict[str, Set[str]] = {}

        # Client info for debugging
        self.client_info: Dict[str, dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept and register a new WebSocket connection"""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.client_info[client_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "subscribed_jobs": set()
        }
        logger.info(f"WebSocket client connected: {client_id}")

        # Send welcome message
        await self.send_personal_message(
            {
                "type": "connection",
                "status": "connected",
                "client_id": client_id,
                "timestamp": datetime.utcnow().isoformat()
            },
            client_id
        )

    def disconnect(self, client_id: str) -> None:
        """Remove a WebSocket connection"""
        if client_id in self.active_connections:
            del self.active_connections[client_id]

            # Remove from all job subscriptions
            for job_id in list(self.job_subscriptions.keys()):
                if client_id in self.job_subscriptions[job_id]:
                    self.job_subscriptions[job_id].discard(client_id)
                    if not self.job_subscriptions[job_id]:
                        del self.job_subscriptions[job_id]

            # Clean up client info
            if client_id in self.client_info:
                del self.client_info[client_id]

            logger.info(f"WebSocket client disconnected: {client_id}")

    async def send_personal_message(self, message: dict, client_id: str) -> None:
        """Send a message to a specific client"""
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message to {client_id}: {e}")
                self.disconnect(client_id)

    async def broadcast(self, message: dict) -> None:
        """Broadcast a message to all connected clients"""
        disconnected_clients = []

        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to {client_id}: {e}")
                disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    async def broadcast_to_job_subscribers(self, job_id: str, message: dict) -> None:
        """Send a message to all clients subscribed to a specific job"""
        if job_id not in self.job_subscriptions:
            return

        message["job_id"] = job_id
        disconnected_clients = []

        for client_id in self.job_subscriptions[job_id]:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to subscriber {client_id}: {e}")
                    disconnected_clients.append(client_id)

        # Clean up disconnected clients
        for client_id in disconnected_clients:
            self.disconnect(client_id)

    def subscribe_to_job(self, client_id: str, job_id: str) -> bool:
        """Subscribe a client to job updates"""
        if client_id not in self.active_connections:
            return False

        if job_id not in self.job_subscriptions:
            self.job_subscriptions[job_id] = set()

        self.job_subscriptions[job_id].add(client_id)

        if client_id in self.client_info:
            self.client_info[client_id]["subscribed_jobs"].add(job_id)

        logger.info(f"Client {client_id} subscribed to job {job_id}")
        return True

    def unsubscribe_from_job(self, client_id: str, job_id: str) -> bool:
        """Unsubscribe a client from job updates"""
        if job_id in self.job_subscriptions:
            self.job_subscriptions[job_id].discard(client_id)
            if not self.job_subscriptions[job_id]:
                del self.job_subscriptions[job_id]

        if client_id in self.client_info:
            self.client_info[client_id]["subscribed_jobs"].discard(job_id)

        logger.info(f"Client {client_id} unsubscribed from job {job_id}")
        return True

    async def send_job_update(self, job_id: str, update_type: str, data: dict) -> None:
        """Send a job update to all subscribers"""
        message = {
            "type": "job_update",
            "update_type": update_type,
            "job_id": job_id,
            "data": data,
            "timestamp": datetime.utcnow().isoformat()
        }
        await self.broadcast_to_job_subscribers(job_id, message)

    async def send_heartbeat(self, client_id: str) -> bool:
        """Send a heartbeat ping to check connection health"""
        if client_id in self.active_connections:
            try:
                await self.send_personal_message(
                    {"type": "ping", "timestamp": datetime.utcnow().isoformat()},
                    client_id
                )
                return True
            except (ConnectionError, RuntimeError, AttributeError) as e:
                logger.debug(f"Error sending heartbeat to client {client_id}: {e}")
                self.disconnect(client_id)
                return False
        return False

    def get_connection_stats(self) -> dict:
        """Get statistics about current connections"""
        return {
            "total_connections": len(self.active_connections),
            "total_job_subscriptions": len(self.job_subscriptions),
            "clients": {
                client_id: {
                    "connected_at": info.get("connected_at"),
                    "subscribed_jobs_count": len(info.get("subscribed_jobs", []))
                }
                for client_id, info in self.client_info.items()
            }
        }


# Global connection manager instance
manager = ConnectionManager()