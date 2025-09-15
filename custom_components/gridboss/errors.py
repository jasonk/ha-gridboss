from aiohttp import ClientResponse

class GridBossError(Exception):
    pass

class GridBossAuthRequiredError(GridBossError):
    def __init__(self):
        super().__init__("Authentication Required")

class GridBossAPIError(GridBossError):
    def __init__(
        self,
        message: str,
        response: ClientResponse,
    ):
        super().__init__(message)
        self.response = response

class GridBossAuthError(GridBossAPIError):
    pass
