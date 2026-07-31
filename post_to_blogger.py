import os
import pickle
import base64
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/blogger"]


def write_file_from_env(env_name, output_file, binary=False):
    value = os.getenv(env_name)
    if not value:
        return

    if binary:
        data = base64.b64decode(value)
        with open(output_file, "wb") as f:
            f.write(data)
    else:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(value)


def prepare_auth_files():
    if not os.path.exists("credentials.json"):
        write_file_from_env("BLOGGER_CREDENTIALS_JSON", "credentials.json", binary=False)

    if not os.path.exists("token.pickle"):
        token_b64 = os.getenv("BLOGGER_TOKEN_PICKLE_B64")
        if token_b64:
            write_file_from_env("BLOGGER_TOKEN_PICKLE_B64", "token.pickle", binary=True)


def create_blogger_service():
    prepare_auth_files()

    creds = None

    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
            with open("token.pickle", "wb") as token:
                pickle.dump(creds, token)

    return build("blogger", "v3", credentials=creds)


def create_post(service, blog_id, title, content, labels=None, is_draft=False):
    if labels is None:
        labels = []

    body = {
        "kind": "blogger#post",
        "title": title,
        "content": content,
        "labels": labels
    }

    post = service.posts().insert(
        blogId=blog_id,
        body=body,
        isDraft=True
    ).execute()

    if not is_draft:
        post = service.posts().publish(
            blogId=blog_id,
            postId=post["id"]
        ).execute()

    return post