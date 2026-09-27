"""Version bumps and releases, invoked by the repository Makefile."""
import argparse
from datetime import date
from pathlib import Path
import re
import subprocess
import sys


def git(*args, capture=False):
    return subprocess.run(['git', *args], check=True, text=True,
                          stdout=subprocess.PIPE if capture else None).stdout


def clean_tree():
    for args in [('diff', '--quiet'), ('diff', '--cached', '--quiet')]:
        result = subprocess.run(['git', *args])
        if result.returncode:
            raise ValueError('Commit or discard tracked changes before bumping or releasing.')


def bump(version, next_version):
    path = Path('VERSION')
    if path.read_text().strip() != version:
        raise ValueError('Version changed while preparing the release.')
    path.write_text(next_version + '\n')
    git('add', 'VERSION')
    git('commit', '-m', f'Bump version to {next_version}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['bump', 'release'])
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--remote', default='origin')
    parser.add_argument('--branch', default='master')
    args = parser.parse_args()
    clean_tree()
    if args.action == 'release' and not args.force:
        tags = git('tag', '--merged', 'HEAD', '--sort=-version:refname', capture=True).splitlines()
        latest = next((tag for tag in tags if re.fullmatch(r'v\d+\.\d+\.\d+', tag)), None)
        if latest and git('rev-parse', f'{latest}^{{commit}}', capture=True) == git('rev-parse', 'HEAD', capture=True):
            print(f'Warning: no new commits since {latest}; nothing to release. Use make release FORCE=1 to override.')
            return

    version = Path('VERSION').read_text().strip()
    if not re.fullmatch(r'\d+\.\d+\.\d+', version):
        raise ValueError('Expected a year.month.sequence project version.')
    year, month, sequence = map(int, version.split('.'))
    today = date.today()
    next_version = f'{today.year}.{today.month}.{sequence + 1}' if (year, month) == (today.year, today.month) else f'{today.year}.{today.month}.1'
    tag = f'v{next_version}'
    if args.action == 'release':
        existing = git('tag', '--list', tag, capture=True).strip()
        if existing:
            raise ValueError(f'Tag {tag} already exists locally.')
        # Check the destination before creating the version commit.
        if git('ls-remote', '--tags', args.remote, f'refs/tags/{tag}', capture=True).strip():
            raise ValueError(f'Tag {tag} already exists on {args.remote}.')
    bump(version, next_version)
    if args.action == 'bump':
        print(f'Version bumped to {next_version}. make release will bump the patch version again.')
        return
    git('push', args.remote, f'HEAD:{args.branch}')
    git('tag', '-a', tag, '-m', f'Release {tag}')
    git('push', args.remote, f'refs/tags/{tag}')
    print(f'Released {tag}.')


if __name__ == '__main__':
    try:
        main()
    except (ValueError, subprocess.CalledProcessError) as exc:
        print(f'Error: {exc}', file=sys.stderr)
        sys.exit(1)
