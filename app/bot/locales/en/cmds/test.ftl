test-db_pool_error = Database pool not available. Please check bot configuration.

test-test_results =
    <b>🧪 Database & Redis Test Results:</b>

    <b>🐘 PostgreSQL:</b>
    Status: { $pg_status }
    Response time: { $pg_time }

    <b>🔴 Redis:</b>
    Status: { $redis_status }
    Response time: { $redis_time }

    <i>✅ All systems operational!</i>
