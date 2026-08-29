#!/usr/bin/env bash
# Containerized Moodle for round-trip tests (Podman; works with Docker via alias).
#
#   scripts/moodle/moodle-rt.sh up [BRANCH]   # start db+web, install Moodle (default: 405)
#   scripts/moodle/moodle-rt.sh status        # is the stack ready?
#   scripts/moodle/moodle-rt.sh down          # stop and remove containers (keeps images)
#
# BRANCH selects the packaged Moodle line, e.g. 405 (4.5 LTS), 500 (5.0).
# Then: QS_MOODLE_ROUNDTRIP=1 uv run pytest tests/test_moodle_roundtrip.py
set -euo pipefail

ENGINE="${QS_CONTAINER_ENGINE:-podman}"
NET=qsafe-moodle
DB=qsafe-moodle-db
WEB=qsafe-moodle-web
DBPASS=qsafe-moodle
PHP_IMAGE=docker.io/moodlehq/moodle-php-apache:8.3
PG_IMAGE=docker.io/library/postgres:16-alpine

up() {
    local branch="${1:-405}"
    local tarball="https://packaging.moodle.org/stable${branch}/moodle-latest-${branch}.tgz"

    $ENGINE network exists "$NET" 2>/dev/null || $ENGINE network create "$NET"

    if ! $ENGINE container exists "$DB" 2>/dev/null; then
        $ENGINE run -d --name "$DB" --network "$NET" \
            -e POSTGRES_USER=moodle -e POSTGRES_PASSWORD="$DBPASS" -e POSTGRES_DB=moodle \
            "$PG_IMAGE"
    fi

    if ! $ENGINE container exists "$WEB" 2>/dev/null; then
        $ENGINE run -d --name "$WEB" --network "$NET" "$PHP_IMAGE"
    fi

    if ! $ENGINE exec "$WEB" test -f /var/www/html/config.php; then
        echo "Downloading Moodle ${branch} ..."
        $ENGINE exec "$WEB" bash -c \
            "curl -sSfL '$tarball' | tar xz --strip-components=1 -C /var/www/html \
             && mkdir -p /var/www/moodledata && chown -R www-data:www-data /var/www/moodledata"
        echo "Installing Moodle (a few minutes) ..."
        $ENGINE exec "$WEB" php /var/www/html/admin/cli/install.php \
            --non-interactive --agree-license --lang=en \
            --wwwroot=http://localhost --dataroot=/var/www/moodledata \
            --dbtype=pgsql --dbhost="$DB" --dbname=moodle --dbuser=moodle --dbpass="$DBPASS" \
            --fullname="questionsafe roundtrip" --shortname=qsrt \
            --adminuser=admin --adminpass='Qsafe.12345' --adminemail=admin@example.invalid
    fi
    status
}

status() {
    if $ENGINE exec "$WEB" php -r 'define("CLI_SCRIPT", true); require "/var/www/html/config.php"; echo "Moodle {$CFG->release} ready\n";' 2>/dev/null; then
        return 0
    fi
    echo "not ready (run: $0 up)" >&2
    return 1
}

down() {
    $ENGINE rm -f "$WEB" "$DB" 2>/dev/null || true
    $ENGINE network rm "$NET" 2>/dev/null || true
    echo "stack removed"
}

case "${1:-}" in
    up) shift; up "$@" ;;
    status) status ;;
    down) down ;;
    *) echo "usage: $0 {up [BRANCH]|status|down}" >&2; exit 2 ;;
esac
