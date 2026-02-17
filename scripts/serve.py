"""Start the dev server."""

import uvicorn


def main():
    uvicorn.run("app.main:app", reload=True, timeout_graceful_shutdown=1)


if __name__ == "__main__":
    main()
