from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.dto.task_dto import TaskCreateDTO, TaskUpdateDTO
from app.application.interfaces.task_repository import TaskRepositoryInterface
from app.domain.entities.task import Task


class TaskRepository(TaskRepositoryInterface):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, task_in: TaskCreateDTO) -> Task:
        task = Task(**task_in.model_dump())
        self._session.add(task)
        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def get_by_id(self, task_id: int) -> Task | None:
        return await self._session.get(Task, task_id)

    async def list_all(self) -> list[Task]:
        stmt = select(Task).order_by(Task.id)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, task: Task, task_in: TaskUpdateDTO) -> Task:
        for field, value in task_in.model_dump(exclude_unset=True).items():
            setattr(task, field, value)

        await self._session.commit()
        await self._session.refresh(task)
        return task

    async def delete(self, task: Task) -> None:
        await self._session.delete(task)
        await self._session.commit()