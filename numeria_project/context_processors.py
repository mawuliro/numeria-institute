import os
import subprocess

from .version import DEPLOY_COMMIT as STATIC_DEPLOY_COMMIT


def get_current_deploy_commit():
    commit = os.environ.get('DEPLOY_COMMIT') or os.environ.get('GIT_COMMIT')
    if commit:
        return commit

    if STATIC_DEPLOY_COMMIT:
        return STATIC_DEPLOY_COMMIT

    try:
        project_root = os.path.dirname(os.path.dirname(__file__))
        commit = subprocess.check_output(
            ['git', 'rev-parse', '--short', 'HEAD'],
            cwd=project_root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return commit
    except Exception:
        return None


def deploy_info(request):
    return {
        'deploy_commit': get_current_deploy_commit() or 'unknown',
    }
