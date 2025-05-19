from fastapi import FastAPI, HTTPException, Depends, status, Security
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, SecurityScopes
from pydantic import BaseModel, ValidationError
from typing import List, Optional
from datetime import date, datetime, timedelta
import uvicorn
from enum import Enum
from jose import JWTError, jwt

# Security configuration - use a fixed secret key
SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Define enums for constrained fields
class StatusEnum(str, Enum):
    PAS_COMMENCE = "Pas commencé"
    EN_COURS = "En cours"
    TERMINEE = "Terminée"

class PriorityEnum(str, Enum):
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"

# User models
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None
    scopes: List[str] = []

class User(BaseModel):
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None
    scopes: List[str] = []

class UserInDB(User):
    password: str

# Task models
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

# OAuth2 configuration
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="token",
    scopes={
        "tasks:read": "Read tasks",
        "tasks:write": "Create and modify tasks"
    }
)

# Initialize FastAPI app
app = FastAPI(title="Task Management API", 
              description="API for managing Task objects with OAuth 2.0 authentication",
              version="1.0.0")

# Fake users database with different permission scopes
fake_users_db = {
    "admin": {
        "username": "admin",
        "full_name": "Administrator",
        "email": "admin@example.com",
        "password": "adminpassword",  # Plain password for simplicity
        "disabled": False,
        "scopes": ["tasks:read", "tasks:write"]
    },
    "user": {
        "username": "user",
        "full_name": "Regular User",
        "email": "user@example.com",
        "password": "userpassword",  # Plain password for simplicity
        "disabled": False,
        "scopes": ["tasks:read"]  # Read-only access
    }
}

# Task names for pre-populated tasks
task_names = [
    "test api3",
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

# Pre-populate tasks
tasks_db = []
for i in range(20):
    status_value = StatusEnum.EN_COURS if i % 3 == 1 else (StatusEnum.TERMINEE if i % 3 == 2 else StatusEnum.PAS_COMMENCE)
    priority_value = PriorityEnum.HIGH if i % 3 == 0 else (PriorityEnum.NORMAL if i % 3 == 1 else PriorityEnum.LOW)
    
    tasks_db.append(
        Task(
            id=i+1,
            Task_Name__c=task_names[i],
            Status=status_value,
            Capacite__c=80 - (i % 5) * 10,
            Effort_Realise__c=20 + (i % 4) * 15,
            Priority=priority_value
        )
    )

# Authentication functions
def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    return None

def authenticate_user(fake_db, username: str, password: str):
    user = get_user(fake_db, username)
    if not user:
        return False
    if password != user.password:  # Simple comparison for testing
        return False
    return user

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    security_scopes: SecurityScopes, 
    token: str = Depends(oauth2_scheme)
):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = "Bearer"
        
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_scopes = payload.get("scopes", [])
        token_data = TokenData(username=username, scopes=token_scopes)
    except (JWTError, ValidationError):
        raise credentials_exception
        
    user = get_user(fake_users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
        
    # Check if the user has all the required scopes
    for scope in security_scopes.scopes:
        if scope not in token_data.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
                headers={"WWW-Authenticate": authenticate_value},
            )
    
    return user

async def get_current_active_user(
    current_user: User = Security(get_current_user, scopes=[])
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Authentication endpoint
@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(fake_users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Only include scopes that the user has access to and were requested
    scopes = [scope for scope in form_data.scopes if scope in user.scopes]
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "scopes": scopes},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

# Task API routes with OAuth2 scopes
@app.post("/tasks/", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(
    task: TaskCreate, 
    current_user: User = Security(get_current_active_user, scopes=["tasks:write"])
):
    """Create a new task (requires write scope)"""
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
def read_tasks(
    skip: int = 0, 
    limit: int = 100, 
    current_user: User = Security(get_current_active_user, scopes=["tasks:read"])
):
    """Retrieve a list of tasks (requires read scope)"""
    return tasks_db[skip : skip + limit]

@app.get("/tasks/{task_id}", response_model=Task)
def read_task(
    task_id: int, 
    current_user: User = Security(get_current_active_user, scopes=["tasks:read"])
):
    """Retrieve a specific task by ID (requires read scope)"""
    for task in tasks_db:
        if task.id == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.put("/tasks/{task_id}", response_model=Task)
def update_task(
    task_id: int, 
    task_update: TaskBase, 
    current_user: User = Security(get_current_active_user, scopes=["tasks:write"])
):
    """Update an existing task (requires write scope)"""
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
def delete_task(
    task_id: int, 
    current_user: User = Security(get_current_active_user, scopes=["tasks:write"])
):
    """Delete a task (requires write scope)"""
    for i, task in enumerate(tasks_db):
        if task.id == task_id:
            tasks_db.pop(i)
            return
    raise HTTPException(status_code=404, detail="Task not found")

# Run the server
if __name__ == "__main__":
    uvicorn.run("task_api:app", host="0.0.0.0", port=8000, reload=True)
