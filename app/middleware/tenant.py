from fastapi import Request


def get_subdomain_from_host(request: Request) -> str | None:
    host = request.headers.get("host", "")
    parts = host.split(".")
    if len(parts) >= 3:
        return parts[0]
    return None


def get_tenant(request: Request) -> str | None:
    subdomain = get_subdomain_from_host(request)
    if subdomain:
        return subdomain
    return request.headers.get("x-tenant-id")
