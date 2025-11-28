import logging
import time


logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        # Log request details before processing
        logger.info(f"Request: {request.method} {request.path}")
        logger.debug(f"Request Headers: {request.headers}")
        logger.debug(f"Request Body:{request.body.decode('utf-8') if request.body else 'No Body'}")

        response = self.get_response(request)

        # Log response details after processing
        process_time = time.time() - start_time
        logger.info(
            f"Response: {response.status_code} for "
            f"{request.method} {request.path} (Processed in {process_time:.2f}s)"
        )
        logger.debug(f"Response Headers: {response.headers}")

        return response
