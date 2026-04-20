from fastapi import APIRouter
from backend.storage import get_posts

router = APIRouter()


@router.get("/posts")
def get_posts_api():

    posts = get_posts(limit=100)

    ranked_posts = sorted(
        posts,
        key=lambda x: (
            float(x.get("priority", 0)),
            float(x.get("timestamp", 0))
        ),
        reverse=True
    )

    return {
        "count": len(ranked_posts),
        "posts": ranked_posts
    }


@router.get("/posts/{post_id}")
def get_post(post_id: int):

    posts = get_posts(limit=200)

    for post in posts:
        if int(post.get("id", 0)) == post_id:
            return post

    return {
        "error": "post not found",
        "post_id": post_id
    }
