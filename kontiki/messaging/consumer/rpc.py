import asyncio

from aio_pika import Message

from kontiki.messaging.rpc import RpcErrorType, RpcReturn
from kontiki.utils import log


def rpc(_func=None, *, include_headers=False):
    def decorator(handler):
        handler._rpc_endpoint = {
            "name": handler.__name__,
            "include_headers": include_headers,
        }
        return handler

    if _func is None:
        return decorator
    return decorator(_func)


def rpc_error(error_code: str, msg: str):
    return RpcReturn(
        success=False,
        message=msg,
        error_type=RpcErrorType.CLIENT,
        error_code=error_code,
    )


class RpcTask:
    def __init__(
        self, name, task, container, reply_exchange, queue, serializer, include_headers
    ):
        self.container = container
        self.task = task
        self.reply_exchange = reply_exchange
        self.queue = queue
        self.futures = {}
        self.name = name
        self.serializer = serializer
        self.include_headers = include_headers

    async def run(self):
        async def handle_rpc(message):
            async with message.process():
                # Identify each request/response pair.
                cid = message.correlation_id
                log.debug("Message received for correlation_id=%s", cid)
                if cid in self.futures:
                    log.error("Duplicate message (%s)", cid)
                    return

                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self.futures[cid] = future

                # Parse the request
                try:
                    request = self.serializer.loads(message.body)
                    args = request.get("args", [])
                    kwargs = request.get("kwargs", {})
                    headers = message.headers if self.include_headers else None
                except Exception as e:
                    log.error("Invalid RPC message format: %s", e)
                    del self.futures[cid]
                    return

                msg = "RPC request received: method=%s args=%s, kwargs=%s"
                log.info(msg, self.name, args, kwargs)

                # Call the handler
                try:
                    if headers:
                        response_data = await self.task(
                            self.container, *args, **kwargs, _headers=headers
                        )
                    else:
                        response_data = await self.task(self.container, *args, **kwargs)

                    if not isinstance(response_data, RpcReturn):
                        response_data = RpcReturn(success=True, result=response_data)

                    if response_data is None:
                        response_data = ""
                    if not future.done():
                        future.set_result(response_data)

                except Exception as e:
                    msg = "Error while processing RPC method %s: %s"
                    log.error(msg, self.name, e)
                    if not future.done():
                        future.set_result(
                            RpcReturn(
                                success=False,
                                message=str(e),
                                error_type=RpcErrorType.SERVER,
                                error_code="INTERNAL_ERROR",
                            )
                        )

                # Send the response
                if message.reply_to:
                    try:
                        response_data = await future
                        serialized = self.serializer.dumps(response_data)
                        log.debug("Reply %s to %s", serialized, message.reply_to)
                        response_message = Message(body=serialized, correlation_id=cid)
                        await self.reply_exchange.publish(
                            response_message, routing_key=message.reply_to
                        )
                    except Exception as e:
                        log.error("Failed to send response: %s", e)
                    finally:
                        if cid in self.futures:
                            del self.futures[cid]

        # Start consuming messages for RPC
        await self.queue.consume(handle_rpc)
