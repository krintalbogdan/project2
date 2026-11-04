import uuid
from core.config import settings
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import algorithms.djikstras
import algorithms.a_star
import os
import json
from db.database import get_db, SessionLocal
from models.gps_job import gpsJob
from schemas.gps import CreateJob, CreateJobResponse, ProcessQuery, QueryResponse

router = APIRouter(
    prefix="/clone",
    tags=["clone"]
)

def run_pathfinding_task(job_id: int):
    db: Session = SessionLocal()
    fetched_job = db.get(gpsJob, job_id)

    # pathfinding function
    from_cord = json.loads(fetched_job.from_coord)
    to_cord = json.loads(fetched_job.to_coord)
    points = None    
    if fetched_job.algorithm == "dijkstra":
        points = algorithms.djikstras.execute_dijkstra(from_cord, to_cord)
    if fetched_job.algorithm == "astar":
        points = algorithms.a_star.execute_astar(from_cord, to_cord)
    fetched_job.path = json.dumps(points)
    fetched_job.status = "complete"
    db.commit()

@router.post("/create", response_model=CreateJobResponse)
def create_job(
        request: CreateJob,
        background_tasks: BackgroundTasks,
        response: Response,
        db: Session = Depends(get_db)
):
    #response.set_cookie(key="session_id", value=session_id, httponly=True)

    job = gpsJob(
        status = "working",
        from_coord = json.dumps(request.from_coord),
        to_coord = json.dumps(request.to_coord),
        algorithm = request.algorithm
    )

    db.add(job)
    db.commit()
    background_tasks.add_task(run_pathfinding_task, job.id)

    return job

@router.post("/process_query", response_model=QueryResponse)
def process_query(
        request: ProcessQuery,
        background_tasks: BackgroundTasks,
        response: Response,
        db: Session = Depends(get_db)
):
    
    fetched_job = db.get(gpsJob, request.id)

    return {
        "id": fetched_job.id,
        "status": fetched_job.status,
        "algorithm": fetched_job.algorithm,
        "from_coord": json.loads(fetched_job.from_coord) if fetched_job.from_coord else [],
        "to_coord": json.loads(fetched_job.to_coord) if fetched_job.to_coord else [],
        "path": json.loads(fetched_job.path) if fetched_job.path else []
    }
'''
@router.post("/retrieve_file", response_model=QueryResponse)
def process_query(
        request: ProcessQuery,
        background_tasks: BackgroundTasks,
        response: Response,
        db: Session = Depends(get_db)
):
    
    fetched_job = db.get(gpsJob, request.id)
    if not fetched_job:
        raise HTTPException(status_code=404, detail="Job not found")

    background_tasks.add_task(run_pathfinding_task, fetched_job.id)

    return fetched_job
'''
'''
@router.post("/retrieve_file")
def retrieve_file(
        request: FileRequest,
        background_tasks: BackgroundTasks,
        db: Session = Depends(get_db)
):
    #response.set_cookie(key="session_id", value=session_id, httponly=True)

    return FileResponse(
        path=settings.STATIC_URL + "/gps_files/" + str(request.id) + "file.gpx",
        media_type="application/gpx+xml"
    )
'''