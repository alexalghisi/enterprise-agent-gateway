class GatewayError(Exception):
    code = "gateway_error"
    status_code = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(GatewayError):
    code = "not_found"
    status_code = 404


class VerificationFailedError(GatewayError):
    code = "verification_failed"
    status_code = 401


class ForbiddenError(GatewayError):
    code = "forbidden"
    status_code = 403


class CoverageError(GatewayError):
    code = "not_covered"
    status_code = 422


class ConflictError(GatewayError):
    code = "conflict"
    status_code = 409
