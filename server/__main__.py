"""Start the local web server with python -m server."""
import argparse
from getpass import getpass
import os
from pathlib import Path


def main(argv=None):
    """Configure local defaults before importing and running the Flask app."""
    parser = argparse.ArgumentParser(description="Run Writer's Workbench.")
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int,
                        default=os.getenv('PORT', '8002'))
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error('--port must be between 1 and 65535')

    password = os.getenv('WRITERS_EDITOR_PASSWORD')
    if not password:
        try:
            password = getpass('Choose an editor password: ')
        except (EOFError, KeyboardInterrupt):
            parser.error('Set WRITERS_EDITOR_PASSWORD or enter a password')
        if not password.strip():
            parser.error('Editor password must not be empty')
        os.environ['WRITERS_EDITOR_PASSWORD'] = password

    root = Path(__file__).resolve().parents[1]
    os.environ.setdefault('DATABASE', 'sqlite')
    os.environ.setdefault('SQLITE_LOC', str(root / 'database'))
    os.environ.setdefault('OUR_NAME', 'WritersWorkbench')
    os.environ.setdefault('WRITERS_EDITOR_USERNAME', 'editor')
    if os.environ['DATABASE'] == 'sqlite':
        Path(os.environ['SQLITE_LOC']).mkdir(parents=True, exist_ok=True)

    from server.endpoints import app

    app.config.update(
        EDITOR_USERNAME=os.environ['WRITERS_EDITOR_USERNAME'],
        EDITOR_PASSWORD=password,
    )
    print(f'Web interface: http://{args.host}:{args.port}/web/')
    app.run(host=args.host, port=args.port)


if __name__ == '__main__':
    main()
