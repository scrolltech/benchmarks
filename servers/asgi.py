class App:

    def __init__(self, scope):
        self.scope = scope
        self.task: Optional[asyncio.Future] = None

    async def __call__(self, receive, send):
        body = bytearray()
        while True:
            event = await receive()
            if event['type'] == 'http.request':
                body.extend(event.get('body', b''))
                if not event.get('more_body', False):
                    await self.send_echo(send, body)
            elif event['type'] == 'http.disconnect':
                break

    async def send_echo(self, send, request_body):
        response = request_body
        content_length = len(response)
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': [(b'content-length', str(content_length).encode())],
        })
        await send({
            'type': 'http.response.body',
            'body': response,
            'more_body': False,
        })
