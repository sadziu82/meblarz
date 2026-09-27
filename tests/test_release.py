"""Exercise release commands against disposable repositories and a local remote."""
from pathlib import Path
import shutil
import subprocess
from datetime import date

import pytest

ROOT = Path(__file__).resolve().parents[1]


def run(repo, *args, check=True):
    return subprocess.run(args, cwd=repo, text=True, capture_output=True, check=check)


@pytest.fixture
def release_repo(tmp_path):
    repo = tmp_path / 'repo'
    repo.mkdir()
    remote = tmp_path / 'remote.git'
    run(tmp_path, 'git', 'init', '--bare', str(remote))
    run(repo, 'git', 'init', '-b', 'master')
    run(repo, 'git', 'config', 'user.name', 'Release Test')
    run(repo, 'git', 'config', 'user.email', 'release@example.invalid')
    run(repo, 'git', 'config', 'commit.gpgsign', 'false')
    run(repo, 'git', 'config', 'tag.gpgsign', 'false')
    run(repo, 'git', 'remote', 'add', 'origin', str(remote))
    shutil.copy(ROOT / 'Makefile', repo)
    (repo / 'scripts').mkdir()
    shutil.copy(ROOT / 'scripts/release.py', repo / 'scripts')
    (repo / 'VERSION').write_text(f'{date.today().year}.{date.today().month}.3\n')
    run(repo, 'git', 'add', '.')
    run(repo, 'git', 'commit', '-m', 'initial')
    run(repo, 'git', 'tag', '-a', f'v{date.today().year}.{date.today().month}.3', '-m', 'release')
    run(repo, 'git', 'push', '--tags', 'origin', 'master')
    (repo / 'untracked.sql').write_text('leave this file alone')
    return repo


def assert_released(repo):
    assert (repo / 'VERSION').read_text().strip() == f'{date.today().year}.{date.today().month}.4'
    head = run(repo, 'git', 'rev-parse', 'HEAD').stdout.strip()
    assert run(repo, 'git', 'rev-parse', f'v{date.today().year}.{date.today().month}.4^{{commit}}').stdout.strip() == head
    remote = run(repo, 'git', 'ls-remote', 'origin', 'refs/heads/master', f'refs/tags/v{date.today().year}.{date.today().month}.4^{{}}').stdout
    assert len(remote.splitlines()) == 2
    assert all(line.startswith(head) for line in remote.splitlines())
    assert run(repo, 'git', 'status', '--porcelain').stdout.strip() == '?? untracked.sql'


def test_no_new_commits_warns_without_mutation(release_repo):
    before = run(release_repo, 'git', 'rev-parse', 'HEAD').stdout
    result = run(release_repo, 'make', 'release')
    assert 'Warning: no new commits' in result.stdout
    assert run(release_repo, 'git', 'rev-parse', 'HEAD').stdout == before
    assert run(release_repo, 'git', 'tag', '--list').stdout.strip() == f'v{date.today().year}.{date.today().month}.3'


def test_force_releases_without_new_commits(release_repo):
    run(release_repo, 'make', 'release', 'FORCE=1')
    assert_released(release_repo)


def test_new_commit_bumps_and_releases(release_repo):
    (release_repo / 'feature.txt').write_text('feature')
    run(release_repo, 'git', 'add', 'feature.txt')
    run(release_repo, 'git', 'commit', '-m', 'feature')
    run(release_repo, 'make', 'release')
    assert_released(release_repo)
    assert 'Warning: no new commits' in run(release_repo, 'make', 'release').stdout


def test_force_still_refuses_uncommitted_changes(release_repo):
    path = release_repo / 'VERSION'
    path.write_text(path.read_text() + '# unsaved change\n')
    result = run(release_repo, 'make', 'release', 'FORCE=1', check=False)
    assert result.returncode != 0
    assert 'tracked changes' in result.stderr
    assert run(release_repo, 'git', 'tag', '--list').stdout.strip() == f'v{date.today().year}.{date.today().month}.3'


def test_standalone_bump_does_not_publish(release_repo):
    run(release_repo, 'make', 'bump')
    assert (release_repo / 'VERSION').read_text().strip() == f'{date.today().year}.{date.today().month}.4'
    assert run(release_repo, 'git', 'tag', '--list').stdout.strip() == f'v{date.today().year}.{date.today().month}.3'
    assert not run(release_repo, 'git', 'ls-remote', '--tags', 'origin', f'refs/tags/v{date.today().year}.{date.today().month}.4').stdout
