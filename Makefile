PYTHON ?= python3
REMOTE ?= origin
BRANCH ?= master
FORCE ?= 0

.PHONY: bump help release

help:
	@printf '%s\n' \
		'make bump             Bump the monthly release sequence and commit VERSION.' \
		'make release          Bump, commit, push the branch, create and push the release tag.' \
		'make release FORCE=1  Release even without new commits since the previous release.'

bump:
	$(PYTHON) scripts/release.py bump

release:
	$(PYTHON) scripts/release.py release --remote "$(REMOTE)" --branch "$(BRANCH)" $(if $(filter 1,$(FORCE)),--force,)
