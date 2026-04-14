from app.application.dto.task_dto import TaskCreateDTO, TaskUpdateDTO
from app.application.interfaces.task_repository import TaskRepositoryInterface
from app.domain.entities.task import Task


class TaskNotFoundError(Exception):
    def __init__(self, task_id: int) -> None:
        super().__init__(f"Task with id {task_id} was not found.")


class TaskService:
    def __init__(self, repository: TaskRepositoryInterface) -> None:
        self._repository = repository

    async def create_task(self, task_in: TaskCreateDTO) -> Task:
        return await self._repository.create(task_in)

    async def list_tasks(self) -> list[Task]:
        return await self._repository.list_all()

    async def get_task(self, task_id: int) -> Task:
        task = await self._repository.get_by_id(task_id)
        if task is None:
            raise TaskNotFoundError(task_id)
        return task

    async def update_task(self, task_id: int, task_in: TaskUpdateDTO) -> Task:
        task = await self.get_task(task_id)
        return await self._repository.update(task, task_in)

    async def delete_task(self, task_id: int) -> None:
        task = await self.get_task(task_id)
        await self._repository.delete(task)