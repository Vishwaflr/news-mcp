"""WebSocket endpoint for real-time job updates"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
import json
import uuid
import asyncio
from app.websocket import connection_manager
from app.core.logging_config import get_logger

router = APIRouter(tags=["websocket"])
logger = get_logger(__name__)


@router.websocket("/ws/jobs")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None)
):
    """
    WebSocket endpoint for real-time job updates

    Message Protocol:
    Client -> Server:
    {
        "action": "subscribe" | "unsubscribe" | "get_status" | "pong",
        "job_id": "string" (for subscribe/unsubscribe),
        "data": {} (optional payload)
    }

    Server -> Client:
    {
        "type": "connection" | "job_update" | "error" | "ping",
        "job_id": "string" (for job updates),
        "data": {},
        "timestamp": "ISO-8601"
    }
    """

    # Generate client ID if not provided
    if not client_id:
        client_id = str(uuid.uuid4())[:8]

    try:
        # Accept connection
        await connection_manager.connect(websocket, client_id)

        # Keep connection alive
        while True:
            try:
                # Receive message from client
                data = await websocket.receive_json()

                action = data.get("action")
                job_id = data.get("job_id")

                if action == "subscribe" and job_id:
                    # Subscribe to job updates
                    success = connection_manager.subscribe_to_job(client_id, job_id)
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "subscribed" if success else "failed",
                        "job_id": job_id
                    })

                    # Send current job status
                    await send_current_job_status(job_id, client_id)

                elif action == "unsubscribe" and job_id:
                    # Unsubscribe from job updates
                    connection_manager.unsubscribe_from_job(client_id, job_id)
                    await websocket.send_json({
                        "type": "subscription",
                        "status": "unsubscribed",
                        "job_id": job_id
                    })

                elif action == "get_status":
                    # Get connection stats
                    stats = connection_manager.get_connection_stats()
                    await websocket.send_json({
                        "type": "status",
                        "data": stats
                    })

                elif action == "pong":
                    # Heartbeat response
                    logger.debug(f"Received pong from {client_id}")

                else:
                    # Unknown action
                    await websocket.send_json({
                        "type": "error",
                        "message": f"Unknown action: {action}"
                    })

            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })

            except asyncio.TimeoutError:
                # Send ping to check connection
                await connection_manager.send_heartbeat(client_id)
                await asyncio.sleep(30)  # Wait for pong

    except WebSocketDisconnect:
        logger.info(f"WebSocket client {client_id} disconnected")
        connection_manager.disconnect(client_id)

    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
        connection_manager.disconnect(client_id)


async def send_current_job_status(job_id: str, client_id: str):
    """Send current job status to a client"""
    try:
        from app.services.domain.job_service import get_job_service

        job_service = get_job_service()
        job = job_service.get_job(job_id)

        if job:
            await connection_manager.send_personal_message({
                "type": "job_update",
                "update_type": "status",
                "job_id": job_id,
                "data": {
                    "status": job.status,
                    "created_at": job.created_at.isoformat() if job.created_at else None,
                    "estimates": job.estimates.dict() if job.estimates else None,
                    "run_id": job.run_id
                }
            }, client_id)

            # If job has a run, send run status too
            if job.run_id:
                await send_run_status(job.run_id, job_id, client_id)

    except Exception as e:
        logger.error(f"Error sending job status: {e}")


async def send_run_status(run_id: int, job_id: str, client_id: str):
    """Send current run status to a client"""
    try:
        from app.repositories.analysis_control import AnalysisControlRepo

        run_status = AnalysisControlRepo.get_run_status(run_id)

        if run_status:
            await connection_manager.send_personal_message({
                "type": "job_update",
                "update_type": "progress",
                "job_id": job_id,
                "data": {
                    "run_id": run_id,
                    "status": run_status.get("status"),
                    "processed_items": run_status.get("processed_items", 0),
                    "total_items": run_status.get("total_items", 0),
                    "progress_percent": run_status.get("progress_percent", 0)
                }
            }, client_id)

    except Exception as e:
        logger.error(f"Error sending run status: {e}")


# Helper function to broadcast job updates (called from job service)
async def broadcast_job_update(job_id: str, update_type: str, data: dict):
    """Broadcast a job update to all subscribers"""
    await connection_manager.send_job_update(job_id, update_type, data)