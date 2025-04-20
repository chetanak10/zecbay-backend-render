from zecbay_admin.wsgi import application
from vercel_wsgi import handle_request

def handler(event, context):
    return handle_request(event, context, application)
