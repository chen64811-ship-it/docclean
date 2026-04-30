#请求体参数
from fastapi import FastAPI
from pydantic import BaseModel  
app = FastAPI()

class User(BaseModel):
    name: str
    age: int
    pwd : str|None = None   
    sex: str|None = None
    email: str


@app.post("/user/")
def create_user(user: dict):
    return user 


@app.post("/user2")
def create_user(user: User):
    return user 




if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main05:app", host="127.0.0.1", port=8000, reload=True)     
