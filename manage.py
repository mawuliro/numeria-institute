#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys


def get_deploy_commit():
    commit = os.environ.get('DEPLOY_COMMIT') or os.environ.get('GIT_COMMIT')
    if commit:
        return commit

    try:
        import subprocess
        project_root = os.path.dirname(__file__)
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=project_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return commit
    except Exception:
        return 'unknown'


def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'numeria_project.settings')
    print('DEPLOY COMMIT:', get_deploy_commit(), file=sys.stderr)
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
