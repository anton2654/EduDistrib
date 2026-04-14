from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.application.dto.task_dto import TaskCreateDTO, TaskReadDTO, TaskUpdateDTO
from app.application.services.task_service import TaskNotFoundError, TaskService
from app.presentation.api.dependencies import (
    get_task_create_form,
    get_task_service,
    get_task_update_form,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

TaskServiceDependency = Annotated[TaskService, Depends(get_task_service)]
TaskCreateFormDependency = Annotated[TaskCreateDTO, Depends(get_task_create_form)]
TaskUpdateFormDependency = Annotated[TaskUpdateDTO, Depends(get_task_update_form)]


@router.post("/", response_model=TaskReadDTO, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_in: TaskCreateFormDependency,
    service: TaskServiceDependency,
) -> TaskReadDTO:
    task = await service.create_task(task_in)
    return TaskReadDTO.model_validate(task)


@router.get("/", response_model=list[TaskReadDTO])
async def list_tasks(service: TaskServiceDependency) -> list[TaskReadDTO]:
    tasks = await service.list_tasks()
    return [TaskReadDTO.model_validate(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskReadDTO)
async def get_task(task_id: int, service: TaskServiceDependency) -> TaskReadDTO:
    try:
        task = await service.get_task(task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return TaskReadDTO.model_validate(task)


@router.put("/{task_id}", response_model=TaskReadDTO)
async def update_task(
    task_id: int,
    task_in: TaskUpdateFormDependency,
    service: TaskServiceDependency,
) -> TaskReadDTO:
    try:
        task = await service.update_task(task_id, task_in)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return TaskReadDTO.model_validate(task)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(task_id: int, service: TaskServiceDependency) -> Response:
    try:
        await service.delete_task(task_id)
    except TaskNotFoundError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error

    return Response(status_code=status.HTTP_204_NO_CONTENT)