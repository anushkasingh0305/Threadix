from fastapi import HTTPException, status


class NotFoundError(HTTPException):
    def __init__(self, resource: str):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND,
                         detail=f'{resource} not found')


class ForbiddenError(HTTPException):
    def __init__(self, msg='Insufficient permissions'):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=msg)


class ConflictError(HTTPException):
    def __init__(self, msg):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=msg)


class ValidationError(HTTPException):
    def __init__(self, msg):
        super().__init__(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=msg)
