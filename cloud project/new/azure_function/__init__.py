import azure.functions as func
from azure.functions.asgi import AsgiMiddleware

from app.main import app

asgi_app = AsgiMiddleware(app)


def main(req: func.HttpRequest, context: func.Context) -> func.HttpResponse:
    return asgi_app.handle(req, context)
