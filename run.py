"""Run the local alarm clock web server."""

import argparse

from alarm_clock.application import ClockApplication


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Earlybird alarm clock UI.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    return parser.parse_args()


def main() -> None:
    print("Starting server.")
    arguments = parse_arguments()
    application = ClockApplication()
    server = application.create_server(arguments.host, arguments.port)
    print(f"Alarm clock UI available at http://{arguments.host}:{arguments.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping alarm clock server.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
