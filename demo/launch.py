#!/usr/bin/env python3
"""One-command local launcher. No third-party runtime dependencies."""
import argparse
import os
import sys
import threading
import webbrowser
from pathlib import Path


def main():
    if sys.version_info < (3, 10):
        raise SystemExit('Python 3.10+ required / 需要 Python 3.10 或更新版本')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    parser.add_argument('--no-browser', action='store_true')
    parser.add_argument('--configure', action='store_true')
    args = parser.parse_args()
    if args.configure:
        import getpass
        import json
        path = Path(__file__).parent / 'data' / 'provider.json'
        print('DeepSeek configuration / DeepSeek 配置。Empty key keeps existing settings.')
        key = getpass.getpass('API key (hidden) / 密钥（隐藏输入）: ').strip()
        if key:
            path.parent.mkdir(exist_ok=True)
            settings = json.loads(path.read_text()) if path.exists() else {'base_url':'https://api.deepseek.com','model':'deepseek-flash'}
            settings['api_key'] = key
            fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'w', encoding='utf-8') as file: json.dump(settings,file)
    try:
        from server import make_server, PROVIDER
        server = make_server(args.port)
    except (OSError, ValueError) as exc:
        print('Startup failed / 启动失败：', str(exc))
        print('Check configuration or choose --port 8766 / 检查配置，或更换端口。')
        return 1
    url = f'http://127.0.0.1:{server.server_port}'
    print('PAPER AI / 本地工作台:',url,flush=True)
    print('Live AI configured / AI 已配置' if PROVIDER['api_key'] else 'Configure AI in settings / 请在设置中配置 AI')
    if not args.no_browser:
        threading.Timer(.5,lambda:webbrowser.open(url)).start()
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
    return 0


if __name__ == '__main__':sys.exit(main())
