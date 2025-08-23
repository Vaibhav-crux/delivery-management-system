import logging

logger = logging.getLogger(__name__)

class LifespanMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    logger.info("Lifespan startup received")
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    logger.info("Lifespan shutdown received")
                    await send({"type": "lifespan.shutdown.complete"})
                    break
        else:
            await self.app(scope, receive, send)