from abc import ABC, abstractmethod

from app.application.dto.task_dto import TaskCreateDTO, TaskUpdateDTO
from app.domain.entities.task import Task


class TaskRepositoryInterface(ABC):
    @abstractmethod
    async def create(self, task_in: TaskCreateDTO) -> Task:
        raise NotImplementedError

    @abstractmethod
    async def get_by_id(self, task_id: int) -> Task | None:
        raise NotImplementedError

    @abstractmethod
    async def list_all(self) -> list[Task]:
        raise NotImplementedError

    @abstractmethod
    async def update(self, task: Task, task_in: TaskUpdateDTO) -> Task:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, task: Task) -> None:
        raise NotImplementedError