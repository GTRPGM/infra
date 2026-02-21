# ---------- builder ----------
FROM postgres:16-bookworm AS builder

ARG PGVECTOR_VER=v0.7.4
ARG AGE_VER=release/PG16/1.6.0

RUN set -eux; \
  apt-get update; \
  apt-get install -y --no-install-recommends \
    ca-certificates git build-essential make cmake \
    postgresql-server-dev-16 \
    libreadline-dev zlib1g-dev \
    clang llvm flex bison \
  ; \
  rm -rf /var/lib/apt/lists/*

# Build pgvector
RUN set -eux; \
  git clone --depth 1 --branch "${PGVECTOR_VER}" https://github.com/pgvector/pgvector.git /tmp/pgvector; \
  cd /tmp/pgvector; \
  make -j"$(nproc)"; \
  make install; \
  rm -rf /tmp/pgvector

# Build Apache AGE
RUN set -eux; \
  git clone --depth 1 --branch "${AGE_VER}" https://github.com/apache/age.git /tmp/age; \
  cd /tmp/age; \
  make -j"$(nproc)"; \
  make install; \
  rm -rf /tmp/age

# ---------- runtime ----------
FROM postgres:16-bookworm

# pgvector + age만 빌더에서 .so/.sql 복사 (빌드툴 없음)
COPY --from=builder /usr/lib/postgresql/16/lib/ /usr/lib/postgresql/16/lib/
COPY --from=builder /usr/share/postgresql/16/extension/ /usr/share/postgresql/16/extension/

# AGE는 shared_preload_libraries 필요
RUN set -eux; \
  printf "\n# AGE Config\nshared_preload_libraries = 'age,pg_stat_statements'\nsearch_path = '\"\$user\", public, ag_catalog'\n" >> /usr/share/postgresql/postgresql.conf.sample

COPY ./initdb/ /docker-entrypoint-initdb.d/
