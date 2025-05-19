from fastapi import FastAPI, HTTPException, Depends, status
from pydantic import BaseModel
from typing import List, Optional
from datetime import date
import uvicorn
from enum import Enum

# Define enums for constrained fields
class StatusEnum(str, Enum):
    PAS_COMMENCE = "Pas commencé"
    EN_COURS = "En cours"
    TERMINEE = "Terminée"

class PriorityEnum(str, Enum):
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"

# Define Task data model
class TaskBase(BaseModel):
    Task_Name__c: str
    Status: StatusEnum
    Capacite__c: int
    Effort_Realise__c: int
    subject: str = "Other"  # Default value
    Priority: PriorityEnum

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int
    
    class Config:
        orm_mode = True

# Initialize FastAPI app
app = FastAPI(title="Task Management API", 
              description="API for managing Task objects",
              version="1.0.0")

# In-memory database with 20 pre-populated tasks
tasks_db = [
    Task(
        id=1,
        Task_Name__c="Complete project requirements documentation",
        Status=StatusEnum.EN_COURS if i % 3 == 1 else 
              (StatusEnum.TERMINEE if i % 3 == 2 else StatusEnum.PAS_COMMENCE),
        Capacite__c=80 - (i % 5) * 10,
        Effort_Realise__c=20 + (i % 4) * 15,
        Priority=PriorityEnum.HIGH if i % 3 == 0 else 
               (PriorityEnum.NORMAL if i % 3 == 1 else PriorityEnum.LOW)
    ) for i in range(1, 21)
]

# Rename task names to make them unique and meaningful
task_names = [
    "api test 5",
    "Complete project requirements documentation",
    "Develop frontend UI components",
    "Set up database schema and models",
    "Implement API authentication",
    "Create automated test suite",
    "Perform security audit",
    "Optimize database queries",
    "Deploy application to staging",
    "Conduct user acceptance testing",
    "Fix reported bugs in module A",
    "Update user documentation",
    "Refactor legacy code module",
    "Integrate with third-party payment API",
    "Create admin dashboard",
    "Implement user notification system",
    "Perform load testing",
    "Migrate data from old system",
    "Review and improve error handling",
    "Implement logging and monitoring",
    "Prepare release notes for v1.0"
]

# Update task names
for i, task in enumerate(tasks_db):
    task.Task_Name__c = task_names[i]

# API routes
@app.post("/tasks/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate):
    """Create a new task"""
    global tasks_db
    new_task = Task(
        id=len(tasks_db) + 1,
        Task_Name__c=task.Task_Name__c,
        Status=task.Status,
        Capacite__c=task.Capacite__c,
        Effort_Realise__c=task.Effort_Realise__c,
        subject=task.subject,
        Priority=task.Priority
    )
    tasks_db.append(new_task)
    return new_task

@app.get("/tasks/", response_model=List[Task])
def read_tasks(skip: int = 0, limit: int = 100):
    """Retrieve a list of tasks"""
    return tasks_db[skip : skip + limit]

@app.get("/tasks/{task_id}", response_model=Task)
def read_task(task_id: int):
    """Retrieve a specific task by ID"""
    for task in tasks_db:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(task_id: int, task_update: TaskBase):
    """Update an existing task"""
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            updated_task = Task(
                id=task_id,
                Task_Name__c=task_update.Task_Name__c,
                Status=task_update.Status,
                Capacite__c=task_update.Capacite__c,
                Effort_Realise__c=task_update.Effort_Realise__c,
                subject=task_update.subject,
                Priority=task_update.Priority
            )
            tasks_db[i] = updated_task
            return updated_task
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int):
    """Delete a task"""
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            tasks_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="Task not found")

# Run the server
if __name__ == "__main__":
    uvicorn.run("task_api:app", host="0.0.0.0", port=8000, reload=True)
