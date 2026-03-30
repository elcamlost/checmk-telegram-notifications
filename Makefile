PKG = telegram_notify
CONTAINER = checkmk-${PKG}
IMAGE ?= checkmk/check-mk-raw:2.4.0-latest
MKP = $(shell ls ${PKG}*.mkp 2>/dev/null | head -1)

.DEFAULT: test
.PHONY: package test

package:
	python3 package.py

test: package
	docker run --detach --rm --name=${CONTAINER} ${IMAGE}
	sleep 10
	docker cp ${MKP} ${CONTAINER}:/tmp/ && \
	docker cp tests/integration_check.py ${CONTAINER}:/tmp/ && \
	docker exec -u cmk ${CONTAINER} bash -l -c "mkp add /tmp/${MKP} && mkp enable ${PKG}" && \
	docker exec -u cmk ${CONTAINER} bash -l -c "mkp list" | grep -q ${PKG} && \
	docker exec -u cmk ${CONTAINER} bash -l -c "python3 /tmp/integration_check.py" && \
	docker exec -u cmk ${CONTAINER} bash -l -c \
	  "python3 -m py_compile ~/local/share/check_mk/notifications/telegram"; \
	EXIT=$$?; docker stop -t 0 ${CONTAINER}; exit $$EXIT
