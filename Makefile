#MAKEFLAGS += --silent

TARGETS= $(shell egrep -o '^[a-zA-Z0-9].*' .gitlab-ci.yml | cut -d: -f1 | egrep -v 'stages|image')

gitlab-runner:
	@(which /usr/bin/gitlab-runner || (echo "ERROR: gitlab-runner not installed."; exit 1;))

$(TARGETS) : gitlab-runner
	gitlab-runner exec docker $@

.PHONY: $(TARGETS)
#.SILENT: gitlab-runner
