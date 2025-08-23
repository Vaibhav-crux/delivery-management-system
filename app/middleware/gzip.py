import gzip
from io import BytesIO
from quart import Response, request

class GzipMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Handle lifespan events
        if scope["type"] == "lifespan":
            await self.app(scope, receive, send)
            return

        # Handle HTTP requests
        if scope["type"] == "http":
            # Capture the original response
            response = await self.app(scope, receive, send)

            # Check if client accepts gzip and response is compressible
            accept_encoding = next(
                (header[1].decode().lower() for header in scope.get("headers", [])
                 if header[0].decode().lower() == "accept-encoding"),
                ""
            )
            if (
                "gzip" in accept_encoding
                and response.status_code == 200
                and "Content-Encoding" not in response.headers
                and response.headers.get("Content-Type", "").startswith(("application/json", "text/"))
                and len(await response.get_data()) > 1024  # Compress only if data > 1KB
            ):
                # Compress the response data
                data = await response.get_data()
                gzip_buffer = BytesIO()
                with gzip.GzipFile(mode="wb", fileobj=gzip_buffer) as gzip_file:
                    gzip_file.write(data)
                compressed_data = gzip_buffer.getvalue()

                # Create new response with compressed data
                response = Response(
                    compressed_data,
                    status=response.status_code,
                    headers=response.headers,
                    mimetype=response.mimetype
                )
                response.headers["Content-Encoding"] = "gzip"
                response.headers["Content-Length"] = len(compressed_data)

            return response

        # Pass through other scope types
        await self.app(scope, receive, send)