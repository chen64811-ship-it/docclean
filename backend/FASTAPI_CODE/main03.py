#路径参数 
from fastapi import FastAPI
app = FastAPI()

@app.get("/args/1")
def path_args1():
    return {"message": "id1 is path args"}

@app.get("/args2/{id}")
def path_args2(id: int):
    return {"message1": f"id{id} is path args"}

@app.get("/args3/{id}")
def path_args3(id: int):
    return {"message2": f"id{id} is path args"}

# 这里是重点：/args4/3/{id}/{name} 必须带斜杠
@app.get("/args4/3/{id}/{name}")
def path_args4(id: int, name: str):
    return {"message3": f"id{id} and name{name} are path args"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main03:app", host="127.0.0.1", port=8000, reload=True)