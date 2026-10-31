import uuid
from core.config import settings
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Cookie, Response, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
import os
from db.database import get_db, SessionLocal
from models.gps_job import gpsJob
from schemas.gps import CreateJob, CreateJobResponse, ProcessQuery, QueryResponse, FileRequest

router = APIRouter(
    prefix="/clone",
    tags=["clone"]
)

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
        from_coord = request.from_coord,
        to_coord = request.to_coord,
        algorithm = request.algorithm
    )

    db.add(job)
    db.commit()

    return job

@router.post("/process_query", response_model=QueryResponse)
def process_query(
        request: ProcessQuery,
        background_tasks: BackgroundTasks,
        response: Response,
        db: Session = Depends(get_db)
):
    #response.set_cookie(key="session_id", value=session_id, httponly=True)

    fetched_job = db.get(gpsJob, request.id)

    # pathfinding function

    fetched_job.status = "complete"
    db.commit()

    return fetched_job

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
def get_session_id(session_id: Optional[str] = Cookie(None)):
    if not session_id:
        session_id = str(uuid.uuid4())
    return session_id

@router.post("/create", response_model=StoryJobResponse)
def create_story(
        request: CreateStoryRequest,
        background_tasks: BackgroundTasks,
        response: Response,
        session_id: str = Depends(get_session_id),
        db: Session = Depends(get_db)
):
    response.set_cookie(key="session_id", value=session_id, httponly=True)

    job_id = str(uuid.uuid4())

    job = StoryJob(
        job_id=job_id,
        session_id=session_id,
        theme=request.theme,
        status="pending"
    )
    db.add(job)
    db.commit()

    # TODO: Add Background Tasks, generate story
    background_tasks.add_task(
        generate_story_task,
        job_id=job_id,
        theme=request.theme,
        session_id=session_id
    )

    return job

def generate_story_task(
        job_id: str,
        theme: str,
        session_id: str
):
    db = SessionLocal()

    try:
        job = db.query(StoryJob).filter(StoryJob.job_id == job_id).first()

        if not job:
            return

        try:
            job.status = "processing"
            db.commit()

            story = {} # TODO: Generate Story

            job.story_id = 1 # TODO: update story id
            job.status = "completed"
            job.completed_at = datetime.now()
            db.commit()

        except Exception as e:
            job.status = "failed"
            job.completed_at = datetime.now()
            job.error = str(e)
            db.commit()
    finally:
        db.close()


@router.get("/{story_id}/complete", response_model=CompleteStoryResponse)
def get_complete_story(
        story_id: int,
        db: Session = Depends(get_db)
):
    story = db.query(Story).filter(Story.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    # TODO: Parse story
    return story

def build_complete_story_tree(
        db: Session,
        story: Story
) -> CompleteStoryResponse:
    pass
# backendurl/api/stories/createstory
'''