# 生成一个 FastAPI 应用
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn

app = FastAPI()

# 允许跨域请求（前端调用时需要）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 定义一个路由，访问根路径时返回一个字符串
@app.get("/")
def read_root():
    return {"Hello": "World"}

# 模拟用户数据
fake_users = {
    1: {"id": 1, "name": "张三", "email": "zhangsan@example.com"},
    2: {"id": 2, "name": "李四", "email": "lisi@example.com"},
}

# 获取所有用户列表
@app.get("/users")
def get_users():
    return list(fake_users.values())

# 根据用户ID获取单个用户
@app.get("/users/{user_id}")
def get_user(user_id: int):
    user = fake_users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

