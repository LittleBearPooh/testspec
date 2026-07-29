# TestSpec 测试环境 Docker Compose
# 用于本地开发和 CI 中启动隔离的测试数据库
#
# 用法:
#   docker-compose -f docker-compose.test.yml up -d     # 启动测试环境
#   docker-compose -f docker-compose.test.yml down -v   # 停止并清理数据卷
#
# 环境变量:
#   TEST_DB_PASSWORD — 数据库密码（默认: Test@1234）
#   TEST_DB_PORT     — 数据库端口映射（默认: 1433/3306/5432）

version: "3.8"

services:
{{#IF_DB_SQLSERVER}}
  test-db:
    image: mcr.microsoft.com/mssql/server:2022-latest
    container_name: testspec-mssql
    environment:
      ACCEPT_EULA: "Y"
      SA_PASSWORD: "${TEST_DB_PASSWORD:-Test@1234}"
      MSSQL_PID: "Express"
    ports:
      - "${TEST_DB_PORT:-1433}:1433"
    volumes:
      - test-db-data:/var/opt/mssql
    healthcheck:
      test: /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "$$SA_PASSWORD" -Q "SELECT 1" -b -C
      interval: 10s
      timeout: 5s
      retries: 10
      start_period: 30s
{{/IF_DB_SQLSERVER}}

{{#IF_DB_MYSQL}}
  test-db:
    image: mysql:8.0
    container_name: testspec-mysql
    environment:
      MYSQL_ROOT_PASSWORD: "${TEST_DB_PASSWORD:-Test@1234}"
      MYSQL_DATABASE: testspec_test
    ports:
      - "${TEST_DB_PORT:-3306}:3306"
    volumes:
      - test-db-data:/var/lib/mysql
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "--silent"]
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 20s
{{/IF_DB_MYSQL}}

{{#IF_DB_POSTGRESQL}}
  test-db:
    image: postgres:16-alpine
    container_name: testspec-postgres
    environment:
      POSTGRES_DB: testspec_test
      POSTGRES_USER: testspec
      POSTGRES_PASSWORD: "${TEST_DB_PASSWORD:-Test@1234}"
    ports:
      - "${TEST_DB_PORT:-5432}:5432"
    volumes:
      - test-db-data:/var/lib/postgresql/data
    healthcheck:
      test: pg_isready -U testspec -d testspec_test
      interval: 5s
      timeout: 3s
      retries: 10
      start_period: 10s
{{/IF_DB_POSTGRESQL}}

volumes:
  test-db-data:
