from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import uvicorn
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_FILE = "api_tasks.json"

def load_tasks():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tasks(tasks):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

user_tasks = load_tasks()

class Task(BaseModel):
    text: str
    status: str = "pending"
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    
    class Config:
        protected_namespaces = ()

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    text: Optional[str] = None
    
    class Config:
        protected_namespaces = ()

@app.get("/")
async def root():
    return {"message": "Task API is running"}

@app.get("/users/{user_id}/tasks")
async def get_user_tasks(user_id: str):
    if user_id not in user_tasks:
        return []
    return user_tasks[user_id]

@app.post("/users/{user_id}/tasks")
async def create_task(user_id: str, task: Task):
    if user_id not in user_tasks:
        user_tasks[user_id] = []
    
    if not task.created_at:
        task.created_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    new_task = task.model_dump()
    user_tasks[user_id].append(new_task)
    save_tasks(user_tasks)
    
    return {"message": "Task created", "task": new_task, "task_id": len(user_tasks[user_id]) - 1}

@app.get("/users/{user_id}/tasks/{task_id}")
async def get_task(user_id: str, task_id: int):
    if user_id not in user_tasks:
        raise HTTPException(status_code=404, detail="User not found")
    
    if task_id < 0 or task_id >= len(user_tasks[user_id]):
        raise HTTPException(status_code=404, detail="Task not found")
    
    return user_tasks[user_id][task_id]

@app.put("/users/{user_id}/tasks/{task_id}")
async def update_task(user_id: str, task_id: int, task_update: TaskUpdate):
    if user_id not in user_tasks:
        raise HTTPException(status_code=404, detail="User not found")
    
    if task_id < 0 or task_id >= len(user_tasks[user_id]):
        raise HTTPException(status_code=404, detail="Task not found")
    
    task = user_tasks[user_id][task_id]
    
    if task_update.status:
        task["status"] = task_update.status
        if task_update.status == "completed":
            task["completed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
        else:
            task.pop("completed_at", None)
    
    if task_update.text:
        task["text"] = task_update.text
    
    save_tasks(user_tasks)
    
    return {"message": "Task updated", "task": task}

@app.delete("/users/{user_id}/tasks/{task_id}")
async def delete_task(user_id: str, task_id: int):
    if user_id not in user_tasks:
        raise HTTPException(status_code=404, detail="User not found")
    
    if task_id < 0 or task_id >= len(user_tasks[user_id]):
        raise HTTPException(status_code=404, detail="Task not found")
    
    deleted_task = user_tasks[user_id].pop(task_id)
    save_tasks(user_tasks)
    
    return {"message": "Task deleted", "task": deleted_task}

@app.delete("/users/{user_id}/tasks")
async def delete_all_user_tasks(user_id: str):
    if user_id in user_tasks:
        user_tasks[user_id] = []
        save_tasks(user_tasks)
    
    return {"message": "All tasks deleted"}

uvicorn.run(app, host="127.0.0.1", port=8000)