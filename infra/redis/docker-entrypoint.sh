#!/bin/sh
set -e
if [ -n "$REDIS_PASSWORD" ]; then
    exec redis-server /usr/local/etc/redis/redis.conf --requirepass "$REDIS_PASSWORD"
else
    exec redis-server /usr/local/etc/redis/redis.conf
fi
