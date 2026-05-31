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
    deploy_commit = get_deploy_commit()
    print('DEPLOY COMMIT:', deploy_commit, file=sys.stderr)
    try:
        path = os.path.join(os.path.dirname(__file__), 'cours', 'models.py')
        with open(path, 'r', encoding='utf-8') as f:
            body = f.read()
        has_proxy = 'class Cours(Course)' in body and "app_label = 'cours'" in body
        print('MODEL_COURS_SOURCE_PRESENT:', has_proxy, file=sys.stderr)
    except Exception as exc:
        print('MODEL_COURS_SOURCE_ERROR:', exc, file=sys.stderr)

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
