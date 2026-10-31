#!/usr/bin/env bash
# Containerized Moodle for round-trip tests (Podman; works with Docker via alias).
#
#   scripts/moodle/moodle-rt.sh up [BRANCH]     # start db+web, install Moodle (default: 502)
#   scripts/moodle/moodle-rt.sh status          # which stacks are ready?
#   scripts/moodle/moodle-rt.sh down [BRANCH]   # remove one stack, or all (keeps images)
#
# BRANCH selects the packaged Moodle line, e.g. 405 (4.5 LTS), 502 (5.2).
# Each branch is its own stack (qsafe-moodle-BRANCH-{db,web}), so several can run at
# once; the round-trip test runs against every running stack.
# Moodle 5.3 requires PostgreSQL 17 (verified with 502 and 503; 405 not re-run on 17).
# From Git Bash on Windows, export MSYS_NO_PATHCONV=1 so container paths stay as is.
# Then: QS_MOODLE_ROUNDTRIP=1 uv run pytest tests/test_moodle_roundtrip.py
set -euo pipefail

ENGINE="${QS_CONTAINER_ENGINE:-podman}"
NET=qsafe-moodle
DBPASS=qsafe-moodle
PHP_IMAGE=docker.io/moodlehq/moodle-php-apache:8.3
PG_IMAGE=docker.io/library/postgres:17-alpine

up() {
    local branch="${1:-502}"
    local tarball="https://packaging.moodle.org/stable${branch}/moodle-latest-${branch}.tgz"
    local db="qsafe-moodle-${branch}-db" web="qsafe-moodle-${branch}-web"

    $ENGINE network exists "$NET" 2>/dev/null || $ENGINE network create "$NET"

    if ! $ENGINE container exists "$db" 2>/dev/null; then
        $ENGINE run -d --name "$db" --network "$NET" \
            -e POSTGRES_USER=moodle -e POSTGRES_PASSWORD="$DBPASS" -e POSTGRES_DB=moodle \
            "$PG_IMAGE"
    fi

    if ! $ENGINE container exists "$web" 2>/dev/null; then
        $ENGINE run -d --name "$web" --network "$NET" "$PHP_IMAGE"
    fi

    if ! $ENGINE exec "$web" test -f /var/www/html/config.php; then
        echo "Downloading Moodle ${branch} ..."
        $ENGINE exec "$web" bash -c \
            "curl -sSfL '$tarball' | tar xz --strip-components=1 -C /var/www/html \
             && mkdir -p /var/www/moodledata && chown -R www-data:www-data /var/www/moodledata"
        echo "Installing Moodle (a few minutes) ..."
        $ENGINE exec "$web" php /var/www/html/admin/cli/install.php \
            --non-interactive --agree-license --lang=en \
            --wwwroot=http://localhost --dataroot=/var/www/moodledata \
            --dbtype=pgsql --dbhost="$db" --dbname=moodle --dbuser=moodle --dbpass="$DBPASS" \
            --fullname="questionsafe roundtrip" --shortname=qsrt \
            --adminuser=admin --adminpass='Qsafe.12345' --adminemail=admin@example.invalid
    fi
    ready "$web"
}

ready() {
    $ENGINE exec "$1" php -r 'define("CLI_SCRIPT", true); require "/var/www/html/config.php"; echo "'"$1"': Moodle {$CFG->release} ready\n";' 2>/dev/null
}

webs() {
    $ENGINE ps --format '{{.Names}}' | grep -E '^qsafe-moodle-[0-9]+-web$' || true
}

status() {
    local web found=1
    for web in $(webs); do ready "$web" && found=0; done
    [ "$found" = 0 ] || { echo "no stack ready (run: $0 up [BRANCH])" >&2; return 1; }
}

down() {
    local pattern="^qsafe-moodle-${1:-[0-9]+}-(db|web)$" name
    for name in $($ENGINE ps -a --format '{{.Names}}' | grep -E "$pattern"); do
        $ENGINE rm -f "$name" >/dev/null && echo "removed $name"
    done
    [ -n "$(webs)" ] || $ENGINE network rm "$NET" >/dev/null 2>&1 || true
}

case "${1:-}" in
    up) shift; up "$@" ;;
    status) status ;;
    down) shift; down "$@" ;;
    *) echo "usage: $0 {up [BRANCH]|status|down [BRANCH]}" >&2; exit 2 ;;
esac
