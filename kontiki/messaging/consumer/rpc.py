import asyncio
import inspect
from typing import get_type_hints

from aio_pika import Message

from kontiki.messaging.reconstruct import model_type
from kontiki.messaging.rpc import RpcErrorType, RpcReturn
from kontiki.runtime.handler_scope import enter_handler_scope, reset_handler_scope
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
        self._consumer_tag = None

    async def stop_accepting(self):
        if self._consumer_tag:
            await self.queue.cancel(self._consumer_tag)
            self._consumer_tag = None

    async def run(self):
        async def handle_rpc(message):
            if self.container.shutting_down:
                await message.nack(requeue=True)
                return

            handler_task = asyncio.create_task(self._handle_rpc(message))
            self.container.amqp_consumer.register_handler_task(handler_task)
            try:
                await handler_task
            finally:
                self.container.amqp_consumer.unregister_handler_task(handler_task)

        self._consumer_tag = await self.queue.consume(handle_rpc)

    def _apply_hint(self, hint, value):
        if not isinstance(value, dict):
            return value
        model = model_type(hint)
        if model is None:
            return value
        return model(**value)

    def _reconstruct_rpc_args(self, args, kwargs, handler):
        sig = inspect.signature(handler)
        type_hints = get_type_hints(handler)
        params = list(sig.parameters.items())

        new_args = []
        for i, param_value in enumerate(args):
            if i + 1 >= len(params):
                new_args.append(param_value)
                continue
            param_name, _param = params[i + 1]
            if param_name in ("self", "container", "_headers"):
                new_args.append(param_value)
                continue
            if param_name in type_hints:
                param_value = self._apply_hint(type_hints[param_name], param_value)
            new_args.append(param_value)

        new_kwargs = {}
        for name, value in kwargs.items():
            if name in ("self", "container", "_headers"):
                new_kwargs[name] = value
                continue
            if name in type_hints:
                value = self._apply_hint(type_hints[name], value)
            new_kwargs[name] = value

        return new_args, new_kwargs

    async def _handle_rpc(self, message):
        scope = enter_handler_scope(
            "rpc",
            self.name,
            headers=message.headers,
            work_in_flight=self.container.amqp_consumer.work_in_flight,
        )
        try:
            async with message.process(requeue=True):
                cid = message.correlation_id
                log.debug("Message received for correlation_id=%s", cid)
                if cid in self.futures:
                    log.error("Duplicate message (%s)", cid)
                    return

                loop = asyncio.get_running_loop()
                future = loop.create_future()
                self.futures[cid] = future

                try:
                    request = self.serializer.loads(message.body)
                    args = request.get("args", [])
                    kwargs = request.get("kwargs", {})
                except Exception as e:
                    log.error("Invalid RPC message format: %s", e)
                    del self.futures[cid]
                    return

                headers = message.headers if self.include_headers else None

                msg = "RPC request received: method=%s args=%s, kwargs=%s"
                log.info(msg, self.name, args, kwargs)

                try:
                    args, kwargs = self._reconstruct_rpc_args(args, kwargs, self.task)
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
                    log.error(msg, self.name, e, exc_info=True)
                    await self.container.report_uncaught_exception(e)
                    if not future.done():
                        future.set_result(
                            RpcReturn(
                                success=False,
                                message=str(e),
                                error_type=RpcErrorType.SERVER,
                                error_code="INTERNAL_ERROR",
                            )
                        )

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
        finally:
            reset_handler_scope(scope)
