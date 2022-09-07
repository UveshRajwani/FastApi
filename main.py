# from typing import Optional
# from random import randint
# from fastapi import FastAPI, Response, status, HTTPException
# import pymongo
# from pydantic import BaseModel
# from bson.json_util import dumps, loads
#
# app = FastAPI()
# uri = "mongodb://localhost:27017"
# client = pymongo.MongoClient(uri)
# db = client.fastapi
# vg = db.posts
#
#
# class Post(BaseModel):
#     title: str
#     content: str
#     published: bool = True
#     rating: Optional[int] = None
#
#
# myPosts = [{'id': 815, 'title': 'Demo Post', 'content': 'Demo Content', 'published': True, 'rating': 9},
#            {'id': 5, 'title': 'Demo Post 1', 'content': 'Demo Content', 'published': True, 'rating': 9}]
#
#
# def find_post(id: int):
#     try:
#         result = list(vg.find({"id": id}, {"_id": 0}))
#         return result[0]
#     except IndexError:
#         return None
#
#
# @app.get("/")
# async def root():
#     return {"message": "Welcome to my api"}
#
#
# @app.get("/hello/{name}")
# async def say_hello(name: str):
#     return {"message": f"Hello {name}"}
#
#
# @app.post("/posts", status_code=status.HTTP_201_CREATED)
# def create_post(new_post: Post):
#     post_dict = new_post.dict()
#     post_dict['id'] = randint(0, 999)
#     print(post_dict['id'])
#     insert_result = vg.insert_one(post_dict)
#     return {"new_post": f"title {new_post.title}, content: {new_post.content} "}
#
#
# @app.get("/posts")
# def get_post():
#     result = list(vg.find({}, {"_id": 0}))
#     return result
#
#
# @app.get("/posts/{id}")
# def get_Post_By_Id(id: int, response: Response):
#     post = find_post(id)
#     if not post:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid post id")
#     else:
#         return post
#
#
# @app.delete("/posts/{id}")
# def delete_post(id: int):
#     post = find_post(id)
#     if not post:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid post id")
#     else:
#         vg.delete_one({"id":id})
#         return {"message": f"successfully deleted your post with the id of {id}"}
#
#
# @app.put("/posts/{id}")
# def update_post(id: int, new_post: Post):
#     post = find_post(id)
#     if not post:
#         raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid post id")
#     post_dict = dict(new_post)
#     post_dict['id'] = id
#     delete_post(id)
#     vg.insert_one(post_dict)
#     return post

