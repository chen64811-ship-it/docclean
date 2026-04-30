from fastapi import FastAPI
from pydantic import BaseModel  
cxy = FastAPI()

class book(BaseModel):
    bookname: str
    author: str
    price: float
    press: float|None = None


@cxy.post("/book/")
def create_book(book: book):
  return {
    "message": "图书添加成功",
    "book": book
}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("practise2:cxy", host="127.0.0.1", port=8000, reload=True)